from typing import List, Tuple

from .br.br_nud import *


class Nud:
    name: str  # chunk name
    mesh_groups: List['NudMeshGroup']

    def __init__(self, br_nud: BrNud):
        pass


class NudMeshGroup:
    name: str
    meshes: List['NudMesh']


class NudMesh:
    vertices: List['NudVertex']
    faces: List[Tuple[int, int, int]]
    materials: List['NudMaterial']

    def add_vertices(self, vertices: List[BrVertex]):
        self.vertices = list()
        for v in vertices:
            self.vertices.append(
                NudVertex(v.position,
                          v.normals,
                          v.biTangents[:3],
                          v.tangents[:3],
                          tuple(map(lambda x: int(x), v.color)),
                          v.uv))

    def add_faces(self, faces: List[int]):
        faces = iter(faces)
        self.faces = list()

        start_dir = 1
        f1 = next(faces)
        f2 = next(faces)
        face_dir = start_dir

        try:
            while True:
                f3 = next(faces)

                if f3 == -1:
                    f1 = next(faces)
                    f2 = next(faces)
                    face_dir = start_dir
                else:
                    face_dir = -face_dir

                    if f1 != f2 != f3:
                        if face_dir > 0:
                            self.faces.append((f3, f2, f1))
                        else:
                            self.faces.append((f2, f3, f1))
                    f1 = f2
                    f2 = f3
        except StopIteration:
            pass

    def add_materials(self):
        pass


class NudVertex:
    position: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    bitangent: Tuple[float, float, float]
    tangent: Tuple[float, float, float]
    color: Tuple[int, int, int, int]
    uv: List[Tuple[float, float]]

    def __init__(self, position, normal, bitangent, tangent, color, uv):
        self.position = position
        self.normal = normal
        self.bitangent = bitangent
        self.tangent = tangent
        self.color = color
        self.uv = uv


class NudMaterial:
    pass
