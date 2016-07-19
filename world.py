import time
from multiprocessing import Pool
from multiprocessing import cpu_count

import scipy.ndimage
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
from noise import snoise4 as perlin

from util import *

# land_scale = 300.
# land_height = 100.
# octaves = 6
#
# color_scale = 150.

land_scale = 1000.
land_height = 200.
land_octaves = 7

color_scale = 800.
color_octaves = 1

generate_dist = 2
cheat_height = land_height * .5

# chunk_size = vec(256, 256, 256)
chunk_size = vec(64, 64, 64)
# z_band = int(math.ceil(cheat_height / chunk_size[2]))
chunk_zoom = 4


class World(object):
    def __init__(self):
        self.chunks = {}
        self.nonempty_chunks = set()
        self.generating = set()
        self.generate_next = set()
        self.process_pool = Pool(max(1, cpu_count() - 1))
        self.results = set()

    def _add_chunk(self, c, chunk_loc):
        self.chunks[chunk_loc] = c
        if not c.is_empty:
            self.nonempty_chunks.add(chunk_loc)
            for dir in (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1):
                next = tuple(np.add(chunk_loc, dir))
                if next not in self.chunks and next not in self.generating:
                    self.generate_next.add(next)

    def ensure_generated(self, pos):
        chunk_loc = tuple(to_int(pos / chunk_size))
        if chunk_loc not in self.chunks:
            self._generate_chunk(chunk_loc, other_process=False)
            if chunk_loc in self.generating:
                self.generating.remove(chunk_loc)

    def _generate_chunk(self, chunk_loc, other_process=True):
        if chunk_loc in self.generate_next:
            self.generate_next.remove(chunk_loc)
        if other_process:
            self.generating.add(chunk_loc)
            self.results.add(self.process_pool.apply_async(
                func=_generate_chunk_process, args=(chunk_loc,)))
        else:
            self._add_chunk(Chunk(chunk_loc), chunk_loc)

    def is_solid(self, pos):
        chunk_loc = to_int(pos / chunk_size)
        chunk = self.chunks.get(tuple(chunk_loc))
        if chunk is None:
            return True
        return chunk.is_solid(pos - chunk.world_pos)

    def render(self, camera_pos):
        ready_results = filter(lambda x: x.ready(), self.results)
        self.results = set(filter(lambda x: not x.ready(), self.results))
        for result in ready_results:
            chunk_loc, c = result.get()
            if chunk_loc in self.generating:
                self.generating.remove(chunk_loc)
                self._add_chunk(c, chunk_loc)

        self.ensure_generated(camera_pos)

        if len(self.generating) < max(1, cpu_count() - 1):
            if self.generate_next:
                chunk_loc = min(self.generate_next,
                                key=lambda x: length_squared(x + vec(.5, .5, .5) - camera_pos / chunk_size))
                if length_squared(chunk_loc + vec(.5, .5,
                                                  .5) - camera_pos / chunk_size) < generate_dist * generate_dist:
                    self._generate_chunk(chunk_loc)

        chunk_locs = np.asarray(list(self.nonempty_chunks))
        if chunk_locs.size:
            centers = chunk_locs * chunk_size + chunk_size / 2
            in_frustum = frustum_intersects_aabbs(centers, chunk_size)
            for chunk_loc in chunk_locs[in_frustum]:
                self.chunks[tuple(chunk_loc)].draw()


class Chunk(object):
    def __init__(self, pos):
        self.pos = np.asarray(pos)
        self.world_pos = self.pos * chunk_size

        if self.pos[2] * chunk_size[2] > cheat_height:
            self.uniform = 0
        elif (self.pos[2] + 1) * chunk_size[2] < 0:  # -cheat_height:
            self.uniform = 1
        else:
            t = time.clock()
            chunk_grid = np.array(
                np.meshgrid(*map(np.arange, self.world_pos, self.world_pos + chunk_size + chunk_zoom + 1,
                                 (chunk_zoom, chunk_zoom, chunk_zoom))))
            chunk_grid = np.transpose(chunk_grid, (0, 2, 1, 3))
            self.solid = calculate_solid(chunk_grid)
            self.solid = scipy.ndimage.zoom(self.solid, (chunk_size + chunk_zoom + 1.1) / (chunk_size / chunk_zoom + 2),
                                            order=1) > 0
            self.solid = self.solid[:chunk_size[0] + 2, :chunk_size[1] + 2, :chunk_size[2] + 2]
            # print chunk_grid.shape, self.solid.shape
            # print 'Calculating solid:', time.clock() - t

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

        t = time.clock()
        num_neighbors = scipy.ndimage.convolve(np.int_(self.solid), np.array((
            ((0, 0, 0), (0, 1, 0), (0, 0, 0)),
            ((0, 1, 0), (1, 0, 1), (0, 1, 0)),
            ((0, 0, 0), (0, 1, 0), (0, 0, 0))
        )), mode='constant', cval=10)
        interesting = self.solid & (num_neighbors < 6)
        self.visible = []
        for pos in np.transpose(np.nonzero(interesting)):
            world_pos = self.world_pos + pos - 1
            col = (perlin(0, *world_pos / color_scale, octaves=color_octaves) / 2 + .5,
                   perlin(1, *world_pos / color_scale, octaves=color_octaves) / 2 + .5,
                   perlin(2, *world_pos / color_scale, octaves=color_octaves) / 2 + .5)
            self.visible.append((pos - 1, col))
        # print 'Calculating visible:', time.clock() - t

        if not self.visible:
            self.is_empty = True
            return
        self.is_empty = False

        t = time.clock()
        self.vbo_data = []
        for pos, col in self.visible:
            # if random.random() < .1:
            self.vbo_data += self._cube_data(pos, col)
        self.vbo_data = np.fromiter(chain.from_iterable(self.vbo_data), dtype=np.float32)
        # print 'Creating vbo data:', time.clock() - t

        self.vbo = None

        # print self.vbo_data
        print len(self.visible), 'visible blocks'

    def is_solid(self, pos):
        if self.uniform is not None:
            return self.uniform
        return self.solid[pos[0] + 1, pos[1] + 1, pos[2] + 1]

    @staticmethod
    def create_shaders():
        vertex_shader = shaders.compileShader("""
            float end_fog = 1000.0;
            vec4 fog_color = vec4(0, .5, 1, 1);
            void main() {
                gl_Position = ftransform();
                float fog = clamp((end_fog - abs(gl_Position.z))/end_fog, 0, 1);
                gl_FrontColor = mix(fog_color, gl_Color, fog);
            }""", GL_VERTEX_SHADER)
        fragment_shader = shaders.compileShader("""
            void main() {
                gl_FragColor = gl_Color;
            }""", GL_FRAGMENT_SHADER)
        Chunk.shader = shaders.compileProgram(vertex_shader, fragment_shader)

    def draw(self):
        if self.is_empty: return
        if self.vbo is None: self.vbo = vbo.VBO(self.vbo_data)
        shaders.glUseProgram(Chunk.shader)
        self.vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        glVertexPointer(3, GL_FLOAT, 24, self.vbo)
        glColorPointer(3, GL_FLOAT, 24, self.vbo + 12)
        glDrawArrays(GL_QUADS, 0, self.vbo_data.size / 6)

        self.vbo.unbind()
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        shaders.glUseProgram(0)

    def _cube_data(self, pos, col):
        pos = np.asarray(pos)
        data = []

        if not self.is_solid(pos + (-1, 0, 0)):
            for v in (0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1):
                data.append(self.world_pos + pos + v)
                data.append(col)
        if not self.is_solid(pos + (1, 0, 0)):
            for v in (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1):
                data.append(self.world_pos + pos + v)
                data.append(col)

        if not self.is_solid(pos + (0, -1, 0)):
            for v in (0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1):
                data.append(self.world_pos + pos + v)
                data.append(col - vec(.01, .01, .01))
        if not self.is_solid(pos + (0, 1, 0)):
            for v in (0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1):
                data.append(self.world_pos + pos + v)
                data.append(col - vec(.01, .01, .01))

        if not self.is_solid(pos + (0, 0, -1)):
            for v in (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0):
                data.append(self.world_pos + pos + v)
                data.append(col - vec(.03, .03, .03))
        if not self.is_solid(pos + (0, 0, 1)):
            for v in (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1):
                data.append(self.world_pos + pos + v)
                data.append(col + vec(.03, .03, .03))

        return data


def _generate_chunk_process(chunk_loc):
    return chunk_loc, Chunk(chunk_loc)


calculate_solid_1 = np.vectorize(lambda x, y, z: - z * land_scale / land_height +
                                                 perlin(-1, x, y, z, octaves=land_octaves))


def calculate_solid(pos):
    return calculate_solid_1(*pos / land_scale)
