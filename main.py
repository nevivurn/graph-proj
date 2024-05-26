#!/usr/bin/env python3

import sys

from pyglet import app, clock, event, gl, resource
from pyglet.graphics import Batch
from pyglet.math import Mat4, Vec4, Vec3
from pyglet.window import key, Window

from model import Model
from obj import OBJModel

try:
    config = gl.Config(
        sample_buffers=1, samples=8,
        double_buffer=True, depth_size=24,
    )
    window = Window(width=1000, height=1000, resizable=False, visible=False, config=config)
except window.NoSuchConfigException:
    window = Window(width=1000, height=1000, resizable=False, visible=False)

batch = Batch()

@window.event
def on_resize(width, height):
    window.viewport = (0, 0, *window.get_framebuffer_size())
    window.projection = Mat4.perspective_projection(window.aspect_ratio, z_near=0.1, z_far=255)
    return event.EVENT_HANDLED

@window.event
def on_draw():
    window.clear()
    batch.draw()

animate = False

def update(dt):
    global groups, view_pos, animate

    if not animate:
        return

    dt *= 0.5
    rot = Mat4.from_rotation(dt, Vec3(1, 1, 0).normalize())

    new_pos = rot @ Vec4(*view_pos, 0)
    view_pos = Vec3(*new_pos[:3])
    window.view = Mat4.look_at(position=view_pos, target=Vec3(0, 0, 0), up=Vec3(0, 1, 0))

    for group in groups:
        group.view_pos = view_pos

@window.event
def on_key_press(symbol, modifiers):
    global animate

    if symbol == key.SPACE:
        animate = not animate
    elif symbol == key.PERIOD:
        animate = True
        update(1 / 60)
        animate = False
    elif symbol == key.COMMA:
        animate = True
        update(-1 / 60)
        animate = False

if __name__ == '__main__':
    resource.path = ['assets']
    resource.reindex()

    filename = sys.argv[1]
    view_pos = Vec3(*map(float, sys.argv[2:5]))

    #view_pos = Vec3(-10, 10, 10)
    obj = OBJModel(filename)
    groups = Model(obj).step2(batch=batch)
    mode = int(sys.argv[5])

    gl.glEnable(gl.GL_DEPTH_TEST)
    #gl.glEnable(gl.GL_CULL_FACE)

    #view_pos = Vec3(10, 10, 10)
    for group in groups:
        group.view_pos = view_pos
        group.mode = mode
    window.view = Mat4.look_at(position=view_pos, target=Vec3(0, 0, 0), up=Vec3(0, 1, 0))

    clock.schedule_interval(update, 1 / 60)

    window.set_visible()
    app.run()
