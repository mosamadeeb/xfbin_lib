from enum import IntEnum
from typing import List, Optional, Tuple, Union

from ...util import *


class BrNud(BrStruct):
    def __br_read__(self, br: BinaryReader) -> None:
        self.magic = br.read_str(4)

        if self.magic != "NDP3":
            raise Exception('Invalid NUD magic.')

        self.fileSize = br.read_uint32()
        self.version = br.read_uint16()

        self.meshGroupCount = br.read_uint16()
        self.boneType = br.read_uint16()
        self.boneCount = br.read_uint16()

        self.polyClumpStart = br.read_uint32() + 0x30
        self.polyClumpSize = br.read_uint32()

        self.vertClumpStart = self.polyClumpStart + self.polyClumpSize
        self.vertClumpSize = br.read_uint32()

        self.vertAddClumpStart = self.vertClumpStart + self.vertClumpSize
        self.vertAddClumpSize = br.read_uint32()

        self.nameStart = self.vertAddClumpStart + self.vertAddClumpSize

        self.boundingSphere = br.read_float(4)

        self.meshGroups: Tuple[BrMeshGroup] = br.read_struct(BrMeshGroup, self.meshGroupCount, self)

        if self.meshGroupCount == 1:
            self.meshGroups = (self.meshGroups,)

        for g in self.meshGroups:
            g.meshes = br.read_struct(BrMesh, g.meshCount, self)


class BrMeshGroup(BrStruct):
    SIZE = 0x30
    meshes: List['BrMesh']

    def __br_read__(self, br: BinaryReader, nud: BrNud) -> None:
        self.boundingSphere = br.read_float(8)
        self.nameStart = br.read_uint32()

        with br.seek_to(self.nameStart + nud.nameStart):
            self.name = br.read_str()

        self.unk = br.read_uint16()
        self.boneFlags = br.read_uint16()
        self.singleBind = br.read_uint16()
        self.meshCount = br.read_uint16()

        self.positionb = br.read_uint32()


class BrMesh(BrStruct):
    SIZE = 0x30

    def __br_read__(self, br: BinaryReader, nud: BrNud) -> None:
        self.polyClumpStart = br.read_uint32() + nud.polyClumpStart
        self.vertClumpStart = br.read_uint32() + nud.vertClumpStart
        self.vertAddClumpStart = br.read_uint32() + nud.vertAddClumpStart

        self.vertexCount = br.read_uint16()
        self.vertexSize = br.read_uint8()
        self.uvSize = br.read_uint8()

        self.texProps = br.read_uint32(4)

        self.faceCount = br.read_uint16()
        self.faceSize = br.read_uint8()
        self.faceFlag = br.read_uint8()
        br.seek(0xC, Whence.CUR)

        # Faces
        with br.seek_to(self.polyClumpStart):
            self.faces = br.read_uint16(self.faceCount)

        # UV + Vertices
        with br.seek_to(self.vertClumpStart):
            boneType = self.vertexSize & 0xF0
            vertexType = self.vertexSize & 0x0F

            colors = list()
            uvs = list()
            if boneType > 0:
                uvCount = self.uvSize >> 4
                uvType = self.uvSize & 0x0F

                for i in range(self.vertexCount):
                    if uvType == 0:
                        colors.append(None)
                    elif uvType == 2:
                        colors.append(br.read_uint8(4))
                    elif uvType == 4:
                        colors.append(list(map(lambda x: x * 255, br.read_half_float(4))))

                    uvs.append(list())
                    for _ in range(uvCount):
                        uvs[i].append(br.read_half_float(2))

                br.seek(self.vertAddClumpStart)

            self.vertices = br.read_struct(BrVertex, self.vertexCount, vertexType, boneType, self.uvSize)

            if boneType > 0:
                for i in range(self.vertexCount):
                    self.vertices[i].color = colors[i]
                    self.vertices[i].uv = uvs[i]

        # Materials
        i = 0
        self.materials: List[BrMaterial] = list()
        while i < 4 and self.texProps[i] != 0:
            with br.seek_to(self.texProps[i]):
                self.materials.append(br.read_struct(BrMaterial, 1, self, nud.nameStart))
            i += 1


class VertexType(IntEnum):
    NoNormals = 0
    NormalsFloat = 1
    Unknown = 2
    NormalsTanBiTanFloat = 3
    NormalsHalfFloat = 6
    NormalsTanBiTanHalfFloat = 7


class BoneType(IntEnum):
    NoBones = 0
    Float = 0x10
    HalfFloat = 0x20
    Byte = 0x40


class BrVertex(BrStruct):
    color: Optional[Union[List[int], List[float]]]
    uv: List[Tuple[float, float]]

    def __br_read__(self, br: BinaryReader, vertexType, boneType, uvSize) -> None:
        self.position = br.read_float(3)

        if vertexType == VertexType.NoNormals:
            br.read_float()
        elif vertexType == VertexType.NormalsFloat:
            br.read_float()
            self.normals = br.read_float(3)
            br.read_float()
        elif vertexType == VertexType.Unknown:
            self.normals = br.read_float(3)
            br.read_float()
            br.read_float(3)
            br.read_float(3)
            br.read_float(3)
        elif vertexType == VertexType.NormalsTanBiTanFloat:
            br.read_float()
            self.normals = br.read_float(3)
            br.read_float()
            self.biTangents = br.read_float(4)
            self.tangents = br.read_float(4)
        elif vertexType == VertexType.NormalsHalfFloat:
            self.normals = br.read_half_float(3)
            br.read_half_float()
        elif vertexType == VertexType.NormalsTanBiTanHalfFloat:
            self.normals = br.read_half_float(3)
            br.read_half_float()
            self.biTangents = br.read_half_float(4)
            self.tangents = br.read_half_float(4)
        else:
            raise Exception(f'Unsupported vertex type: {vertexType}')

        if boneType == BoneType.NoBones:
            if uvSize >= 18:
                self.color = br.read_uint8(4)

            self.uv = list()
            for _ in range(uvSize >> 4):
                self.uv.append(br.read_half_float(2))
        elif boneType == BoneType.Float:
            self.boneIds = br.read_uint32(4)
            self.boneWeights = br.read_float(4)
        elif boneType == BoneType.HalfFloat:
            self.boneIds = br.read_uint16(4)
            self.boneWeights = br.read_half_float(4)
        elif boneType == BoneType.Byte:
            self.boneIds = br.read_uint8(4)
            self.boneWeights = list(map(lambda x: float(x) / 255, br.read_uint8(4)))
        else:
            raise Exception(f'Unsupported bone type: {boneType}')


class BrMaterial(BrStruct):
    def __br_read__(self, br: BinaryReader, mesh: BrMesh, nameStart: int) -> None:
        self.flags = br.read_uint32()
        br.read_uint32()

        self.sourceFactor = br.read_uint16()
        self.textureCount = br.read_uint16()
        self.destFactor = br.read_uint16()

        self.alphaTest = br.read_uint8()
        self.alphaFunction = br.read_uint8()

        self.refAlpha = br.read_uint16()
        self.cullMode = br.read_uint16()
        br.read_uint32(2)
        self.zBufferOffset = br.read_uint32()

        self.textures = br.read_struct(BrMaterialTexture, self.textureCount)

        while True:
            matAttPos = br.pos()

            self.matAttSize = br.read_uint32()
            self.nameStart = br.read_uint32()

            br.read_uint8(3)
            self.valueCount = br.read_uint8()
            br.read_uint32()

            if self.valueCount != 0:
                with br.seek_to(nameStart + self.nameStart):
                    self.name = br.read_str()

                self.values = list(br.read_float(self.valueCount))
                self.values.extend([float()] * (4 - self.valueCount))

            if self.matAttSize == 0:
                break

            br.seek(matAttPos + self.matAttSize)


class BrMaterialTexture(BrStruct):
    def __br_read__(self, br: BinaryReader) -> None:
        self.hash = br.read_uint32()
        br.read_uint32()

        br.read_uint16()
        self.mapMode = br.read_uint16()

        self.wrapModeS = br.read_uint8()
        self.wrapModeT = br.read_uint8()
        self.minFilter = br.read_uint8()
        self.magFilter = br.read_uint8()
        self.mipDetail = br.read_uint8()
        self.unk1 = br.read_uint8()

        br.read_uint32()
        self.unk2 = br.read_int16()