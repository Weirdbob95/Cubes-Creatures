from multiprocessing import Process
from multiprocessing.queues import SimpleQueue

import scipy.ndimage
from OpenGL.GL import *
from noise import snoise4 as perlin
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from util import *

chunk_size = vec(32, 32, 32)
# chunk_size = vec(8, 8, 8)

land_scale = 300.
land_height = 100.
octaves = 10

color_scale = 150.

draw_dist = 2


# generate_dist = 4


class World(object):
    chunks = {}
    nonempty_chunks = {}

    generating = []
    chunk_queue = SimpleQueue()

    def ensure_generated(self, chunk_loc):
        if chunk_loc not in self.chunks:
            print chunk_loc
            self.generate_chunk(chunk_loc, other_process=False)
            if chunk_loc in self.generating:
                self.generating.remove(chunk_loc)

    def generate_chunk(self, chunk_loc, other_process=True):
        if other_process:
            self.generating.append(chunk_loc)
            p = Process(target=self._generate_chunk_process, args=(chunk_loc, self.chunk_queue))
            p.daemon = True
            p.start()
        else:
            c = Chunk(chunk_loc)
            self.chunks[chunk_loc] = c
            if not c.is_empty:
                c.redraw()
                self.nonempty_chunks[chunk_loc] = c

    # @staticmethod
    def _generate_chunk_process(self, chunk_loc, output):
        try:
            output.put((chunk_loc, Chunk(chunk_loc)))
        except Exception as e:
            output.put(e)

    def is_solid(self, pos):
        chunk_loc = to_int(pos / chunk_size)
        chunk = self.chunks.get(tuple(chunk_loc))
        if chunk is None:
            return True
        return chunk.is_solid(pos - chunk_loc * chunk_size)

    def render(self, camera_pos):
        while not self.chunk_queue.empty():
            chunk_loc, c = self.chunk_queue.get()
            if chunk_loc in self.generating:
                self.generating.remove(chunk_loc)
                self.chunks[chunk_loc] = c
                if not c.is_empty:
                    c.redraw()
                    self.nonempty_chunks[chunk_loc] = c
                    break

        camera_loc = np.int_(camera_pos / chunk_size)
        self.ensure_generated(tuple(camera_loc))

        if len(self.generating) < 15:
            nearby = multi_range(camera_loc[:2] - draw_dist, camera_loc[:2] + draw_dist + 1)
            nearby = flatten(map(lambda x: [x + (a,) for a in xrange(-2, 2)], nearby))
            to_generate = filter(lambda x: x not in self.chunks and x not in self.generating, nearby)
            if to_generate:
                chunk_loc = min(to_generate,
                                key=lambda x: length_squared(x + vec(.5, .5, .5) - camera_pos / chunk_size))
                self.generate_chunk(chunk_loc)

        chunk_locs = np.asarray(self.nonempty_chunks.keys())
        if chunk_locs.size:
            centers = chunk_locs * chunk_size + chunk_size / 2
            in_frustum = frustum_intersects_aabbs(centers, chunk_size)
            for chunk_loc in chunk_locs[in_frustum]:
                self.nonempty_chunks[tuple(chunk_loc)].draw()


class Chunk(object):
    def __init__(self, pos):
        self.pos = np.asarray(pos)

        if self.pos[2] * chunk_size[2] > land_height:
            self.uniform = 0
        elif (self.pos[2] + 1) * chunk_size[2] < -land_height:
            self.uniform = 1
        else:
            chunk_grid = np.array(
                np.meshgrid(*map(np.arange, self.pos * chunk_size - 1, (self.pos + 1) * chunk_size + 1)))
            chunk_grid = np.transpose(chunk_grid, (0, 2, 1, 3))
            self.solid = calculate_solid(chunk_grid)

            if np.all(self.solid == 0):
                self.uniform = 0
            elif np.all(self.solid == 1):
                self.uniform = 1
            else:
                self.uniform = None

        if self.uniform is not None:
            self.is_empty = True
            self.solid = None
            return

        num_neighbors = scipy.ndimage.convolve(np.int_(self.solid), np.array((
            ((0, 0, 0), (0, 1, 0), (0, 0, 0)),
            ((0, 1, 0), (1, 0, 1), (0, 1, 0)),
            ((0, 0, 0), (0, 1, 0), (0, 0, 0))
        )), mode='constant', cval=10)
        interesting = self.solid & (num_neighbors < 6)
        self.visible = []
        for pos in np.transpose(np.nonzero(interesting)):
            world_pos = self.pos * chunk_size + pos - 1
            col = (perlin(0, *world_pos / color_scale, octaves=octaves) / 2 + .5,
                   perlin(1, *world_pos / color_scale, octaves=octaves) / 2 + .5,
                   perlin(2, *world_pos / color_scale, octaves=octaves) / 2 + .5)
            self.visible.append((pos - 1, col))

        if not self.visible:
            self.is_empty = True
            return
        self.is_empty = False

        self.gl_commands = []
        for pos, col in self.visible:
            self.gl_commands.append(('glColor', col))
            self.gl_commands += self.draw_cube(pos)

        print len(self.visible), 'visible blocks'

    def is_solid(self, pos):
        if self.uniform is not None:
            return self.uniform
        return self.solid[pos[0] + 1, pos[1] + 1, pos[2] + 1]

    display_list = None

    def draw(self):
        if self.is_empty: return
        if self.display_list is None:
            self.redraw()
        glCallList(self.display_list)

    def _create_vbo(self):
        if self.is_empty: return

        if self.vbo is None:
            self.vbo = vbo.VBO()

    def redraw(self):
        if self.is_empty: return

        self.display_list = glGenLists(1)

        glNewList(self.display_list, GL_COMPILE)
        glBegin(GL_QUADS)

        for command, val in self.gl_commands:
            if command == 'glVertex':
                glVertex(val + self.pos * chunk_size)
            elif command == 'glColor':
                glColor(val)
            elif command == 'glNormal':
                glNormal3fv(val)

        glEnd()
        glEndList()

    def draw_cube(self, pos):
        pos = np.asarray(pos)
        gl_commands = []

        if not self.is_solid(pos + (-1, 0, 0)):
            gl_commands.append(('glNormal', (-1, 0, 0)))
            for v in (0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid(pos + (1, 0, 0)):
            gl_commands.append(('glNormal', (1, 0, 0)))
            for v in (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1):
                gl_commands.append(('glVertex', pos + v))

        if not self.is_solid(pos + (0, -1, 0)):
            gl_commands.append(('glNormal', (0, -1, 0)))
            for v in (0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid(pos + (0, 1, 0)):
            gl_commands.append(('glNormal', (0, 1, 0)))
            for v in (0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1):
                gl_commands.append(('glVertex', pos + v))

        if not self.is_solid(pos + (0, 0, -1)):
            gl_commands.append(('glNormal', (0, 0, -1)))
            for v in (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0):
                gl_commands.append(('glVertex', pos + v))
        if not self.is_solid(pos + (0, 0, 1)):
            gl_commands.append(('glNormal', (0, 0, 1)))
            for v in (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1):
                gl_commands.append(('glVertex', pos + v))
        return gl_commands


calculate_solid_1 = np.vectorize(lambda x, y, z:
                                 z * land_scale / land_height < perlin(-1, x, y, z, octaves=octaves))


def calculate_solid(pos):
    return calculate_solid_1(*pos / land_scale)
