from settings import *
from numba import uint8


@njit
def get_ao(local_pos, world_pos, world_voxels, plane):
    x, y, z = local_pos
    wx, wy, wz = world_pos

    # checking if there are faces around the current face and calculating ao
    if plane == 'Y':
        a = is_void((x, y, z - 1), (wx, wy, wz - 1), world_voxels)
        b = is_void((x - 1, y, z - 1), (wx - 1, wy, wz - 1), world_voxels)
        c = is_void((x - 1, y, z), (wx - 1, wy, wz), world_voxels)
        d = is_void((x - 1, y, z + 1), (wx - 1, wy, wz + 1), world_voxels)
        e = is_void((x, y, z + 1), (wx, wy, wz + 1), world_voxels)
        f = is_void((x + 1, y, z + 1), (wx + 1, wy, wz + 1), world_voxels)
        g = is_void((x + 1, y, z), (wx + 1, wy, wz), world_voxels)
        h = is_void((x + 1, y, z - 1), (wx + 1, wy, wz - 1), world_voxels)

    elif plane == 'X':
        a = is_void((x, y, z - 1), (wx, wy, wz - 1), world_voxels)
        b = is_void((x, y - 1, z - 1), (wx, wy - 1, wz - 1), world_voxels)
        c = is_void((x, y - 1, z), (wx, wy - 1, wz), world_voxels)
        d = is_void((x, y - 1, z + 1), (wx, wy - 1, wz + 1), world_voxels)
        e = is_void((x, y, z + 1), (wx, wy, wz + 1), world_voxels)
        f = is_void((x, y + 1, z + 1), (wx, wy + 1, wz + 1), world_voxels)
        g = is_void((x, y + 1, z), (wx, wy + 1, wz), world_voxels)
        h = is_void((x, y + 1, z - 1), (wx, wy + 1, wz - 1), world_voxels)

    elif plane == 'Z':
        a = is_void((x - 1, y, z), (wx - 1, wy, wz), world_voxels)
        b = is_void((x - 1, y - 1, z), (wx - 1, wy - 1, wz), world_voxels)
        c = is_void((x, y - 1, z), (wx, wy - 1, wz), world_voxels)
        d = is_void((x + 1, y - 1, z), (wx + 1, wy - 1, wz), world_voxels)
        e = is_void((x + 1, y, z), (wx + 1, wy, wz), world_voxels)
        f = is_void((x + 1, y + 1, z), (wx + 1, wy + 1, wz), world_voxels)
        g = is_void((x, y + 1, z), (wx, wy + 1, wz), world_voxels)
        h = is_void((x - 1, y + 1, z), (wx - 1, wy + 1, wz), world_voxels)

    ao = (a + b + c), (g + h + a), (e + f + g), (c + d + e)
    return ao

@njit
def pack_data(x, y, z, voxel_id, face_id, ao_id, flip_id):
    # to optimize the memory we use bitwise shift method
    # we only need x: 6 bit y: 6bit z: 6bit voxel_id: 8bit: face_id: 3bit ao_id:2bit flip_id: 1bit
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id

    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit
    efg_bit = e_bit + fg_bit
    defg_bit = d_bit + efg_bit
    cdefg_bit = c_bit + defg_bit
    bcdefg_bit = b_bit + cdefg_bit

    packed_data = (
        a << bcdefg_bit |
        b << cdefg_bit |
        c << defg_bit |
        d << efg_bit |
        e << fg_bit |
        f << g_bit | g
    )
    return packed_data

@njit
def get_chunk_index(world_voxel_pos):
    wx, wy, wz = world_voxel_pos
    cx = wx // CHUNK_SIZE
    cy = wy // CHUNK_SIZE
    cz = wz // CHUNK_SIZE
    if not (0 <= cx < WORLD_W and 0 <= cy < WORLD_H and 0 <= cz < WORLD_D):
        return -1

    index = cx + WORLD_W * cz + WORLD_AREA * cy
    return index


@njit
# function to check if any voxels block the view of the face of the current voxel
def is_void(local_voxel_pos, world_voxel_pos, world_voxels):
    chunk_index = get_chunk_index(world_voxel_pos)
    if chunk_index == -1:
        return False
    chunk_voxels = world_voxels[chunk_index]

    x, y, z = local_voxel_pos
    voxel_index = x % CHUNK_SIZE + z % CHUNK_SIZE * CHUNK_SIZE + y % CHUNK_SIZE * CHUNK_AREA

    if chunk_voxels[voxel_index]:
        return False
    return True


@njit
# method to add vertex attributes to vertex data array
def add_data(vertex_data, index, *vertices):
    for vertex in vertices:
        vertex_data[index] = vertex
        index += 1
    return index


@njit
def build_chunk_mesh(chunk_voxels, format_size, chunk_pos, world_voxels):
    # maximum faces we can see at any given time on a voxel is 3
    # 3 faces made up of 2 triangles each. so 3 * 2 * 3 = 18 vertices for a voxel
    # format_size is no.of attributes they are x, y, z, voxel_id, face_id
    # uint32 - unsigned 32-bit integers. That is each vertex takes 1 byte in gpu memory
    vertex_data = np.empty(CHUNK_VOLUME * 18 * format_size, dtype='uint32')
    index = 0

    for x in range(CHUNK_SIZE):
        for z in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]
                if not voxel_id:
                    continue

                # voxel world position
                cx, cy, cz = chunk_pos
                wx = x + cx * CHUNK_SIZE
                wy = y + cy * CHUNK_SIZE
                wz = z + cz * CHUNK_SIZE

                # top face
                if is_void((x, y + 1, z), (wx, wy + 1, wz), world_voxels):
                    # get ao values
                    ao = get_ao((x, y + 1, z), (wx, wy + 1, wz), world_voxels, plane='Y')
                    # comparing ao terms for orientation
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x, y + 1, z, voxel_id, 0, ao[0], flip_id)
                    v1 = pack_data(x + 1, y + 1, z, voxel_id, 0, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 0, ao[2], flip_id)
                    v3 = pack_data(x, y + 1, z + 1, voxel_id, 0, ao[3], flip_id)

                    # flip the order of triangles if the condition is met
                    if flip_id:
                        index = add_data(vertex_data, index, v1, v0, v3, v1, v3, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                    # form the face by making 2 triangles
                    # index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                # bottom face
                if is_void((x, y - 1, z), (wx, wy - 1, wz), world_voxels):
                    ao = get_ao((x, y - 1, z), (wx, wy - 1, wz), world_voxels, plane='Y')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x, y, z, voxel_id, 1, ao[0], flip_id)
                    v1 = pack_data(x + 1, y, z, voxel_id, 1, ao[1], flip_id)
                    v2 = pack_data(x + 1, y, z + 1, voxel_id, 1, ao[2], flip_id)
                    v3 = pack_data(x, y, z + 1, voxel_id, 1, ao[3], flip_id)

                    # form the face by making 2 triangles
                    if flip_id:
                        index = add_data(vertex_data, index, v1, v2, v0, v1, v2, v3)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v3, v0, v1, v2)

                # right face
                if is_void((x + 1, y, z), (wx + 1, wy, wz), world_voxels):
                    ao = get_ao((x + 1, y, z), (wx + 1, wy, wz), world_voxels, plane='X')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x + 1, y, z, voxel_id, 2, ao[0], flip_id)
                    v1 = pack_data(x + 1, y + 1, z, voxel_id, 2, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 2, ao[2], flip_id)
                    v3 = pack_data(x + 1, y, z + 1, voxel_id, 2, ao[3], flip_id)

                    # form the face by making 2 triangles
                    if flip_id:
                        index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                # left face
                if is_void((x - 1, y, z), (wx - 1, wy, wz), world_voxels):
                    ao = get_ao((x - 1, y, z), (wx - 1, wy, wz), world_voxels, plane='X')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x, y, z, voxel_id, 3, ao[0], flip_id)
                    v1 = pack_data(x, y + 1, z, voxel_id, 3, ao[1], flip_id)
                    v2 = pack_data(x, y + 1, z + 1, voxel_id, 3, ao[2], flip_id)
                    v3 = pack_data(x, y, z + 1, voxel_id, 3, ao[3], flip_id)

                    # form the face by making 2 triangles
                    if flip_id:
                        index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                # back face
                if is_void((x, y, z - 1), (wx, wy, wz - 1), world_voxels):
                    ao = get_ao((x, y, z - 1), (wx, wy, wz - 1), world_voxels, plane='Z')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x, y, z, voxel_id, 4, ao[0], flip_id)
                    v1 = pack_data(x, y + 1, z, voxel_id, 4, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z, voxel_id, 4, ao[2], flip_id)
                    v3 = pack_data(x + 1, y, z, voxel_id, 4, ao[3], flip_id)

                    # form the face by making 2 triangles
                    if flip_id:
                        index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                # front face
                if is_void((x, y, z + 1), (wx, wy, wz + 1), world_voxels):
                    ao = get_ao((x, y, z + 1), (wx, wy, wz + 1), world_voxels, plane='Z')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]

                    v0 = pack_data(x, y, z + 1, voxel_id, 5, ao[0], flip_id)
                    v1 = pack_data(x, y + 1, z + 1, voxel_id, 5, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 5, ao[2], flip_id)
                    v3 = pack_data(x + 1, y, z + 1, voxel_id, 5, ao[3], flip_id)

                    # form the face by making 2 triangles
                    if flip_id:
                        index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

    return vertex_data[:index + 1]
