from numba import njit, typed, types
from numba.experimental import jitclass
import numpy as np

from utils import *

from collections import namedtuple

Hit = namedtuple('Hit', ['t', 'norm', 'front'])
noHit = Hit(np.inf, vec3(0, 0, 0), False)


@jitclass([('origin', types.float64[::1]), ('direction', types.float64[::1])])
class Ray:
    def __init__(self, origin, direction):
        self.origin = origin
        self.direction = direction

    def at(self, t):
        return self.origin + t * self.direction


@jitclass([('center', types.float64[:]), ('radius', types.float64)])
class Sphere:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def hit(self, ray):
        oc = self.center - ray.origin
        a = np.linalg.norm(ray.direction) ** 2
        h = np.dot(ray.direction, oc)
        c = np.linalg.norm(oc) ** 2 - self.radius ** 2

        disc = h ** 2 - a * c
        if disc < 0:
            return False, noHit

        sqrtd = np.sqrt(disc)

        root = (h - sqrtd) / a
        if root < 1e-3:
            root = (h + sqrtd) / a
            if root < 1e-3:
                return False, noHit

        pos = ray.at(root)

        t = root
        norm = unit_vector(pos - self.center)
        front = np.dot(ray.direction, norm) < 0
        if not front:
            norm = -norm

        return True, Hit(t, norm, front)


@jitclass([
    ('u', types.float64[::1]),
    ('v', types.float64[::1]),
    ('w', types.float64[::1]),
    ('norm', types.float64[::1]),
    ('Q', types.float64[::1]),
    ('D', types.float64),
])
class Quad:
    # actually a parallelogram
    def __init__(self, points):
        self.u = points[1] - points[0]
        self.v = points[2] - points[0]

        n = np.cross(self.u, self.v)
        self.w = n / np.dot(n, n)
        self.norm = unit_vector(n)

        self.Q = points[0]
        self.D = np.dot(self.norm, points[0])


@njit(fastmath=True)
def hit_quad(ray, quad):
    # intersect with plane
    denom = np.dot(quad.norm, ray.direction)

    # no plane intersection
    if np.fabs(denom) < 1e-8:
        return False, noHit

    t = (quad.D - np.dot(quad.norm, ray.origin)) / denom
    if t < 0:
        return False, noHit
    pos = ray.at(t)

    p = pos - quad.Q
    a = np.dot(quad.w, np.cross(p, quad.v))
    b = np.dot(quad.w, np.cross(quad.u, p))

    # out of quad
    if not (0 < a < 1 and 0 < b < 1):
        return False, noHit

    norm = quad.norm
    front = denom < 0
    if not front:
        norm = -norm

    return True, Hit(t, norm, front)


@jitclass([('albedo', types.float64[:])])
class Lambertian:
    def __init__(self, albedo):
        self.albedo = albedo

    def scatter(self, ray, hit):
        reflected = hit.norm + random_unit_vector()

        # degenerate rays
        if np.linalg.norm(reflected) < 1e-3:
            reflected = hit.norm

        return True, self.albedo, Ray(ray.at(hit.t), reflected)


@jitclass([('albedo', types.float64[:]), ('fuzz', types.float64)])
class Metal:
    def __init__(self, albedo, fuzz):
        self.albedo = albedo
        self.fuzz = fuzz

    def scatter(self, ray, hit):
        reflected = ray.direction - 2 * np.dot(ray.direction, hit.norm) * hit.norm
        reflected = unit_vector(reflected) + self.fuzz * random_unit_vector()

        if np.dot(reflected, hit.norm) <= 0:
            return False, vec3(0, 0, 0), ray

        return True, self.albedo, Ray(ray.at(hit.t), reflected)


@jitclass([('ref_idx', types.float64)])
class Dielectric:
    def __init__(self, ref_idx):
        self.ref_idx = ref_idx

    def scatter(self, ray, hit):
        ri = self.ref_idx
        if hit.front:
            ri = 1 / ri

        unit_dir = unit_vector(ray.direction)
        cos_theta = np.dot(-unit_dir, hit.norm)
        sin_theta = np.sqrt(1 - cos_theta ** 2)

        no_refract = ri * sin_theta > 1

        if no_refract or self.reflectance(cos_theta, ri) > np.random.uniform():
            direction = unit_dir - 2 * np.dot(unit_dir, hit.norm) * hit.norm
        else:
            perp = ri * (unit_dir + cos_theta * hit.norm)
            para = -np.sqrt(np.fabs(1 - np.linalg.norm(perp) ** 2)) * hit.norm
            direction = perp + para

        return True, vec3(1, 1, 1), Ray(ray.at(hit.t), direction)

    def reflectance(self, cos, ri):
        r0 = (1 - ri) / (1 + ri)
        r0 = r0 ** 2
        return r0 + (1 - r0) * (1 - cos) ** 5


@jitclass([('color', types.float64[:])])
class Light:
    def __init__(self, color):
        self.color = color

    def scatter(self, ray, hit):
        return False, self.color, ray


@jitclass([('pos', types.float64[:]), ('color', types.float64[:])])
class LightSource:
    def __init__(self, pos, color):
        self.pos = pos
        self.color = color


@jitclass([
    ('lights', types.ListType(LightSource.class_type.instance_type)),
    ('spheres', types.ListType(Sphere.class_type.instance_type)),
    ('sphere_mats', types.ListType(types.Tuple([types.string, types.int64]))),
    ('quads', types.ListType(Quad.class_type.instance_type)),
    ('quad_mats', types.ListType(types.Tuple([types.string, types.int64]))),
    ('mat_lambertians', types.ListType(Lambertian.class_type.instance_type)),
    ('mat_metals', types.ListType(Metal.class_type.instance_type)),
    ('mat_dielectrics', types.ListType(Dielectric.class_type.instance_type)),
    ('mat_lights', types.ListType(Light.class_type.instance_type)),
])
class Scene:
    def __init__(self):
        self.lights = typed.List([
            LightSource(vec3(0, 0, 0), vec3(0, 0, 0)),
        ])

        self.spheres = typed.List([
            Sphere(vec3(405, 100, 405), 100),
            Sphere(vec3(150, 100, 150), 100),
        ])
        self.sphere_mats = typed.List([
            ('metal', 0),
            ('dielectric', 0),
        ])

        self.quads = typed.List([
            Quad([vec3(555, 0, 0), vec3(555, 555, 0), vec3(555, 0, 555)]),
            Quad([vec3(0, 0, 0), vec3(0, 555, 0), vec3(0, 0, 555)]),
            Quad([vec3(343, 554, 332), vec3(213, 554, 332), vec3(343, 554, 227)]),
            Quad([vec3(0, 0, 0), vec3(555, 0, 0), vec3(0, 0, 555)]),
            Quad([vec3(555, 555, 555), vec3(0, 555, 555), vec3(555, 555, 0)]),
            Quad([vec3(0, 0, 555), vec3(555, 0, 555), vec3(0, 555, 555)]),

        ])
        self.quad_mats = typed.List([
            ('lambertian', 0),
            ('lambertian', 1),
            ('light', 0),
            ('lambertian', 2),
            ('lambertian', 2),
            ('lambertian', 2),
        ])

        self.mat_lambertians = typed.List([
            Lambertian(vec3(.12, .45, .15)),
            Lambertian(vec3(.65, .05, .05)),
            Lambertian(vec3(.73, .73, .73)),
        ])
        self.mat_metals = typed.List([
            Metal(vec3(0.8, 0.8, 0.8), 0),
            Metal(vec3(0.8, 0.6, 0.2), 1),
        ])
        self.mat_dielectrics = typed.List([
            Dielectric(1.5),
        ])
        self.mat_lights = typed.List([
            Light(vec3(15, 15, 15)),
        ])


@njit
def ray_intersect(ray, scene, min, max):
    ok_hit = False
    min_hit = noHit
    min_mat = ('', 0)

    for sphere, mat_spec in zip(scene.spheres, scene.sphere_mats):
        ok, hit = sphere.hit(ray)
        if not ok or not min < hit.t < max:
            continue

        if not ok_hit or hit.t < min_hit.t:
            min_hit = hit
            min_mat = mat_spec
        ok_hit = True

    for quad, mat_spec in zip(scene.quads, scene.quad_mats):
        ok, hit = hit_quad(ray, quad)
        if not ok or not min < hit.t < max:
            continue

        if not ok_hit or hit.t < min_hit.t:
            min_hit = hit
            min_mat = mat_spec
        ok_hit = True

    return ok_hit, min_hit, min_mat


@njit
def ray_intersect_light(ray, scene, min, max):
    for sphere in scene.spheres:
        ok, _ = sphere.hit
        if not ok or not min < hit.t < max:
            continue
        return True
    return False
