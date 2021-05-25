from typing import List

from .nucc import NuccChunk


class Page:
    def __init__(self):
        self.chunks: List[NuccChunk] = list()
        self.references: List[NuccChunk] = list()


class Xfbin:
    def __init__(self):
        self.pages: List[Page] = list()
