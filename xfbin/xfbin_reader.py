from typing import List, Union

from .structure.br.br_xfbin import *
from .structure.nucc import NuccChunk
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

    with BinaryReader(file_bytes, Endian.BIG, 'cp932') as br:
        br_xfbin: BrXfbin = br.read_struct(BrXfbin)

    table = br_xfbin.chunkTable

    # Create NuccChunks with the correct type from the chunk map
    chunks: List[NuccChunk] = list()
    for m in table.chunkMaps:
        chunks.append(NuccChunk.create_from_nucc_type(*table.get_props_from_chunk_map(m)))

    xfbin = Xfbin()
    for br_page in br_xfbin.pages:
        page = Page()

        for index in br_page.chunksDict:
            # Get the NuccChunk corresponding to the current BrNuccChunk
            chunk: NuccChunk = chunks[br_page.pageChunkIndices[index]]

            # Initialize the NuccChunk's data using the BrNuccChunk, the list of chunks, and the indices from the page
            chunk.init_data(br_page.chunksDict[index], chunks,
                            br_page.pageChunkIndices, br_page.pageChunkReferences)

            # Add the chunk to the page
            page.chunks.append(chunk)

        # Create ChunkReferences and add them to the page's list
        for br_ref in br_page.pageChunkReferences:
            page.chunk_references.append(ChunkReference(
                table.chunkNames[br_ref.chunkNameIndex], chunks[br_ref.chunkMapIndex]))

        # Add the page to the xfbin
        xfbin.pages.append(page)

    return xfbin
