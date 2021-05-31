from typing import Dict, List, Tuple

from ...util import *
from .br_nucc import *


class BrXfbin(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.header: BrNuccHeader = br.read_struct(BrNuccHeader)
        self.chunkTable: BrChunkTable = br.read_struct(BrChunkTable)

        self.pages: List[BrPage] = list()
        self.chunks: List[BrChunk] = list()

        # Set the page start index to be able to use it inside BrPage read method
        self.curPageStart = 0
        self.curReferenceStart = 0

        # Assume that the file ends with a nuccChunkPage
        while not br.eof():
            br_page: BrPage = br.read_struct(BrPage, None, self)

            # Add the page size to the current page index to "flip" to the next page
            self.curPageStart += br_page.pageChunk.pageSize
            self.curReferenceStart += br_page.pageChunk.referenceSize

            # Add references to the chunks for later use
            self.chunks.extend(br_page.chunksDict.values())

            # Add the page to the br_xfbin
            self.pages.append(br_page)


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

        # Align after reading strings
        br.align_pos(4)

        self.chunkMaps: List[BrChunkMap] = br.read_struct(BrChunkMap, self.chunkMapCount)

        # Chunk references are placed between chunk maps and chunk map indices
        self.chunkMapReferences: List[BrChunkReference] = br.read_struct(BrChunkReference, self.chunkMapReferencesCount)

        self.chunkMapIndices = br.read_uint32(self.chunkMapIndicesCount)

    def get_props_from_chunk_map(self, chunk_map: 'BrChunkMap') -> Tuple[str, str, str]:
        # Return a tuple of (type, path, name) using the chunk map
        return (self.chunkTypes[chunk_map.chunkTypeIndex],
                self.filePaths[chunk_map.filePathIndex],
                self.chunkNames[chunk_map.chunkNameIndex])

    def get_br_nucc_chunk(self, br_chunk: 'BrChunk', page_start_index: int) -> BrNuccChunk:
        # Get the chunk map of the br_chunk
        chunk_map = self.chunkMaps[self.chunkMapIndices[page_start_index + br_chunk.chunkMapIndex]]

        # Create and return a BrNuccChunk with the correct type from the map
        return BrNuccChunk.create_from_nucc_type(*self.get_props_from_chunk_map(chunk_map), br_chunk.data)


class BrChunkMap(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.chunkTypeIndex = br.read_uint32()
        self.filePathIndex = br.read_uint32()
        self.chunkNameIndex = br.read_uint32()


class BrChunkReference(BrStruct):
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


class BrPage(BrStruct):
    def __br_read__(self, br: BinaryReader, br_xfbin: BrXfbin):
        self.chunksDict: Dict[int, BrNuccChunk] = dict()

        while True:
            # Read a BrChunk
            br_chunk: BrChunk = br.read_struct(BrChunk)

            # Convert the BrChunk to a BrNuccChunk
            chunk = br_xfbin.chunkTable.get_br_nucc_chunk(br_chunk, br_xfbin.curPageStart)

            # Add the BrNuccChunk to the dictionary by its local map index (for use when converting BrNuccChunks to NuccChunks)
            self.chunksDict[br_chunk.chunkMapIndex] = chunk

            # Break upon reaching the nuccChunkPage
            if isinstance(chunk, BrNuccChunkPage):
                self.pageChunk = chunk

                # Store the indices of this page from the chunk table for later use
                self.pageChunkIndices = br_xfbin.chunkTable.chunkMapIndices[
                    br_xfbin.curPageStart: br_xfbin.curPageStart + self.pageChunk.pageSize]

                # Store the reference indices of this page from the chunk table for later use
                self.pageChunkReferenceIndices = br_xfbin.chunkTable.chunkMapReferences[
                    br_xfbin.curReferenceStart: br_xfbin.curReferenceStart + chunk.referenceSize]

                # do not forget to think about how we are going to initialize the rest of chunks that were not added
                # by this (so basically NuccChunk objects that do not have data, only type, name and file path)
                break
