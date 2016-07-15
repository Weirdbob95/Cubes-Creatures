from math import *

import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *

from map import Map
from util import *

SCREEN_SIZE = (1200, 800)

pygame.init()
screen = pygame.display.set_mode(SCREEN_SIZE, HWSURFACE | OPENGL | DOUBLEBUF)
# screen = pygame.display.set_mode(SCREEN_SIZE, OPENGL)

# Init OpenGL
glEnable(GL_DEPTH_TEST)
glDepthFunc(GL_LEQUAL);

# glShadeModel(GL_FLAT)
glClearColor(1.0, 1.0, 1.0, 0.0)

glEnable(GL_COLOR_MATERIAL)

glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
ambient = .8
diffuse = .05
glLight(GL_LIGHT0, GL_AMBIENT, (ambient,) * 3 + (1,))
glLight(GL_LIGHT0, GL_DIFFUSE, (diffuse,) * 3 + (1,))
glLight(GL_LIGHT0, GL_SPECULAR, (0, 0, 0, 0))
glLight(GL_LIGHT0, GL_POSITION, (0, 0, 1, 0))

clock = pygame.time.Clock()

# glMaterial(GL_FRONT, GL_AMBIENT, (1.0, 1.0, 1.0, 1.0))
# glMaterial(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

# This object renders the 'map'
game_map = Map()

# Starting player pos
position = np.array(game_map.size) / (2.0, 2.0, .5)
velocity = np.array((0.0, 0.0, 0.0))
gravity = np.array((0.0, 0.0, -20.0))

facing = np.array((0.0, 0.0))
forwards = np.array((1.0, 0.0, 0.0))

pygame.mouse.set_visible(False)

grab_events = False
pygame.event.set_grab(grab_events)

running = True
while running:

    # Timing
    pygame.time.wait(1)

    time_passed_seconds = clock.tick() / 1000.
    if time_passed_seconds > .1:
        time_passed_seconds = .1

    pygame.display.set_caption(str(clock.get_fps()))

    # Input events
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == KEYUP and event.key == K_ESCAPE:
            running = False
        if event.type == KEYUP and event.key == K_l:
            grab_events = not grab_events
            pygame.event.set_grab(grab_events)
        if event.type == KEYUP and event.key == K_1:
            glEnable(GL_LIGHTING)
        if event.type == KEYUP and event.key == K_2:
            glDisable(GL_LIGHTING)
        if event.type == KEYUP and event.key == K_p:
            print position

    mouse_delta = np.array(pygame.mouse.get_rel())

    pressed = pygame.key.get_pressed()

    # Clear the screen, and z-buffer
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    # FPS mouse look
    facing -= mouse_delta / 400.
    if facing[1] > 1.5: facing[1] = 1.5
    if facing[1] < -1.5: facing[1] = -1.5
    forwards = np.array((cos(facing[0]) * cos(facing[1]), sin(facing[0]) * cos(facing[1]), sin(facing[1])))

    # Calculate movement
    movement_speed = 10.0
    if pressed[K_LSHIFT]:
        movement_speed = 30.0

    forward_spd, side_spd = 0, 0
    if pressed[K_w] or pressed[K_UP]:
        forward_spd += 1
    if pressed[K_s] or pressed[K_DOWN]:
        forward_spd -= 1
    if pressed[K_a] or pressed[K_LEFT]:
        side_spd += 1
    if pressed[K_d] or pressed[K_RIGHT]:
        side_spd -= 1

    sideways = np.cross((0, 0, 1), forwards)
    sideways /= np.linalg.norm(sideways)
    hor_velocity = np.cross(sideways, (0, 0, 1)) * forward_spd + sideways * side_spd
    hor_velocity *= movement_speed

    velocity[:2] = hor_velocity[:2]

    if pressed[K_SPACE]:
        velocity[2] = movement_speed

    # Move camera
    old_pos = position.copy()
    position += velocity * time_passed_seconds
    velocity += gravity * time_passed_seconds


    def collision_at(pos):
        lower_left = np.int_(pos - (.8, .8, 2.2))
        upper_right = np.int_(pos + (.8, .8, .6)) + 1
        for pos in multi_range(lower_left, upper_right):
            if game_map.is_solid(pos):
                return True
        return False


    if collision_at(position):
        movement = position - old_pos
        position = old_pos
        if collision_at(position):
            position += movement
        else:
            for dim in 0, 1, 2:
                steps = 10
                step = [0, 0, 0]
                step[dim] = movement[dim] / steps
                for _ in xrange(steps):
                    if not collision_at(position + step):
                        position += step
                    else:
                        velocity[dim] = 0
                        break

    # Update the OpenGL window
    glViewport(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1])
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, float(SCREEN_SIZE[0]) / SCREEN_SIZE[1], .5, 1000.)
    gluLookAt(*append(position, position + forwards, (0, 0, 1)))
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Render the map
    game_map.render()

    # Show the screen
    pygame.display.flip()
