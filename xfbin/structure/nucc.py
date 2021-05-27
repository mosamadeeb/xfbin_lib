from typing import List

from binary_reader import BinaryReader


class NuccChunk:
    name: str
    filePath: str
    data: bytearray

    extension: str

    def __init__(self):
        self.extension = ''

    def init_data(self, br: BinaryReader):
        self.data = br.buffer()
        br.seek(0)

    @classmethod
    def get_nucc_type_from_str(cls, s: str) -> type:
        return globals().get(s[0].upper() + s[1:], cls)

    @classmethod
    def create_from_nucc_type(cls, s: str) -> 'NuccChunk':
        return cls.get_nucc_type_from_str(s)()

    @classmethod
    def get_all_nucc_types(cls) -> List[type]:
        # This will only return types with names that start with this class's name (but are not this class)
        return [n for (k, n) in globals() if k.startswith(cls.__qualname__) and len(k) > len(cls.__qualname__)]


class NuccChunkNull(NuccChunk):
    # Empty
    pass


class NuccChunkPage(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.pageSize = br.read_uint32()
        self.referenceCount = br.read_uint32()


class NuccChunkIndex(NuccChunk):
    # Does not exist
    pass


class NuccChunkTexture(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.nut'


class NuccChunkDynamics(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.dynamics'


class NuccChunkAnm(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.anm'


class NuccChunkClump(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.clump'


class NuccChunkModel(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.nud'


class NuccChunkMaterial(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.material'


class NuccChunkCoord(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.coord'


class NuccChunkBillboard(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.billboard'


class NuccChunkTrail(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.trail'


class NuccChunkCamera(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.cam'


class NuccChunkParticle(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.particle'


class NuccChunkBinary(NuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.extension = '.bin'
