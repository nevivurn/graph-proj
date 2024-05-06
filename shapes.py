import math

from pyglet import graphics
from pyglet.graphics import shader
from pyglet.gl import *
from pyglet.math import Vec2, Vec3, Vec4

vert_shader = '''
#version 330 core

uniform mat4 view_mat;
uniform mat4 proj_mat;

in vec3 in_pos;
in vec3 in_norm;
in vec4 in_color;

out vec4 frag_color;
out vec3 frag_norm;

void main()
{
    gl_Position = proj_mat * view_mat * vec4(in_pos, 1.0f);
    frag_norm = in_norm;
    frag_color = in_color;
}
'''

frag_shader = '''
#version 330 core

in vec4 frag_color;
in vec3 frag_norm;

out vec4 out_color;

void main()
{
    vec3 norm = normalize(frag_norm);
    vec3 light = vec3(0.0f, 1.0f, 0.0f);

    // we take the abs because patches may be flipped
    // has the effect of lighting from both above and below
    float diff = max(abs(dot(norm, light)), 0.0f);
    float intensity = 0.1f + 0.9f * diff;

    out_color = vec4(frag_color.rgb * intensity, frag_color.a);
}
'''

program = shader.ShaderProgram(
    shader.Shader(vert_shader, 'vertex'),
    shader.Shader(frag_shader, 'fragment'),
)

def flatten(vecs):
    return [c for v in vecs for c in v]

def repeat(e, dims):
    if len(dims) == 0:
        return e
    return [repeat(e, dims[1:]) for _ in range(dims[0])]

class Shape:
    def __init__(self, batch, group):
        self.program = program
        self.batch = batch
        self.group = graphics.ShaderGroup(program, parent=group)

    def _create_vlist(self):
        raise NotImplementedError
    def _update_vertices(self, vertices):
        self._vlist.in_pos[:] = vertices

    # handle window events
    def on_click(self, window, x, y):
        pass
    def on_drag(self, window, dx, dy):
        pass

class Points(Shape):
    def __init__(self, batch, group, vertices, colors):
        super().__init__(batch, group)
        self.vertices = vertices
        self.colors = colors
        self._create_vlist()

    def _create_vlist(self):
        self._vlist = program.vertex_list_indexed(
            len(self.vertices), GL_POINTS,
            batch=self.batch, group=self.group,
            indices=list(range(len(self.vertices))),
            in_pos=('f', flatten(self.vertices)),
            in_norm=('f', (0, 1, 0) * len(self.vertices)),
            in_color=('f', flatten(self.colors)),
        )

class Grid(Shape):
    def __init__(self, batch, group, vertices, colors):
        super().__init__(batch, group)
        self.vertices = vertices
        self.colors = colors
        self._create_vlist()

    def _create_vlist(self):
        indices = []
        h, w = len(self.vertices), len(self.vertices[0])
        for i in range(h):
            for j in range(w-1):
                indices.append(i*w + j)
                indices.append(i*w + j+1)
        for j in range(w):
            for i in range(h-1):
                indices.append(i*w + j)
                indices.append((i+1)*w + j)

        self._vlist = program.vertex_list_indexed(
            w*h, GL_LINES,
            batch=self.batch, group=self.group,
            indices=indices,
            in_pos=('f', flatten(flatten(self.vertices))),
            in_norm=('f', (0, 1, 0) * h * w),
            in_color=('f', flatten(flatten(self.colors))),
        )

class Surface(Shape):
    def __init__(self, batch, group, indices, vertices, colors):
        super().__init__(batch, group)
        self.indices = indices
        self.vertices = vertices
        self.colors = colors

        self._create_vlist()

    def write_obj(self, file):
        for row in self.vertices:
            for v in row:
                print(f'v {v.x} {v.y} {v.z}', file=file)
        for i in range(0, len(self.indices), 3):
            print(f'f {" ".join(map(lambda x: str(x + 1), self.indices[i:i+3]))}', file=file)

    def _compute_normals(self):
        n, m = len(self.vertices), len(self.vertices[0])
        norms = [Vec3() for _ in range(m*n)]

        for i in range(0, len(self.indices), 3):
            i1, i2, i3 = map(lambda j: j//m, self.indices[i:i+3])
            j1, j2, j3 = map(lambda j: j%m, self.indices[i:i+3])

            v1, v2, v3 = self.vertices[i1][j1], self.vertices[i2][j2], self.vertices[i3][j3]
            norm = (v2 - v1).cross(v3 - v1)

            norms[i1*m + j1] += norm
            norms[i2*m + j2] += norm
            norms[i3*m + j2] += norm

        norms = [norm.normalize() for norm in norms]
        return norms

    def _update_vertices(self, vertices):
        # update vertices, mainly for writing obj
        i, j = 0, 0
        for v in range(0, len(vertices), 3):
            if len(self.vertices[i]) == j:
                i, j = i+1, 0
            self.vertices[i][j] = Vec3(*vertices[v:v+3])
            j += 1

        super()._update_vertices(vertices)
        self._vlist.in_norm[:] = flatten(self._compute_normals())

    def _create_vlist(self):
        h, w = len(self.vertices), len(self.vertices[0])
        self._vlist = program.vertex_list_indexed(
            w*h, GL_TRIANGLES,
            batch=self.batch, group=self.group,
            indices=self.indices,
            in_pos=('f', flatten(flatten(self.vertices))),
            in_norm=('f', flatten(self._compute_normals())),
            in_color=('f', flatten(flatten(self.colors))),
        )

class GridSurface(Surface):
    def __init__(self, batch, group, vertices, colors):
        indices = self._compute_indices(vertices)
        super().__init__(batch, group, indices, vertices, colors)

    def _compute_indices(self, vertices):
        h, w = len(vertices), len(vertices[0])
        indices = []
        for i in range(h-1):
            for j in range(w-1):
                indices.append(i*w + j)
                indices.append(i*w + j+1)
                indices.append((i+1)*w + j+1)

                indices.append((i+1)*w + j+1)
                indices.append((i+1)*w + j)
                indices.append(i*w + j)
        return indices

class ParamSurface(Shape):
    def __init__(self, batch, group, control_points, segments):
        super().__init__(batch, group)

        self.control_points = control_points
        self.segments = segments
        surface_points = self._compute_surface()

        c_point_color = Vec4(1, 1, 1, 1)
        c_grid_color = Vec4(1, 0, 0, 1)

        s_grid_color = Vec4(.5, .5, .5, .8)
        s_color = Vec4(0, 1, 0, 1)

        self.control_group = graphics.Group(order=2, parent=self.group)
        self.overlay_group = graphics.Group(order=1, parent=self.group)
        self.surface_group = graphics.Group(order=0, parent=self.group)

        self.child_control_points = Points(
            batch, self.control_group,
            flatten(control_points),
            repeat(c_point_color, [len(control_points) * len(control_points[0])]),
        )
        self.child_control_grid = Grid(
            batch, self.control_group,
            control_points,
            repeat(c_grid_color, [len(control_points), len(control_points[0])]),
        )
        self.child_surface_grid = Grid(
            batch, self.overlay_group,
            surface_points,
            repeat(s_grid_color, [len(surface_points), len(surface_points[0])]),
        )
        self.child_surface = GridSurface(
            batch, self.surface_group,
            surface_points,
            repeat(s_color, [len(surface_points), len(surface_points[0])]),
        )

        self.selected_point = None

    def write_obj(self, file):
        self.child_surface.write_obj(file)

    def _compute_surface(self):
        raise NotImplementedError

    # find closest point, record index
    def on_click(self, window, x, y):
        x = x / (window.width/2) - 1
        y = y / (window.height/2) - 1
        cursor = Vec2(x, y)

        min_dist = None
        min_point = None

        for i, row in enumerate(self.control_points):
            for j, p in enumerate(row):
                # project point to screen
                pos = window.proj_mat @ window.view_mat @ Vec4(*p, 1)
                pos = Vec2(pos.x, pos.y) / pos.w

                # only select visible points
                if not (-1 < pos.x < 1 and -1 < pos.y < 1):
                    continue

                # distance from cursor to point, on screen
                # does not take aspect ratio into account, but good enough
                dist = cursor.distance(pos)

                if min_dist is None or dist < min_dist:
                    min_dist = dist
                    min_point = (i, j)

        self.selected_point = min_point

    # move selected point
    def on_drag(self, window, dx, dy):
        if self.selected_point is None:
            return

        drag_speed = 0.01

        x_vec = -window.cam_pos.cross(window.cam_up).normalize()
        y_vec = -x_vec.cross(window.cam_pos).normalize()
        x_vec *= drag_speed * dx
        y_vec *= drag_speed * dy

        self.control_points[self.selected_point[0]][self.selected_point[1]] += x_vec + y_vec
        self._update()

    def _update(self):
        surface_points = self._compute_surface()

        flat_control_p = flatten(flatten(self.control_points))
        flat_surface_p = flatten(flatten(surface_points))

        self.child_control_points._update_vertices(flat_control_p)
        self.child_control_grid._update_vertices(flat_control_p)
        self.child_surface_grid._update_vertices(flat_surface_p)
        self.child_surface._update_vertices(flat_surface_p)

class BezierSurface(ParamSurface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _compute_surface(self):
        verts = []
        for u in range(self.segments+1):
            row = []
            for v in range(self.segments+1):
                row.append(self._compute_bezier(u/self.segments, v/self.segments))
            verts.append(row)
        return verts

    def _compute_bezier(self, u, v):
        n = len(self.control_points) - 1
        m = len(self.control_points[0]) - 1
        p = Vec3()

        for i in range(n+1):
            bi = self._bernstein(n, i, u)
            for j in range(n+1):
                bj = self._bernstein(m, j, v)
                p += self.control_points[i][j] * bi * bj

        return p

    def _bernstein(self, n, i, u):
        return math.comb(n, i) * u**i * (1-u)**(n-i)

class BsplineSurface(ParamSurface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _compute_surface(self):
        verts = []
        for u in range(self.segments+1):
            row = []
            for v in range(self.segments+1):
                row.append(self._compute_bspline(u/self.segments, v/self.segments))
            verts.append(row)
        return verts

    def _compute_bspline(self, u, v):
        n = len(self.control_points) - 1
        m = len(self.control_points[0]) - 1
        p = Vec3()

        for i in range(n+1):
            bi = self._basis(i, u)
            for j in range(n+1):
                bj = self._basis(j, v)
                p += self.control_points[i][j] * bi * bj

        return p

    def _basis(self, i, t):
        if i == 0:
            v = -t**3 + 3*t**2 - 3*t + 1
        elif i == 1:
            v = 3*t**3 - 6*t**2 + 4
        elif i == 2:
            v = -3*t**3 + 3*t**2 + 3*t + 1
        elif i == 3:
            v = t**3
        return v/6
