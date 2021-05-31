from typing import List, Tuple

from .br.br_nud import *


class Nud:
    name: str  # chunk name
    mesh_groups: List['NudMeshGroup']

    def __init__(self, name, br_nud: BrNud):
        self.name = name

        self.mesh_groups = list()
        for br_mesh_group in br_nud.meshGroups:
            self.mesh_groups.append(NudMeshGroup(br_mesh_group))


class NudMeshGroup:
    name: str
    meshes: List['NudMesh']

    def __init__(self, br_mesh_group: BrNudMeshGroup):
        self.name = br_mesh_group.name

        self.meshes = list()
        for br_mesh in br_mesh_group.meshes:
            self.meshes.append(NudMesh(br_mesh))


class NudMesh:
    vertices: List['NudVertex']
    faces: List[Tuple[int, int, int]]
    materials: List['NudMaterial']

    def __init__(self, br_mesh: BrNudMesh):
        self.add_vertices(br_mesh.vertices)
        self.add_faces(br_mesh.faces)
        self.add_materials(br_mesh.materials)

    def add_vertices(self, vertices: List[BrNudVertex]):
        self.vertices = list()
        for br_vertex in vertices:
            self.vertices.append(NudVertex(br_vertex))

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

    def add_materials(self, materials: List[BrNudMaterial]):
        self.materials = list()


class NudVertex:
    position: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    bitangent: Tuple[float, float, float]
    tangent: Tuple[float, float, float]

    color: Tuple[int, int, int, int]
    uv: List[Tuple[float, float]]

    bone_ids: Tuple[int, int, int, int]
    bone_weights: Tuple[float, float, float, float]

    def __init__(self, br_vertex: BrNudVertex):
        self.position = br_vertex.position
        self.normal = br_vertex.normals
        self.bitangent = br_vertex.biTangents if br_vertex.biTangents else None
        self.tangent = br_vertex.tangents if br_vertex.tangents else None

        self.color = tuple(map(lambda x: int(x), br_vertex.color)) if br_vertex.color else None
        self.uv = br_vertex.uv

        self.bone_ids = br_vertex.boneIds
        self.bone_weights = br_vertex.boneWeights


class NudMaterial:
    pass
