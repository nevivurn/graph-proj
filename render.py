from pyglet import app, graphics, text, window
from pyglet.gl import *
from pyglet.math import Vec3, Vec4, Mat4

class RenderWindow(window.Window):
    def __init__(self):
        try:
            # try MSAA
            config = Config(
                sample_buffers=1, samples=4,
                double_buffer=True, depth_size=24,
            )
            super().__init__(800, 800, resizable=True, style=self.WINDOW_STYLE_DIALOG, config=config)
        except window.NoSuchConfigException:
            print('disabling MSAA')
            super().__init__(800, 800, resizable=True)

        glEnable(GL_DEPTH_TEST)
        glPointSize(5)
        self.wireframe = False

        self.batch = graphics.Batch()

        self.cam_pos = Vec3(10, 10, 10)
        # up, negative cancels out
        self.cam_up = self.cam_pos.cross(Vec3(0, 1, 0)).cross(self.cam_pos).normalize()

        # listen for keys
        self.keys = window.key.KeyStateHandler()
        self.push_handlers(self.keys)

    def set_shape(self, shape):
        self.shape = shape

    def run(self):
        # set initial view matrices
        self.update_matrices()
        app.run()

    def on_resize(self, width, height):
        self.update_matrices()
        super().on_resize(width, height)

    def on_draw(self):
        self.clear()
        self.batch.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        self.shape.on_click(self, x, y)

    def on_key_press(self, symbol, modifiers):
        if symbol == window.key.ESCAPE:
            self.close()
        if symbol == window.key.SPACE:
            self.wireframe = not self.wireframe
            if self.wireframe:
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            else:
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    # look or drag items
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        look_speed = 0.01

        y_vec = self.cam_up.normalize()
        x_vec = self.cam_pos.cross(y_vec).normalize()

        if buttons & window.mouse.RIGHT:
            cam_4 = Vec4(*self.cam_pos, 0)
            up_4 = Vec4(*self.cam_up, 0)

            rot_mat = Mat4.from_rotation(dy * look_speed, x_vec)
            rot_mat = Mat4.from_rotation(dx * look_speed, y_vec) @ rot_mat

            cam_4 = rot_mat @ cam_4
            up_4 = rot_mat @ up_4

            self.cam_pos = Vec3(*cam_4[:3])
            self.cam_up = Vec3(*up_4[:3])
            self.update_matrices()
        elif buttons & window.mouse.LEFT:
            # selection needs reference to window to calculate rays and stuff
            self.shape.on_drag(self, dx, dy)

    # "zoom" camera, move forward/backward
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        scroll_speed = 1

        f_vec = -self.cam_pos.normalize()
        upd = self.cam_pos + f_vec * scroll_speed * scroll_y

        # prevent flipping
        if upd.dot(f_vec) < 0:
            self.cam_pos = upd

        self.update_matrices()

    def update_matrices(self):
        self.view_mat = Mat4.look_at(self.cam_pos, Vec3(0, 0, 0), self.cam_up)
        self.proj_mat = Mat4.perspective_projection(self.width / self.height, .1, 100)

        self.shape.program['proj_mat'] = self.proj_mat
        self.shape.program['view_mat'] = self.view_mat
