from numba import njit
import numpy as np


@njit
def vec3(x, y, z):
    return np.array([x, y, z], dtype=np.float64)


@njit
def unit_vector(v):
    return v / np.linalg.norm(v)


@njit
def random_unit_vector():
    vec = np.random.rand(3) * 2 - 1
    while np.linalg.norm(vec) > 1:
        vec = np.random.rand(3) * 2 - 1
    return unit_vector(vec)
