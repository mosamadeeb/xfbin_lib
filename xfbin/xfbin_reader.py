from typing import Union

from binary_reader import *

from .structure.br_xfbin import BrXfbin
from .structure.nucc import NuccChunk, NuccChunkPage
from .structure.xfbin import Page, Xfbin


def read_xfbin(file: Union[str, bytearray]) -> Xfbin:
    if isinstance(file, str):
        with open(file, 'rb') as f:
            file_bytes = f.read()
    else:
        file_bytes = file

    with BinaryReader(file_bytes, Endian.BIG) as br:
        br_xfbin: BrXfbin = br.read_struct(BrXfbin)

    table = br_xfbin.chunkTable

    xfbin = Xfbin()

    chunks = list()
    for m in table.chunkMaps:
        chunk = NuccChunk.create_from_nucc_type(table.chunkTypes[m.chunkTypeIndex])
        chunk.filePath = table.filePaths[m.filePathIndex]
        chunk.name = table.chunkNames[m.chunkNameIndex]
        chunks.append(chunk)

    page_index = 0
    reference_index = 0
    first_chunk_index = -1
    page_chunks = list()

    for c in br_xfbin.chunks:
        current_index = table.chunkMapIndices[page_index + c.chunkMapIndex]

        if first_chunk_index == -1:
            first_chunk_index = current_index

        chunk: NuccChunk = chunks[current_index]
        chunk.init_data(BinaryReader(c.data, Endian.BIG))
        page_chunks.append(chunk)

        if isinstance(chunk, NuccChunkPage):
            page = Page()
            page.chunks.extend(page_chunks)

            for r in table.chunkMapReferences[reference_index: reference_index + chunk.referenceCount]:
                page.references.append(chunks[page_index + r.chunkMapIndex])

            page_index += chunk.pageSize
            reference_index += chunk.referenceCount
            first_chunk_index = -1
            page_chunks.clear()

            xfbin.pages.append(page)

    return xfbin
