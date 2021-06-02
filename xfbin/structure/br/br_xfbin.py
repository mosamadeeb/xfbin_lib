from typing import Dict, List, Tuple

from ...util import *
from ..nucc import *
from ..xfbin import *
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

    def __br_write__(self, br: 'BinaryReader', xfbin: Xfbin):
        # Store the pages in a separate buffer and merge it with the main buffer later
        br_page_writer = BinaryReader(endianness=Endian.BIG)

        # First page always has an extra null chunk (doesn't affect anything though)
        null_chunk = BrNuccChunkNull()
        null_chunk.nuccChunk = NuccChunkNull()
        br_page_writer.write_struct(BrChunk(), null_chunk, IterativeDict())

        # This will contain all unique chunks
        chunk_map_dict = IterativeDict()

        # This will contain the indices list for all pages combined
        chunk_map_indices = list()

        # Write each page
        for page in xfbin:
            br_page = BrPage()

            # Write the BrPage
            br_page_writer.write_struct(br_page, page)

            # Add the non-existent NuccChunkIndex chunk, as it should not be written as a BrChunk
            br_page.chunkIndexDict.get_or_next(NuccChunkIndex())

            # Update the global chunk list using this BrPage's chunk index dict
            chunk_map_dict.update_or_next(br_page.chunkIndexDict)

            # Add all of the chunks in the current page to the indices list (in order)
            chunk_map_indices.extend(br_page.chunkIndexDict.keys())

        # After all of the pages have been written, start writing the table
        br_chunk_table_writer = BinaryReader(endianness=Endian.BIG)
        br_chunk_table = BrChunkTable()

        br_chunk_table.chunkMapDict = chunk_map_dict
        br_chunk_table.chunkMapIndices = chunk_map_indices

        br_chunk_table_writer.write_struct(br_chunk_table)

        br_header = BrNuccHeader()
        br_header.chunkTableSize = br_chunk_table_writer.size() - br_chunk_table.chunkMapReferencesSize

        # Write the header
        br.write_struct(br_header)

        # Write the chunk table to the main buffer
        br.extend(br_chunk_table_writer.buffer())
        br.seek(br_chunk_table_writer.size(), Whence.CUR)

        # Write the page buffer to the main buffer
        br.extend(br_page_writer.buffer())
        br.seek(br_page_writer.size(), Whence.CUR)


class BrNuccHeader(BrStruct):
    # Only used when writing
    chunkTableSize: int

    def __br_read__(self, br: BinaryReader):
        self.magic = br.read_str(4)

        if self.magic != 'NUCC':
            raise Exception('Invalid magic.')

        self.nuccId = br.read_uint32()
        br.seek(8, Whence.CUR)

        self.chunkTableSize = br.read_uint32()  # Without the extra references size
        self.minPageSize = br.read_uint32()
        self.nuccId2 = br.read_uint16()
        self.unk = br.read_uint16()

    def __br_write__(self, br: 'BinaryReader'):
        # Nothing in the header except for the 8 padding bytes after the nucc ID actually matters
        br.write_str('NUCC')
        br.write_uint32(0x79)  # nuccID

        # Padding
        br.write_uint64(0)

        br.write_uint32(self.chunkTableSize)
        br.write_uint32(3)  # TODO: Doesn't really affect anything, but should test with xfbins with references

        br.write_uint16(0x79)  # nuccID
        br.write_uint16(0)


class BrChunkTable(BrStruct):
    # Contains all unique chunks
    chunkMapDict: Dict[NuccChunk, int]

    # Contains the combined page indices
    chunkMapIndices: List[NuccChunk]

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

    def __br_write__(self, br: 'BinaryReader'):
        # Set up the indices dictionaries
        chunk_type_indices = IterativeDict()
        file_path_indices = IterativeDict()
        chunk_name_indices = IterativeDict()
        dict_tuple = (chunk_type_indices, file_path_indices, chunk_name_indices)

        with BinaryReader(endianness=Endian.BIG) as br_internal:
            # Write the chunk maps
            for chunk in self.chunkMapDict.keys():
                br_internal.write_struct(BrChunkMap(), (NuccChunk.get_nucc_str_from_type(
                    type(chunk)), chunk.filePath, chunk.name), dict_tuple)

            # TODO: Write the chunk map references
            self.chunkMapReferencesSize = 0

            # Write the chunk map indices
            br_internal.write_uint32(list(map(lambda x: self.chunkMapDict[x], self.chunkMapIndices)))

            chunk_map_buffer = br_internal.buffer()

        string_sizes = list()
        with BinaryReader(endianness=Endian.BIG, encoding='cp932') as br_internal:
            for d in dict_tuple:
                for s in d.keys():
                    br_internal.write_str(s, True)
                string_sizes.append(br_internal.size() - sum(string_sizes))

            # Align after all string sections have been written
            br_internal.align(4)

            string_buffer = br_internal.buffer()

        # Write each of the string sections' count and size
        for i, d in enumerate(dict_tuple):
            br.write_uint32(len(d))
            br.write_uint32(string_sizes[i])

        # Write chunk maps count and size
        br.write_uint32(len(self.chunkMapDict))
        br.write_uint32((len(self.chunkMapDict) * 3) * 4)

        # Write chunk map indices count
        br.write_uint32(len(self.chunkMapIndices))
        br.write_uint32(0)  # TODO: Write the chunk map references count

        # Write the string sections buffer to the main buffer
        br.extend(string_buffer)
        br.seek(len(string_buffer), Whence.CUR)

        # Write the chunk map/indices buffer to the main buffer
        br.extend(chunk_map_buffer)
        br.seek(len(chunk_map_buffer), Whence.CUR)


class BrChunkMap(BrStruct):
    def __br_read__(self, br: BinaryReader):
        self.chunkTypeIndex = br.read_uint32()
        self.filePathIndex = br.read_uint32()
        self.chunkNameIndex = br.read_uint32()

    def __br_write__(self, br: 'BinaryReader', chunk_tuple: tuple, dict_tuple: Tuple[IterativeDict]):
        # Write each of the type, file path, and name indices
        br.write_uint32(list(map(lambda x, y: y.get_or_next(x), chunk_tuple, dict_tuple)))


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

    def __br_write__(self, br: 'BinaryReader', br_nucc_chunk: BrNuccChunk, chunkIndexDict: IterativeDict, *args):
        with BinaryReader(endianness=Endian.BIG) as br_internal:
            chunk_index = chunkIndexDict.get_or_next(br_nucc_chunk.nuccChunk)
            br_internal.write_struct(br_nucc_chunk, chunkIndexDict, *args)

            br.write_uint32(br_internal.size())
            br.write_uint32(chunk_index)

            # This doesn't affect anything
            br.write_uint16(0x79)  # nuccId
            br.write_uint16(0)

            br.extend(br_internal.buffer())
            br.seek(br_internal.size(), Whence.CUR)


class BrPage(BrStruct):
    # Only used when writing
    chunkIndexDict: IterativeDict

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

                break

    def __br_write__(self, br: 'BinaryReader', page: Page):
        self.chunkIndexDict = IterativeDict()

        # Write the null chunk
        null_chunk = BrNuccChunkNull()
        null_chunk.nuccChunk = NuccChunkNull()
        br.write_struct(BrChunk(), null_chunk, self.chunkIndexDict)

        for nucc_chunk in page:
            # Skip leftover null and page chunks, as we're supposed to write new ones
            if isinstance(nucc_chunk, (NuccChunkNull, NuccChunkPage)):
                continue

            # Create a new BrNuccChunk from the NuccChunk's type
            br_nucc_chunk: BrNuccChunk = BrNuccChunk.get_br_nucc_type_from_str(type(nucc_chunk).__qualname__)()
            br_nucc_chunk.nuccChunk = nucc_chunk

            # Write the BrNuccChunk
            br.write_struct(BrChunk(), br_nucc_chunk, self.chunkIndexDict)

        # Write the page chunk
        # This is just a placeholder and the actual data will be given by the BrPage's dictionary
        br_nucc_page = BrNuccChunkPage()
        br_nucc_page.nuccChunk = NuccChunkPage()
        br.write_struct(BrChunk(), br_nucc_page, self.chunkIndexDict)

        # TODO: Write reference chunks page size too
