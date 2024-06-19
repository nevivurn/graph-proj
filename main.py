#!/usr/bin/env python

import os
import multiprocessing as mp

from numba import njit
import numpy as np

from PIL import Image

from scene import Scene, Ray, ray_intersect
from utils import *


# debug flag
DEBUG = os.getenv('DEBUG') == '1'

# render globals
workers = int(os.getenv('WORKERS', 1))
image_width = int(os.getenv('IMAGE_WIDTH', 200))
image_height = int(os.getenv('IMAGE_HEIGHT', 200))
max_samples = int(os.getenv('MAX_SAMPLES', 100))
max_depth = int(os.getenv('MAX_DEPTH', 5))

# camera globals
cam_pos = vec3(278, 278, -800)
cam_tgt = vec3(278, 278, 0)
cam_up = vec3(0, 1, 0)

# projection globals
cam_near = 1
cam_v_width = np.deg2rad(40 / 2) * cam_near * 2
cam_v_height = cam_v_width * image_height / image_width

# lighting globals
background = vec3(0, 0, 0)


@njit
def ray_color(depth, scene, ray):
    # start off with background
    if depth >= max_depth:
        # recursion limit
        return background

    ok, hit, mat_spec = ray_intersect(ray, scene, 1e-3, np.inf)

    if not ok:
        # we hit nothing
        return background

    # material scattering
    mat_type, mat_id = mat_spec
    if mat_type == 'lambertian':
        mat = scene.mat_lambertians[mat_id]
        mat_ok, attn, new_ray = mat.scatter(ray, hit)
    elif mat_type == 'metal':
        mat = scene.mat_metals[mat_id]
        mat_ok, attn, new_ray = mat.scatter(ray, hit)
    elif mat_type == 'dielectric':
        mat = scene.mat_dielectrics[mat_id]
        mat_ok, attn, new_ray = mat.scatter(ray, hit)
    elif mat_type == 'light':
        mat = scene.mat_lights[mat_id]
        mat_ok, attn, new_ray = mat.scatter(ray, hit)

    if not mat_ok:
        # material couldn't scatter any light
        return attn

    return attn * ray_color(depth + 1, scene, new_ray)


@njit
def render(scene, samples):
    du = cam_v_width / image_width
    dv = cam_v_height / image_height

    w = cam_pos - cam_tgt
    w = w / np.linalg.norm(w)
    u = np.cross(cam_up, w)
    u = u / np.linalg.norm(u)
    v = np.cross(w, u)

    vp_corner = cam_pos - w * cam_near - u * cam_v_width / 2 - v * cam_v_height / 2
    vp_corner += u * du / 2 + v * dv / 2

    image = np.zeros((image_width, image_height, 3), dtype=np.float64)
    aanoise = np.random.rand(samples, 2) - 0.5

    for a in range(samples):
        for i in range(image_width):
            for j in range(image_height):
                pu = (i + aanoise[a, 0]) * du * u
                pv = (j + aanoise[a, 1]) * dv * v

                pos = vp_corner + pu + pv
                dir = pos - cam_pos

                ray = Ray(cam_pos, dir)
                col = ray_color(0, scene, ray)
                image[i, j] += col

                if DEBUG:
                    print('done', a, i, j)

    return image


@njit
def combine(image):
    return np.sum(image, 0) / max_samples


def worker(q, samples):
    scene = Scene()
    q.put(render(scene, samples))


def main():
    samples_per = max_samples // workers

    print('WORKERS', workers)
    print('IMAGE_WIDTH', image_width)
    print('IMAGE_HEIGHT', image_height)
    print('MAX_SAMPLES', max_samples)
    print('MAX_DEPTH', max_depth)

    q = mp.Queue()
    procs = []
    for i in range(workers):
        samples = samples_per + (1 if i < max_samples % workers else 0)
        p = mp.Process(target=worker, args=(q, samples))
        procs.append(p)
        p.start()

    image = np.zeros((image_width, image_height, 3), dtype=np.float64)
    for i in range(workers):
        image += q.get()
    for i, p in enumerate(procs):
        p.join()
        print(f'worker {i} done')

    print('combining images')
    image /= max_samples
    image = np.clip(image, 0, 1)
    image = np.sqrt(image)

    image = np.transpose(image, (1, 0, 2))
    image = np.flipud(image)

    img = Image.fromarray(np.uint8(image * 255))
    img.save('output.png')


if __name__ == '__main__':
    main()
