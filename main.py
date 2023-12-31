from settings import *
import moderngl as mgl
import pygame as pg
import sys
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from textures import Textures


class VoxelEngine:
    def __init__(self):
        # set opengl attributes and depth buffer to 24
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, 24)

        # Create opengl window using pygame context
        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        # enable depth test, face culling and blending in moderngl
        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        # enable automatic garbage collection
        self.ctx.gc_mode = 'auto'

        # to keep track of time
        self.clock = pg.time.Clock()
        self.delta_time = 0
        self.time = 0

        # Locking the mouse to the window
        pg.event.set_grab(True)
        # make the cursor invisible
        pg.mouse.set_visible(False)

        # flag to check if application is running
        self.is_running = True

        self.on_init()

    def on_init(self):
        self.textures = Textures(self)
        self.player = Player(self)
        self.shader_program = ShaderProgram(self)
        self.scene = Scene(self)

    def update(self):
        self.player.update()
        self.shader_program.update()
        self.scene.update()

        # start the clock ticks
        self.delta_time = self.clock.tick()
        # to monitor performance by using display fps
        self.time = pg.time.get_ticks() * 0.001
        pg.display.set_caption(f'{self.clock.get_fps() :.0f}')

    def render(self):
        # clear frame and depth buffer
        self.ctx.clear(color=BG_COLOR)
        # render from scene class
        self.scene.render()
        # And display a new frame
        pg.display.flip()

    def handle_events(self):
        # to handle events like pressing quit or escape
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                self.is_running = False
            self.player.handle_event(event=event)

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
        pg.quit()
        sys.exit()


if __name__ == '__main__':
    app = VoxelEngine()
    app.run()
