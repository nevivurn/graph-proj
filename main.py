#!/usr/bin/env python3

import sys

from pyglet.math import Vec3, Vec4

from render import RenderWindow
from shapes import Surface, BezierSurface, BsplineSurface, repeat
from model import Model

def usage():
    print(f'usage: {sys.argv[0]} {{bezier | bspline | catmullclark}} <count> <input.obj> [output.obj]')
    sys.exit(1)

def run(argv):
    if len(sys.argv) < 4:
        usage()

    mode = sys.argv[1]
    count = int(sys.argv[2])
    filename = sys.argv[3]

    if mode not in {'bezier', 'bspline', 'catmullclark'}:
        usage()
    if mode == 'catmullclark' and count < 0:
        usage()
    if (mode == 'bezier' or mode == 'bspline') and count < 1:
        usage()

    print(f'loading {filename}')
    with open(filename) as f:
        model = Model.from_obj(f)

    window = RenderWindow()
    window.set_visible(False)

    if mode == 'catmullclark':
        for i in range(count):
            print(f'Catmull-Clark round {i+1}/{count}')
            model = model.catmull_clark()

        shape = Surface(
            window.batch, None,
            model.indices, [model.verts],
            repeat(Vec4(0, 1, 0, 1), [1, len(model.verts)]),
        )

    elif mode == 'bezier' or mode == 'bspline':
        grid = model.grid_reconstruct()
        if mode == 'bezier':
            shape = BezierSurface(
                window.batch, None,
                grid, count,
            )
        elif mode == 'bspline':
            shape = BsplineSurface(
                window.batch, None,
                grid, count,
            )

    window.set_shape(shape)
    window.set_visible(True)
    window.run()

    if len(sys.argv) >= 5:
        out_filename = sys.argv[4]
        print(f'writing to {out_filename}')
        with open(out_filename, 'x') as f:
            shape.write_obj(f)

if __name__ == '__main__':
    run(sys.argv)
