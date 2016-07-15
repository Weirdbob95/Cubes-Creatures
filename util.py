import itertools

import numpy as np


def append(*args):
    return np.append((), args)


def multi_range(lower_left, upper_right=None):
    if upper_right is None:
        upper_right = lower_left
        lower_left = [0] * len(upper_right)
    return itertools.product(*(xrange(start, end) for start, end in zip(lower_left, upper_right)))
