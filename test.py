import io

from pyglet.image import SolidColorImagePattern
from pyglet.model.codecs.obj import Mesh

from model import Model


class TestModel(Model):
    def __init__(self):
        color = (1, 0, 0, 1)
        ka = (0.1, 0.1, 0.1, 1)
        kd = (0.5, 0.5, 0.5, 1)
        ks = (0.8, 0.8, 0.8, 1)
        ns = (1/4, 1/4, 1/4, 1)
        norm = (0, 0, 1, 1)

        color = [int(255 * c) for c in color]
        ka = [int(255 * c) for c in ka]
        kd = [int(255 * c) for c in kd]
        ks = [int(255 * c) for c in ks]
        ns = [int(255 * c) for c in ns]
        norm = [int(255 * c) for c in norm]

        color = SolidColorImagePattern(color).create_image(1, 1).get_texture()
        ka = SolidColorImagePattern(ka).create_image(1, 1).get_texture()
        kd = SolidColorImagePattern(kd).create_image(1, 1).get_texture()
        ks = SolidColorImagePattern(ks).create_image(1, 1).get_texture()
        ns = SolidColorImagePattern(ns).create_image(1, 1).get_texture()
        norm = SolidColorImagePattern(norm).create_image(2048, 2048).get_texture()

        mesh = Mesh('test')
        mesh.vertices = [
            -1, 0, -1,
            -1, 0, 1,
            1, 0, -1,

            1, 0, 1,
            1, 0, -1,
            -1, 0, 1,
        ]
        mesh.normals = [0, 1, 0] * 6
        mesh.tex_coords = [
            0, 0,
            1, 0,
            0, 1,

            1, 1,
            0, 1,
            1, 0,
        ]

        self.mesh = mesh
        self.tex_color = color
        self.tex_ao = ka
        self.tex_roughness = ns
        self.tex_specular = ks
        self.tex_normal = norm
