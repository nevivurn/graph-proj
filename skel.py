import math

from pyglet.math import Mat4, Vec3


class Joint:
    def __init__(self, fixed_trans: Mat4, free_trans: Mat4, parent=None):
        self.fixed_trans = fixed_trans
        self.free_trans = free_trans
        self.parent = parent
        self.full_trans = None
        self.t = 0

    def get_transform(self):
        if not self.full_trans:
            if self.parent is None:
                self.full_trans = self.fixed_trans @ self.free_trans
            else:
                self.full_trans = self.parent.get_transform() @ self.fixed_trans @ self.free_trans
        return self.full_trans

    def unset_trans(self):
        self.full_trans = None

    def advance(self, dt):
        pass

class CustomJoint(Joint):
    def __init__(self, fixed_trans, free_trans, scale, axis, parent):
        super().__init__(fixed_trans, free_trans, parent)
        self.scale = scale
        self.axis = axis

    def advance(self, dt):
        self.t += dt * self.scale
        self.free_trans = Mat4.from_rotation(angle=math.sin(2*math.pi * self.t), vector=self.axis)
