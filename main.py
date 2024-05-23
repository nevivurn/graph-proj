#!/usr/bin/env python3

from pyglet import app, clock, event, gl, image, resource
from pyglet.graphics import Batch
from pyglet.math import Mat4, Vec4, Vec3
from pyglet.window import key, Window

from model import Model, WireframeGroup
from test import TestModel

try:
    config = gl.Config(
        sample_buffers=1, samples=8,
        double_buffer=True, depth_size=24,
    )
    window = Window(width=800, height=800, resizable=False, visible=False, config=config)
except window.NoSuchConfigException:
    window = Window(width=800, height=800, resizable=False, visible=False)

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
    global group, animate

    if not animate:
        return

    dt *= 0.5
    rot = Mat4.from_rotation(dt, Vec3(0, 0, 1).normalize())

    new_pos = rot @ Vec4(*group.view_pos, 0)
    group.view_pos = Vec3(*new_pos[:3])
    window.view = Mat4.look_at(position=group.view_pos, target=Vec3(0, 0, 0), up=Vec3(0, 1, 0))

@window.event
def on_key_press(symbol, modifiers):
    global animate

    if symbol == key.SPACE:
        animate = not animate
    elif symbol == key.PERIOD:
        animate = True
        update(1/60)
        animate = False
    elif symbol == key.COMMA:
        animate = True
        update(-1/60)
        animate = False

if __name__ == '__main__':
    resource.path = ['assets']
    resource.reindex()

    tex_color = resource.texture('Free_rock_tex/Free_rock_Base_Color.jpg')
    tex_ao = resource.texture('Free_rock_tex/Free_rock_Mixed_AO.jpg')
    tex_roughness = resource.texture('Free_rock_tex/Free_rock_Roughness.jpg')
    tex_specular = resource.texture('Free_rock_tex/Free_rock_Specular.jpg')
    tex_normal = resource.texture('Free_rock_tex/Free_rock_Normal_OpenGL.jpg')

    with resource.file('Free_rock.obj') as obj_file:
        group, model = Model(
            obj_file,
            tex_color, tex_ao, tex_roughness, tex_specular, tex_normal,
        ).step2(batch=batch)

    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_CULL_FACE)

    group.view_pos = Vec3(-10, 10, 10)
    window.view = Mat4.look_at(position=group.view_pos, target=Vec3(0, 0, 0), up=Vec3(0, 1, 0))

    clock.schedule_interval(update, 1/60)

    window.set_visible()
    app.run()
