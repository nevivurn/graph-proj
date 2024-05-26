from pyglet import gl
from pyglet.graphics import Group
from pyglet.graphics.shader import ShaderProgram, Shader
from pyglet.math import Vec2, Vec3

class Model:
    def __init__(self, obj):
        self.meshes = obj.meshes

    def step2(self, order=0, batch=None, parent=None):
        groups = []

        for mesh in self.meshes:
            group = Step2(mesh, order, parent)

            tangents = []
            for i in range(len(mesh.vs) // 9):
                v0 = Vec3(*mesh.vs[9 * i + 0:9 * i + 3])
                v1 = Vec3(*mesh.vs[9 * i + 3:9 * i + 6])
                v2 = Vec3(*mesh.vs[9 * i + 6:9 * i + 9])

                c0 = Vec2(*mesh.vts[6 * i + 0:6 * i + 2])
                c1 = Vec2(*mesh.vts[6 * i + 2:6 * i + 4])
                c2 = Vec2(*mesh.vts[6 * i + 4:6 * i + 6])

                d1 = v1 - v0
                d2 = v2 - v0
                dc1 = c1 - c0
                dc2 = c2 - c0

                tan = (d1 * dc2.y - d2 * dc1.y)
                tan = tan.normalize()
                tangents.extend([*tan[:]] * 3)

            verts = {
                'in_pos': ('f', mesh.vs),
                'in_texcoord': ('f', mesh.vts),
                'in_norm': ('f', mesh.vns),
                'in_tangent': ('f', tangents),
            }
            verts = {k: v for k, v in verts.items() if k in group.program.attributes}

            group.program.vertex_list(
                len(mesh.vs) // 3, gl.GL_TRIANGLES, batch, group,
                **verts,
            )
            groups.append(group)

        return groups

class ModelGroup(Group):
    def __init__(self, mesh, order=0, parent=None):
        super().__init__(order, parent)
        self.mesh = mesh
        self.program = ShaderProgram(
            Shader(self.vert_source, 'vertex'),
            Shader(self.frag_source, 'fragment'),
        )
        self.mode = 0

    @property
    def view_pos(self):
        return self._view_pos

    @view_pos.setter
    def view_pos(self, pos):
        self._view_pos = Vec3(*pos)

    def set_state(self):
        self.program.use()

        if 'mode' in self.program.uniforms:
            self.program['mode'] = self.mode
        if self.mode == 0:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
            gl.glDisable(gl.GL_CULL_FACE)
        else:
            gl.glEnable(gl.GL_CULL_FACE)

        if 'view_pos' in self.program.uniforms:
            self.program['view_pos'] = self._view_pos

        if 'mat_ka' in self.program.uniforms:
            self.program['mat_ka'] = self.mesh.material.ka
        if 'mat_kd' in self.program.uniforms:
            self.program['mat_kd'] = self.mesh.material.kd
        if 'mat_ks' in self.program.uniforms:
            self.program['mat_ks'] = self.mesh.material.ks
        if 'mat_ns' in self.program.uniforms:
            self.program['mat_ns'] = self.mesh.material.ns

        textures = [
            self.mesh.material.ka_map,
            self.mesh.material.kd_map,
            self.mesh.material.ks_map,
            self.mesh.material.ns_map,
            self.mesh.material.bump_map,
        ]

        for i, tex in enumerate(textures):
            gl.glActiveTexture(gl.GL_TEXTURE0 + i)
            gl.glBindTexture(tex.target, tex.id)

    def unset_state(self):
        self.program.stop()

    def __eq__(self, other):
        return (self.__class__ is other.__class__) and self.mesh.name == other.mesh.name

    def __hash__(self):
        return hash(self.mesh.name)

class Step2(ModelGroup):
    vert_source = '''#version 330 core
    in vec3 in_pos;
    in vec2 in_texcoord;
    in vec3 in_norm;
    in vec3 in_tangent;

    out vec3 frag_pos;
    out vec2 frag_texcoord;
    out mat3 frag_tbn;

    uniform WindowBlock {
        mat4 projection;
        mat4 view;
    } window;

    void main() {
        gl_Position = window.projection * window.view * vec4(in_pos, 1.0f);
        frag_texcoord = in_texcoord;
        frag_tbn = mat3(
            normalize(in_tangent),
            normalize(cross(in_norm, in_tangent)),
            normalize(in_norm)
        );
    }
    '''

    frag_source = '''#version 440 core
    in vec3 frag_pos;
    in vec2 frag_texcoord;
    in mat3 frag_tbn;

    out vec4 out_color;

    uniform int mode;

    uniform vec3 view_pos;

    uniform vec3 mat_ka;
    uniform vec3 mat_kd;
    uniform vec3 mat_ks;
    uniform float mat_ns;

    layout(binding=0) uniform sampler2D mat_ka_map;
    layout(binding=1) uniform sampler2D mat_kd_map;
    layout(binding=2) uniform sampler2D mat_ks_map;
    layout(binding=3) uniform sampler2D mat_ns_map;
    layout(binding=4) uniform sampler2D mat_bump_map;

    // far away light
    const vec3 light_pos = vec3(1e3, 1e3, 1e3);
    const float light_pow = 5e6;
    const float amb_pow = 0.2f;

    void main() {
        // normal mapping
        vec3 norm = frag_tbn[2];
        if (mode == 3) {
            norm = texture(mat_bump_map, frag_texcoord).rgb;
            norm = normalize(norm * 2.0f - 1.0f);
            norm = normalize(frag_tbn * norm);
        }

        // direction vectors
        vec3 light_dir = normalize(light_pos - frag_pos);
        vec3 reflect_dir = reflect(-light_dir, normalize(norm));
        vec3 view_dir = normalize(view_pos - frag_pos);

        // attenuation
        float attn = 1.0f / pow(distance(light_pos, frag_pos), 2);

        vec3 base_color = vec3(0.5f);
        vec3 k_spc = vec3(0.8f);
        float shin = 4;
        if (mode >= 2) {
            base_color = mat_kd * texture(mat_kd_map, frag_texcoord).rgb;
            base_color *= texture(mat_ka_map, frag_texcoord).rgb;

            k_spc = mat_ks * texture(mat_ks_map, frag_texcoord).rgb;
            shin = mat_ns / texture(mat_ns_map, frag_texcoord).r;
        }

        float lambertian = max(dot(light_dir, norm), 0.0f);

        vec3 l_amb = amb_pow * mat_ka * base_color;
        vec3 l_dif = light_pow * attn * base_color * lambertian;
        vec3 l_spc = vec3(0.0f);
        if (lambertian > 0.0f)
            l_spc = light_pow * attn * k_spc * pow(max(dot(reflect_dir, view_dir), 0.0f), shin);

        vec3 intensity = l_amb + l_dif + l_spc;

        out_color = vec4(0, 0, 1, 1);
        if (mode >= 1) {
            out_color = vec4(intensity, 1.0f);
        }
    }
    '''
