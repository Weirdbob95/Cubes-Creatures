from sys import exit

import pygame
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
from pygame.locals import *

from util import *

if __name__ == '__main__':
    SCREEN_SIZE = (1200, 800)

    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE, HWSURFACE | OPENGL | DOUBLEBUF)
    # screen = pygame.display.set_mode(SCREEN_SIZE, OPENGL)

    # Init OpenGL
    glClearColor(1.0, 1.0, 1.0, 0.0)

    clock = pygame.time.Clock()

    vertex_shader = shaders.compileShader("""
        varying vec4 vertex_color;
        void main() {
            gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
            vertex_color = gl_Color;
        }""", GL_VERTEX_SHADER)
    fragment_shader = shaders.compileShader("""
        varying vec4 vertex_color;
        void main() {
            gl_FragColor = vertex_color;
        }""", GL_FRAGMENT_SHADER)
    shader = shaders.compileProgram(vertex_shader, fragment_shader)
    my_vbo = vbo.VBO(np.array(
        [[0, 1, 0, 0, 1, 0], [-1, -1, 0, 1, 1, 0], [1, -1, 0, 0, 1, 1], [2, -1, 0, 1, 0, 0], [4, -1, 0, 0, 1, 0],
         [4, 1, 0, 0, 0, 1], [2, -1, 0, 1, 0, 0], [4, 1, 0, 0, 0, 1], [2, 1, 0, 0, 1, 1], ], 'f'))

    running = True
    while running:

        pygame.time.wait(1)

        # Timing
        time_passed_seconds = clock.tick() / 1000.
        if time_passed_seconds > .1:
            time_passed_seconds = .1

        pygame.display.set_caption(str(clock.get_fps()))

        # Input events
        for event in pygame.event.get():
            if event.type == QUIT:
                exit()
                running = False
                pygame.event.set_grab(False)
            if event.type == KEYUP and event.key == K_ESCAPE:
                exit()
                running = False
                pygame.event.set_grab(False)

        mouse_delta = np.array(pygame.mouse.get_rel())

        pressed = pygame.key.get_pressed()

        # Clear the screen, and z-buffer
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        # Update the OpenGL window
        glViewport(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1])
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-5, 5, -5, 5, -1, 1)
        # gluPerspective(60.0, float(SCREEN_SIZE[0]) / SCREEN_SIZE[1], .5, 1000.)
        # gluLookAt(*append(position, position + forwards, (0, 0, 1)))
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        shaders.glUseProgram(shader)
        my_vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointer(3, GL_FLOAT, 24, my_vbo)
        glColorPointer(3, GL_FLOAT, 24, my_vbo + 12)
        glDrawArrays(GL_TRIANGLES, 0, 9)
        my_vbo.unbind()
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        shaders.glUseProgram(0)

        # Show the screen
        pygame.display.flip()
