import itertools
from itertools import chain

import numpy as np


def append(*args):
    return np.append((), args)


def flatten(listOfLists):
    return list(chain.from_iterable(listOfLists))


length = np.linalg.norm

length_squared = lambda a: np.sum(a * a)


def multi_range(lower_left, upper_right=None):
    if upper_right is None:
        upper_right = lower_left
        lower_left = [0] * len(upper_right)
    # print zip(lower_left, upper_right)
    return itertools.product(*(xrange(start, end) for start, end in zip(lower_left, upper_right)))


def vec(*args):
    return np.array(args)
