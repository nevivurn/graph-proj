import pyglet
from pyglet.math import Mat4, Vec3

from render import RenderWindow
from primitives import Cube,Sphere
from control import Control

from skel import Joint, CustomJoint

import math


if __name__ == '__main__':
    width = 1280
    height = 720

    # Render window.
    renderer = RenderWindow(width, height, "Hello Pyglet", resizable=True)
    renderer.set_location(200, 200)

    # Keyboard/Mouse control. Not implemented yet.
    controller = Control(renderer)


    leg = Cube(Vec3(.5, 2, .5))
    ball = Sphere(30, 30, scale=.0)
    prev_joint = Joint(Mat4.from_translation(Vec3(0, -5, -3)), Mat4())
    prev_ind = renderer.add_shape(prev_joint, leg.vertices, leg.indices, leg.colors)
    for i in range(10):
        leg = Cube(Vec3(.5, 2-i*.2, .5))
        prev_joint = CustomJoint(Mat4.from_translation(Vec3(0, (2-i*.2)/2 + .3, 0)), Mat4(), 1/10, Vec3(0, 0, 1), prev_joint)
        prev_ind = renderer.add_shape(prev_joint, ball.vertices, ball.indices, ball.colors, prev_ind)
        prev_joint = Joint(Mat4.from_translation(Vec3(0, (2-i*.2)/2, 0)), Mat4(), prev_joint)
        prev_ind = renderer.add_shape(prev_joint, leg.vertices, leg.indices, leg.colors, prev_ind)

    #draw shapes
    renderer.run()
