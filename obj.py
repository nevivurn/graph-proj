from dataclasses import dataclass, field

from pyglet import image, resource

Color = tuple[float, float, float]

@dataclass
class Material:
    name: str
    ka: Color = (1.0, 1.0, 1.0)
    kd: Color = (1.0, 1.0, 1.0)
    ks: Color = (1.0, 1.0, 1.0)
    ns: float = 100.0

    ka_map = None
    kd_map = None
    ks_map = None
    ns_map = None
    bump_map = None

class MaterialLibrary:
    materials: dict[str, Material]

    def __init__(self, res: str):
        self.materials: dict[str, Material] = {}

        cur_material = None
        with resource.file(res, 'r') as f:
            for line in f:
                split = line.strip().split()

                if len(split) == 0:
                    continue

                match split[0]:
                    case 'newmtl':
                        if cur_material is not None:
                            self.materials[cur_material.name] = cur_material
                        cur_material = Material(name=split[1])

                    case 'Ka':
                        cur_material.ka = tuple(map(float, split[1:]))
                    case 'Kd':
                        cur_material.kd = tuple(map(float, split[1:]))
                    case 'Ks':
                        cur_material.ks = tuple(map(float, split[1:]))
                    case 'Ns':
                        cur_material.ns = float(split[1])

                    case 'map_Ka':
                        cur_material.ka_map = resource.texture(split[-1])
                    case 'map_Kd':
                        cur_material.kd_map = resource.texture(split[-1])
                    case 'map_Ks':
                        cur_material.ks_map = resource.texture(split[-1])
                    case 'map_Ns':
                        cur_material.ns_map = resource.texture(split[-1])
                    case 'map_Bump':
                        cur_material.bump_map = resource.texture(split[-1])

        if cur_material is not None:
            self.materials[cur_material.name] = cur_material

@dataclass
class Mesh:
    name: str
    material: Material = None
    vs: list[float] = field(default_factory=list)
    vts: list[float] = field(default_factory=list)
    vns: list[float] = field(default_factory=list)

    def fill_textures(self) -> None:
        w = self.material.kd_map.width
        h = self.material.kd_map.height

        if self.material.ka_map is None:
            self.material.ka_map = image.create(w, h, image.SolidColorImagePattern((255, 255, 255, 255))).get_texture()
        if self.material.ns_map is None:
            self.material.ka_map = image.create(w, h, image.SolidColorImagePattern((0, 0, 0, 255))).get_texture()
        if self.material.ks_map is None:
            self.material.ks_map = image.create(w, h, image.SolidColorImagePattern((255, 255, 255, 255))).get_texture()
        if self.material.bump_map is None:
            self.material.bump_map = image.create(w, h, image.SolidColorImagePattern((0, 0, 255, 255))).get_texture()

class OBJModel:
    meshes: list[Mesh]

    def __init__(self, res: str):
        self.meshes = []

        vs = []
        vts = []
        vns = []

        mtl = None
        cur_mesh = None

        with resource.file(res, 'r') as f:
            for line in f:
                split = line.strip().split()
                if len(split) == 0:
                    continue

                match split[0]:
                    case 'mtllib':
                        mtl = MaterialLibrary(split[1])
                    case 'usemtl':
                        cur_mesh.material = mtl.materials[split[1]]
                    case 'o':
                        if cur_mesh is not None:
                            self.meshes.append(cur_mesh)
                        cur_mesh = Mesh(name=split[1])

                    case 'v':
                        vs.append(tuple(map(float, split[1:])))
                    case 'vt':
                        vts.append(tuple(map(float, split[1:3])))
                    case 'vn':
                        vns.append(tuple(map(float, split[1:])))

                    case 'f':
                        face = []
                        for f in split[1:]:
                            vi, vti, vni = map(lambda x: int(x) - 1, f.split('/'))
                            face.append((vi, vti, vni))

                        faces = [tuple(face[:3])]
                        if len(face) == 4:
                            faces.append(tuple(face[2:] + face[:1]))

                        for face in faces:
                            for vi, vti, vni in face:
                                cur_mesh.vs.extend(vs[vi])
                                cur_mesh.vts.extend(vts[vti])
                                cur_mesh.vns.extend(vns[vni])

        if cur_mesh is not None:
            self.meshes.append(cur_mesh)

        for mesh in self.meshes:
            mesh.fill_textures()
