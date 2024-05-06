from typing import TextIO

from pyglet.math import Vec3

def sort_pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)

class Face:
    def __init__(self, verts: list[int]) -> None:
        self.verts = verts

        ext_verts = verts + [verts[0]]
        self.edges = []
        for i in range(len(ext_verts)-1):
            self.edges.append((ext_verts[i], ext_verts[i+1]))

class Model:
    def __init__(self, verts: list[Vec3], faces: list[list[int]]) -> None:
        self.verts = verts
        self.faces = [Face(f) for f in faces]

    @staticmethod
    def from_obj(file: TextIO) -> 'Model':
        verts = []
        faces = []

        for line in file:
            split = line.rstrip().split()
            t, split = split[0], split[1:]
            if t == 'v':
                verts.append(Vec3(*map(float, split)))
            elif t == 'f':
                faces.append([int(x) - 1 for x in split])

        return Model(verts, faces)

    @property
    def indices(self) -> list[int]:
        indices = []
        for f in self.faces:
            if len(f.verts) == 3:
                indices += f.verts
            elif len(f.verts) == 4:
                indices += f.verts[:3] + f.verts[2:] + f.verts[:1]
        return indices

    # given a 4x4 vert grid, reconstruct the grid
    def grid_reconstruct(self) -> list[list[Vec3]]:
        if len(self.verts) != 16:
            raise ValueError('Expected 16 verts')

        rel_pos: list[None|tuple[int, int]] = [None] * len(self.verts)

        # ccw vertex orders
        dirs = [
            [(1, 0), (1, 1), (0, 1)],
            [(0, 1), (-1, 1), (-1, 0)],
            [(-1, 0), (-1, -1), (0, -1)],
            [(0, -1), (1, -1), (1, 0)],
        ]

        faces = [f.verts for f in self.faces]

        # choose the first face as the origin, assing rel pos
        face = faces.pop()
        rel_pos[face[0]] = (0, 0)
        rel_pos[face[1]] = dirs[0][0]
        rel_pos[face[2]] = dirs[0][1]
        rel_pos[face[3]] = dirs[0][2]

        while faces:
            # find a face with at least 2 known vertices
            face = faces.pop()
            known_cnt = 0
            for i, v in enumerate(face):
                cur = rel_pos[v]
                if cur is not None:
                    known_cnt += 1
                    known = cur
                    known_ind = i
                    known_vert = v
            if known_cnt < 2:
                # We could do it with just 1, but it would require checking known
                # neighbors. This still eventually maps out all verts.
                faces.append(face)
                continue

            # find direction
            for i in range(1, 4):
                cur = rel_pos[face[(known_ind+i) % 4]]
                if cur is None:
                    continue

                rel = (cur[0] - known[0], cur[1] - known[1])
                for d in range(4):
                    if rel == dirs[d][i-1]:
                        face_dir = d
                        break
                break

            # set relative positions
            for i in range(1, 4):
                pos = (known[0] + dirs[face_dir][i-1][0], known[1] + dirs[face_dir][i-1][1])
                rel_pos[face[(known_ind+i) % 4]] = pos

        # actual origin
        # None check is to make mypy happy
        abs_origin = min(p for p in rel_pos if p is not None)

        sorted_verts = []
        for i in range(4):
            row = []
            for j in range(4):
                pos = (abs_origin[0] + i, abs_origin[1] + j)
                row.append(self.verts[rel_pos.index(pos)])
            sorted_verts.append(row)

        return sorted_verts

    def catmull_clark(self) -> 'Model':
        # face points
        face_points = []
        for face in self.faces:
            point = Vec3()
            for vi in face.verts:
                point += self.verts[vi]
            point /= len(face.verts)
            face_points.append(point)

        # edge points
        edge_points = {}
        seen_edges = set()
        for fi, face in enumerate(self.faces):
            for (a, b) in face.edges:
                # canonical order
                key_e = sort_pair(a, b)

                # edges can be shared by multiple faces a->b b->a
                if key_e in seen_edges:
                    continue
                seen_edges.add(key_e)

                point = self.verts[a] + self.verts[b]
                for fj, face2 in enumerate(self.faces[fi+1:]):
                    if (b, a) not in face2.edges:
                        continue
                    # found adjacent face, not boundary
                    point += face_points[fi] + face_points[fi+1+fj]
                    edge_points[key_e] = point / 4
                    break
                else:
                    # boundary, just add midpoint
                    edge_points[key_e] = point / 2

        # move verts
        new_verts = []
        for vi, vert in enumerate(self.verts):
            f_p = Vec3()
            f_cnt = 0

            edge_cnt: dict[tuple[int, int], int] = {}
            for fi, face in enumerate(self.faces):
                if vi not in face.verts:
                    continue
                f_p += face_points[fi]
                f_cnt += 1

                # in case of boundary condition, we need to know "open" edges
                for e in face.edges:
                    if vi in e:
                        e = sort_pair(*e)
                        edge_cnt[e] = edge_cnt.get(e, 0) + 1

            f_p /= f_cnt

            r_p = Vec3()
            r_cnt = 0
            for (a, b) in edge_cnt.keys():
                if a == vi:
                    r_p += (vert + self.verts[b]) / 2
                    r_cnt += 1
                elif b == vi:
                    r_p += (vert + self.verts[a]) / 2
                    r_cnt += 1
            r_p /= r_cnt

            if f_cnt < 3:
                # boundary, only consider open edges
                r_p = Vec3()
                for e, cnt in edge_cnt.items():
                    if cnt == 1:
                        r_p += edge_points[e] / 2
                new_vert = (r_p + vert) / 2
            else:
                new_vert = f_p + r_p * 2 + vert * (f_cnt - 3)
                new_vert /= f_cnt

            new_verts.append(new_vert)

        # add face and edge verts
        # face: len(verts) + fi
        # edge: ei
        edge_index = {}
        for fp in face_points:
            new_verts.append(fp)
        for e, ep in edge_points.items():
            edge_index[e] = len(new_verts)
            new_verts.append(ep)

        # new faces
        new_faces = []
        for vi, vert in enumerate(self.verts):
            # for each vert, generate new face per face
            for fi, face in enumerate(self.faces):
                if vi not in face.verts:
                    continue

                # for each face, vert has an outedge and an inedge
                for (a, b) in face.edges:
                    if a == vi:
                        out_e = sort_pair(a, b)
                    elif b == vi:
                        in_e = sort_pair(a, b)
                new_faces.append([vi, edge_index[out_e], len(self.verts) + fi, edge_index[in_e]])

        return Model(new_verts, new_faces)
