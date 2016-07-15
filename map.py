import time

import scipy.ndimage
from OpenGL.GL import *
from noise import snoise4 as perlin

from util import *


class Map(object):
    def __init__(self):
        self.size = (500, 500, 200)
        land_scale = 200.
        color_scale = 50.

        self.solid = np.zeros(self.size)
        self.lowest_air = np.int_(np.zeros(self.size[:2]))
        self.highest_cube = np.int_(np.zeros(self.size[:2]))

        print 'Generating random terrain'

        t = time.clock()
        pnoise = np.vectorize(lambda x, y, z:
                              z / 100. < 1 + perlin(-1, x / land_scale, y / land_scale, z / land_scale, octaves=4))
        self.solid = pnoise(*np.meshgrid(*map(np.arange, self.size)))
        print time.clock() - t

        self.lowest_air = np.apply_along_axis(lambda a: np.nonzero(a)[0][0], 2, self.solid == 0)
        self.highest_cube = np.apply_along_axis(lambda a: np.nonzero(a)[0][-1], 2, self.solid)
        print time.clock() - t
        #
        # t = time.clock()
        # for pos in multi_range(self.size):
        #     # if pos[0] % 10 + pos[1] + pos[2] == 0:
        #     #     print pos[0]
        #     if perlin(-1, pos[0] / land_scale, pos[1] / land_scale, pos[2] / land_scale, octaves=4) \
        #             > pos[2] / 100. - 1:
        #         self.solid[pos] = True
        # print time.clock() - t
        #
        # t = time.clock()
        # for pos in multi_range(self.size):
        #     # if pos[0] % 10 + pos[1] + pos[2] == 0:
        #     #     print pos[0]
        #     if perlin(-1, pos[0] / land_scale, pos[1] / land_scale, pos[2] / land_scale, octaves=4) \
        #             > pos[2] / 100. - 1:
        #         self.solid[pos] = True
        #         if self.lowest_air[pos[:2]] == pos[2]:
        #             self.lowest_air[pos[:2]] = pos[2] + 1
        #         self.highest_cube[pos[:2]] = pos[2]
        # print time.clock() - t

        print 'Coloring terrain'

        t = time.clock()
        self.visible = []
        for x, y in multi_range((1, 1), (self.size[0] - 1, self.size[1] - 1)):
            if x % 10 + y == 0:
                print x
            lowest_cube = min(self.lowest_air[x, y] - 1,
                              self.lowest_air[x - 1, y], self.lowest_air[x + 1, y],
                              self.lowest_air[x, y - 1], self.lowest_air[x, y + 1])
            for z in xrange(lowest_cube, self.highest_cube[x, y] + 1):
                pos = np.asarray((x, y, z))
                if self.is_solid_fast(pos):
                    for v in (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1):
                        if not self.is_solid(pos + v):
                            col = (perlin(0, *pos / color_scale, octaves=4) / 2 + .5,
                                   perlin(1, *pos / color_scale, octaves=4) / 2 + .5,
                                   perlin(2, *pos / color_scale, octaves=4) / 2 + .5)
                            self.visible.append((pos, col))
                            break
        print time.clock() - t

        t = time.clock()
        self.visible = []
        neighbors = scipy.ndimage.convolve(np.int_(self.solid), np.array((
            ((0, 0, 0), (0, 1, 0), (0, 0, 0)),
            ((0, 1, 0), (1, 0, 1), (0, 1, 0)),
            ((0, 0, 0), (0, 1, 0), (0, 0, 0))
        )), mode='constant', cval=10)
        interesting = (0 < neighbors) & (6 > neighbors) & self.solid
        for pos in np.transpose(np.nonzero(interesting)):
            col = (perlin(0, *pos / color_scale, octaves=4) / 2 + .5,
                   perlin(1, *pos / color_scale, octaves=4) / 2 + .5,
                   perlin(2, *pos / color_scale, octaves=4) / 2 + .5)
            self.visible.append((pos, col))
        print time.clock() - t

        print len(self.visible), 'visible cubes'

        self.display_list = None

    def is_solid(self, pos):
        for dim in 0, 1, 2:
            if pos[dim] < 0 or pos[dim] >= self.size[dim]:
                return True
        return self.solid[pos[0], pos[1], pos[2]]

    def is_solid_fast(self, pos):
        return self.solid[pos[0], pos[1], pos[2]]

    def render(self):
        if self.display_list is None:

            print 'Computing visible cube faces'
            gl_commands = []
            for pos, col in self.visible:
                gl_commands.append(('glColor', col))
                gl_commands += self.draw_cube(pos)

            print 'Creating display list'
            self.display_list = glGenLists(1)

            glNewList(self.display_list, GL_COMPILE)
            glBegin(GL_QUADS)

            for command, val in gl_commands:
                if command == 'glVertex':
                    glVertex(val)
                elif command == 'glColor':
                    glColor(val)
                elif command == 'glNormal':
                    glNormal3fv(val)

            glEnd()
            glEndList()
            print 'Done'

        glCallList(self.display_list)

    def draw_cube(self, pos):
        pos = np.asarray(pos)
        gl_commands = []

        if not self.is_solid_fast(pos + (-1, 0, 0)):
            gl_commands.append(('glNormal', (-1, 0, 0)))
            for v in (0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid_fast(pos + (1, 0, 0)):
            gl_commands.append(('glNormal', (1, 0, 0)))
            for v in (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1):
                gl_commands.append(('glVertex', pos + v))

        if not self.is_solid_fast(pos + (0, -1, 0)):
            gl_commands.append(('glNormal', (0, -1, 0)))
            for v in (0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid_fast(pos + (0, 1, 0)):
            gl_commands.append(('glNormal', (0, 1, 0)))
            for v in (0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1):
                gl_commands.append(('glVertex', pos + v))

        if not self.is_solid_fast(pos + (0, 0, -1)):
            gl_commands.append(('glNormal', (0, 0, -1)))
            for v in (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid_fast(pos + (0, 0, 1)):
            gl_commands.append(('glNormal', (0, 0, 1)))
            for v in (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1):
                gl_commands.append(('glVertex', pos + v))
        return gl_commands
