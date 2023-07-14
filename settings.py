from numba import njit
import numpy as np
import glm
import math

# resolution
WIN_RES = glm.vec2(1600, 900)

# chunk
CHUNK_SIZE = 32
H_CHUNK_SIZE = CHUNK_SIZE // 2
CHUNK_AREA = CHUNK_SIZE * CHUNK_SIZE
CHUNK_VOLUME = CHUNK_AREA * CHUNK_SIZE

# world
WORLD_W, WORLD_H = 10, 3
WORLD_D = WORLD_W
WORLD_AREA = WORLD_W * WORLD_D
WORLD_VOL = WORLD_AREA * WORLD_H

# world center
CENTER_XZ = WORLD_W * H_CHUNK_SIZE
CENTER_Y = WORLD_H * H_CHUNK_SIZE

# camera
# calculating aspect ratio by dividing the window resolution's x and y axes
ASPECT_RATIO = WIN_RES.x / WIN_RES.y
# field of view
FOV_DEG = 50
# calcultion vertical fov and horizontal fov
V_FOV = glm.radians(FOV_DEG)
H_FOV = 2 * math.atan(math.tan(V_FOV * 0.5 * ASPECT_RATIO))
# setting near and far clipping planes
NEAR = 0.1
FAR = 2000
PITCH_MAX = glm.radians(89)

# player
PLAYER_SPEED = 0.005
PLAYER_ROT_SPEED = 0.003
PLAYER_POS = glm.vec3(CENTER_XZ, WORLD_H * CHUNK_SIZE, CENTER_XZ)
MOUSE_SENSITIVITY = 0.002

# color
BG_COLOR = glm.vec3(.1, .16, .25)
