import itertools
from itertools import chain

import numpy as np


def append(*args):
    return np.append((), args)


def flatten(listOfLists):
    return list(chain.from_iterable(listOfLists))


frustum = None


# This works by magic and arrays - don't question it too much
def frustum_intersects_aabbs(aabb_center, aabb_size):
    result = np.ones(aabb_center.shape[0], dtype=bool)
    for i in xrange(6):
        plane_vec4 = np.asarray(frustum.planes[i])
        plane_normal = plane_vec4[:3]
        d = np.dot(aabb_center, plane_normal)
        r = np.dot(aabb_size, np.abs(plane_normal))
        result &= (d + r) > -plane_vec4[3]
    return result


length = np.linalg.norm

length_squared = lambda a: np.sum(a * a)


def multi_range(lower_left, upper_right=None):
    if upper_right is None:
        upper_right = lower_left
        lower_left = [0] * len(upper_right)
    # print zip(lower_left, upper_right)
    return itertools.product(*(xrange(start, end) for start, end in zip(lower_left, upper_right)))

to_int = lambda x: np.int_(np.floor(x))

def vec(*args):
    return np.array(args)
