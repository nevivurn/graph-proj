from pyglet import gl
from pyglet.graphics import Group
from pyglet.graphics.shader import ShaderProgram, Shader
from pyglet.math import Mat4, Vec2, Vec3
from pyglet.model.codecs.obj import parse_obj_file


class Model:
    def __init__(self, mesh_file, tex_color, tex_ao, tex_roughness, tex_specular, tex_normal):
        self.mesh = parse_obj_file('', file=mesh_file)[0]
        self.tex_color = tex_color
        self.tex_ao = tex_ao
        self.tex_roughness = tex_roughness
        self.tex_specular = tex_specular
        self.tex_normal = tex_normal

    def wireframe(self, order=0, batch=None, parent=None):
        group = WireframeGroup(self, order, parent)
        return group, group.program.vertex_list(
            len(self.mesh.vertices) // 3, gl.GL_TRIANGLES, batch, group,
            in_pos=('f', self.mesh.vertices),
        )

    def step1_gouraud(self, order=0, batch=None, parent=None):
        group = Step1GouraudGroup(self, order, parent)
        return group, group.program.vertex_list(
            len(self.mesh.vertices) // 3, gl.GL_TRIANGLES, batch, group,
            in_pos=('f', self.mesh.vertices),
            in_norm=('f', self.mesh.normals),
        )

    def step1_phong(self, order=0, batch=None, parent=None):
        group = Step1PhongGroup(self, order, parent)
        return group, group.program.vertex_list(
            len(self.mesh.vertices) // 3, gl.GL_TRIANGLES, batch, group,
            in_pos=('f', self.mesh.vertices),
            in_norm=('f', self.mesh.normals),
        )

    def step2(self, order=0, batch=None, parent=None):
        group = Step2(self, order, parent)

        tangents = []
        for i in range(len(self.mesh.vertices) // 9):
            v0 = Vec3(*self.mesh.vertices[9*i:9*i+3])
            v1 = Vec3(*self.mesh.vertices[9*i+3:9*i+6])
            v2 = Vec3(*self.mesh.vertices[9*i+6:9*i+9])

            c0 = Vec2(*self.mesh.tex_coords[6*i:6*i+2])
            c1 = Vec2(*self.mesh.tex_coords[6*i+2:6*i+4])
            c2 = Vec2(*self.mesh.tex_coords[6*i+4:6*i+6])

            d1 = v1 - v0
            d2 = v2 - v0
            dc1 = c1 - c0
            dc2 = c2 - c0

            tan = (d1 * dc2.y - d2 * dc1.y)
            tan = tan.normalize()
            tangents.extend([*tan[:]]*3)

        verts = {
            'in_pos': ('f', self.mesh.vertices),
            'in_norm': ('f', self.mesh.normals),
            'in_tangent': ('f', tangents),
            'in_texcoord': ('f', self.mesh.tex_coords),
        }
        verts = {k: v for k, v in verts.items() if k in group.program.attributes}

        return group, group.program.vertex_list(
            len(self.mesh.vertices) // 3, gl.GL_TRIANGLES, batch, group,
            **verts,
        )

class ModelGroup(Group):
    def __init__(self, model, order=0, parent=None):
        super().__init__(order, parent)
        self.model = model
        self.program = ShaderProgram(
            Shader(self.vert_source, 'vertex'),
            Shader(self.frag_source, 'fragment'),
        )

    @property
    def view_pos(self):
        return self._view_pos

    @view_pos.setter
    def view_pos(self, pos):
        self._view_pos = Vec3(*pos)

    def set_state(self):
        self.program.use()
        self.program['view_pos'] = self._view_pos

    def unset_state(self):
        self.program.stop()


class WireframeGroup(ModelGroup):
    vert_source = '''#version 330 core
    in vec3 in_pos;

    uniform WindowBlock {
        mat4 projection;
        mat4 view;
    } window;

    uniform vec3 view_pos;

    void main() {
        gl_Position = window.projection * window.view * vec4(in_pos, 1.0f);
    }
    '''

    frag_source = '''#version 330 core
    out vec4 out_color;

    void main() {
        out_color = vec4(0.0f, 0.0f, 1.0f, 1.0f);
    }
    '''

    def set_state(self):
        super().set_state()
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)

class Step1GouraudGroup(ModelGroup):
    vert_source = '''#version 330 core
    in vec3 in_pos;
    in vec3 in_norm;

    out vec4 frag_color;

    uniform WindowBlock {
        mat4 projection;
        mat4 view;
    } window;

    uniform vec3 view_pos;

    const vec3 light_pos = vec3(10.0f, 10.0f, 10.0f);
    const float light_pow = 40.0f;

    const vec3 k_amb = vec3(0.1f, 0.1f, 0.1f);
    const vec3 k_dif = vec3(0.5f, 0.5f, 0.5f);
    const vec3 k_spc = vec3(0.8f, 0.8f, 0.8f);
    const float shin = 4.0f;

    void main() {
        gl_Position = window.projection * window.view * vec4(in_pos, 1.0f);

        float light_dist = distance(light_pos, in_pos);
        vec3 light_dir = normalize(light_pos - in_pos);
        vec3 reflect_dir = reflect(-light_dir, normalize(in_norm));
        vec3 view_dir = normalize(view_pos - in_pos);

        float light_intensity = light_pow / (pow(light_dist, 2));

        vec3 intensity = k_amb + light_intensity * (
            k_dif * max(dot(light_dir, in_norm), 0.0f) +
            k_spc * pow(max(dot(reflect_dir, view_dir), 0.0f), shin)
        );
        frag_color = vec4(intensity, 1.0f);
    }
    '''

    frag_source = '''#version 330 core
    in vec4 frag_color;

    out vec4 out_color;

    void main() {
        out_color = frag_color;
    }
    '''

class Step1PhongGroup(ModelGroup):
    vert_source = '''#version 330 core
    in vec3 in_pos;
    in vec3 in_norm;

    out vec3 frag_pos;
    out vec3 frag_norm;

    uniform WindowBlock {
        mat4 projection;
        mat4 view;
    } window;

    void main() {
        gl_Position = window.projection * window.view * vec4(in_pos, 1.0f);
        frag_pos = in_pos;
        frag_norm = in_norm;
    }
    '''

    frag_source = '''#version 330 core
    in vec3 frag_pos;
    in vec3 frag_norm;

    out vec4 out_color;

    uniform vec3 view_pos;

    const vec3 light_pos = vec3(10.0f, 10.0f, 10.0f);
    const float light_pow = 40.0f;

    const vec3 k_amb = vec3(0.1f, 0.1f, 0.1f);
    const vec3 k_dif = vec3(0.5f, 0.5f, 0.5f);
    const vec3 k_spc = vec3(0.8f, 0.8f, 0.8f);
    const float shin = 4.0f;

    void main() {
        float light_dist = distance(light_pos, frag_pos);
        vec3 light_dir = normalize(light_pos - frag_pos);
        vec3 reflect_dir = reflect(-light_dir, normalize(frag_norm));
        vec3 view_dir = normalize(view_pos - frag_pos);

        float light_intensity = light_pow / (pow(light_dist, 2));
        float light_intensity = light_pow / (pow(light_dist, 2));

        vec3 intensity = k_amb + light_intensity * (
            k_dif * max(dot(light_dir, frag_norm), 0.0f) +
            k_spc * pow(max(dot(reflect_dir, view_dir), 0.0f), shin)
        );
        out_color = vec4(intensity, 1.0f);
    }
    '''

class Step2(ModelGroup):
    vert_source = '''#version 330 core
    in vec3 in_pos;
    in vec3 in_norm;
    in vec3 in_tangent;
    in vec2 in_texcoord;

    out vec3 frag_pos;
    out vec2 frag_texcoord;
    out mat3 frag_tbn;

    uniform WindowBlock {
        mat4 projection;
        mat4 view;
    } window;

    void main() {
        gl_Position = window.projection * window.view * vec4(in_pos, 1.0f);
        frag_pos = in_pos;
        frag_texcoord = in_texcoord;
        frag_tbn = mat3(
            in_tangent,
            cross(in_norm, in_tangent),
            in_norm
        );
    }
    '''

    frag_source = '''#version 440 core
    in vec3 frag_pos;
    in vec2 frag_texcoord;
    in mat3 frag_tbn;

    out vec4 out_color;

    layout(binding=0) uniform sampler2D tex_ao;
    layout(binding=1) uniform sampler2D tex_color;
    layout(binding=2) uniform sampler2D tex_roughness;
    layout(binding=3) uniform sampler2D tex_specular;
    layout(binding=4) uniform sampler2D tex_normal;

    uniform vec3 view_pos;

    // far away light
    const vec3 light_pos = vec3(1e3, 1e3, 1e3);
    const float light_pow = 4e6;

    void main() {
        // normal mapping
        vec3 norm = texture(tex_normal, frag_texcoord).rgb;
        norm = normalize(norm * 2.0f - 1.0f);
        norm = normalize(frag_tbn * norm);

        // direction vectors
        vec3 light_dir = normalize(light_pos - frag_pos);
        vec3 reflect_dir = reflect(-light_dir, normalize(norm));
        vec3 view_dir = normalize(view_pos - frag_pos);

        // attenuation
        float attn = 1.0f / pow(distance(light_pos, frag_pos), 2);

        // material properties
        vec3 base_color = texture(tex_color, frag_texcoord).rgb;
        vec3 k_amb = base_color * texture(tex_ao, frag_texcoord).rgb;
        vec3 k_dif = base_color;
        vec3 k_spc = texture(tex_specular, frag_texcoord).rgb;
        float shin = 1.0f / (texture(tex_roughness, frag_texcoord).r);

        float lambertian = max(dot(light_dir, norm), 0.0f);

        vec3 l_amb = k_amb * 0.5f;
        vec3 l_dif = light_pow * attn * k_dif * lambertian;
        vec3 l_spc = vec3(0.0f);
        if (lambertian > 0.0f)
            l_spc = light_pow * attn * k_spc * pow(max(dot(reflect_dir, view_dir), 0.0f), shin);

        vec3 intensity = l_amb + l_dif + l_spc;
        out_color = vec4(intensity, 1.0f);
    }
    '''

    def set_state(self):
        super().set_state()

        textures = [
            self.model.tex_ao,
            self.model.tex_color,
            self.model.tex_roughness,
            self.model.tex_specular,
            self.model.tex_normal,
        ]
        for i, tex in enumerate(textures):
            gl.glActiveTexture(gl.GL_TEXTURE0+i)
            gl.glBindTexture(tex.target, tex.id)
