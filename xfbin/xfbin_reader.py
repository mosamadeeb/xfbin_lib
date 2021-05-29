from typing import Union

from .structure.br.br_xfbin import BrXfbin
from .structure.nucc import NuccChunk, NuccChunkPage
from .structure.xfbin import Page, Xfbin
from .util import *


def read_xfbin(file: Union[str, bytearray]) -> Xfbin:
    """Reads an XFBIN file and returns an Xfbin object.
    :param file: Path to file as a string, or bytes-like object containing the file
    :return: The Xfbin object
    """
    if isinstance(file, str):
        with open(file, 'rb') as f:
            file_bytes = f.read()
    else:
        file_bytes = file

    with BinaryReader(file_bytes, Endian.BIG) as br:
        br_xfbin: BrXfbin = br.read_struct(BrXfbin)

    table = br_xfbin.chunkTable

    xfbin = Xfbin()

    # Create chunks with the correct type from the chunk map
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

    # Add chunks to pages based on the chunk map indices list
    for c in br_xfbin.chunks:
        # Get index of current chunk in the page
        current_index = table.chunkMapIndices[page_index + c.chunkMapIndex]

        if first_chunk_index == -1:
            first_chunk_index = current_index

        # Initialize the NuccChunk with its data
        chunk: NuccChunk = chunks[current_index]
        chunk.init_data(BinaryReader(c.data, Endian.BIG))
        page_chunks.append(chunk)

        if isinstance(chunk, NuccChunkPage):
            # "Flip" the page once we reach a nuccChunkPage chunk
            page = Page()
            page.chunks.extend(page_chunks)

            # TODO: References should be added to the individual chunks using them, instead of storing them in the page
            for r in table.chunkMapReferences[reference_index: reference_index + chunk.referenceCount]:
                page.references.append(chunks[page_index + r.chunkMapIndex])

            # Finish setting up each chunk, when needed
            for ch in page.chunks:
                ch.finalize_data(br_xfbin, page, page_index)

            # Add the page size to the current page index to "flip" to the next page
            page_index += chunk.pageSize
            reference_index += chunk.referenceCount
            first_chunk_index = -1
            page_chunks.clear()

            xfbin.pages.append(page)

    return xfbin
