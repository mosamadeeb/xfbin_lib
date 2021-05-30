from itertools import chain
from typing import Dict, List, Union

from .nucc import NuccChunk, NuccChunkNull, NuccChunkPage


class Page:
    def __init__(self):
        self.chunks: List[NuccChunk] = list()

    def __iter__(self):
        return iter(self.chunks)

    def get_chunks_by_type(self, nucc_type: Union[str, type]) -> List[NuccChunk]:
        if type(nucc_type) is str:
            nucc_type = NuccChunk.get_nucc_type_from_str(nucc_type)

        return [c for c in self.chunks if type(c) is nucc_type]


class Xfbin:
    def __init__(self):
        self.pages: List[Page] = list()

    def __iter__(self):
        return iter(self.pages)

    def get_type_chunk_dict(self) -> Dict[Union[str, type], List[NuccChunk]]:
        chunks = list(chain.from_iterable(self.pages))
        result: Dict[type, List[NuccChunk]] = dict()

        for c in chunks:
            if type(c) is NuccChunkPage or type(c) is NuccChunkNull:
                continue

            if not result.get(type(c), None):
                result[type(c)] = list()

            result[type(c)].append(c)

        return result

    def get_page_chunk_dict(self) -> Dict[Union[str, type], List[NuccChunk]]:
        result = dict()

        for p in range(len(self.pages)):
            result[f'Page{p}'] = [c for c in self.pages[p].chunks if type(c) not in (NuccChunkPage, NuccChunkNull)]

        return result

    def get_chunks_by_type(self, nucc_type: Union[str, type]) -> List[NuccChunk]:
        result = list()

        for p in self.pages:
            result.extend(p.get_chunks_by_type(nucc_type))

        return result
