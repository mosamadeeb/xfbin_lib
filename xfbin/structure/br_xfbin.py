from typing import List

from binary_reader import *


class BrXfbin(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.header: BrNuccHeader = br.read_struct(BrNuccHeader)
        self.chunkTable: BrChunkTable = br.read_struct(BrChunkTable)

        self.chunks: List[BrChunk] = list()
        while not br.eof():
            self.chunks.append(br.read_struct(BrChunk))


class BrNuccHeader(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.magic = br.read_str(4)

        if self.magic != "NUCC":
            raise Exception('Invalid magic.')

        self.nuccId = br.read_uint32()
        br.seek(8, Whence.CUR)

        self.chunkTableSize = br.read_uint32()
        self.minPageSize = br.read_uint32()
        self.nuccId2 = br.read_uint16()
        self.unk = br.read_uint16()


class BrChunkTable(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.chunkTypeCount = br.read_uint32()
        self.chunkTypeSize = br.read_uint32()

        self.filePathCount = br.read_uint32()
        self.filePathSize = br.read_uint32()

        self.chunkNameCount = br.read_uint32()
        self.chunkNameSize = br.read_uint32()

        self.chunkMapCount = br.read_uint32()
        self.chunkMapSize = br.read_uint32()

        self.chunkMapIndicesCount = br.read_uint32()
        self.chunkMapReferencesCount = br.read_uint32()

        self.chunkTypes = list()
        for _ in range(self.chunkTypeCount):
            self.chunkTypes.append(br.read_str())

        self.filePaths = list()
        for _ in range(self.filePathCount):
            self.filePaths.append(br.read_str())

        self.chunkNames = list()
        for _ in range(self.chunkNameCount):
            self.chunkNames.append(br.read_str())

        self.chunkMaps: List[BrChunkMap] = br.read_struct(BrChunkMap, self.chunkMapCount)
        self.chunkMapIndices = br.read_uint32(self.chunkMapIndicesCount)

        self.chunkMapReferences: List[BrchunkMapReference] = br.read_struct(BrchunkMapReference, self.chunkMapReferencesCount)


class BrChunkMap(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.chunkTypeIndex = br.read_uint32()
        self.filePathIndex = br.read_uint32()
        self.chunkNameIndex = br.read_uint32()

class BrchunkMapReference(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.chunkNameIndex = br.read_uint32()
        self.chunkMapIndex = br.read_uint32()

class BrChunk(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.size = br.read_uint32()
        self.chunkMapIndex = br.read_uint32()
        self.nuccId = br.read_uint16()
        self.unk = br.read_uint16()
        self.data = br.read_bytes(self.size)
