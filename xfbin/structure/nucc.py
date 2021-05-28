from ..util import *
from .br import *


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
    def get_all_nucc_types(cls):
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

        self.field00 = br.read_uint16()
        self.width = br.read_uint16()
        self.height = br.read_uint16()
        self.field06 = br.read_uint16()

        self.nutSize = br.read_uint32()

        try:
            self.nut = BinaryReader(br.buffer()[br.pos(): br.pos() + self.nutSize], Endian.BIG).read_struct(BrNut)
        except:
            print(f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
            self.nut = None
        finally:
            br.seek(self.nutSize, Whence.CUR)


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

        self.field00 = br.read_uint16()
        self.field02 = br.read_uint16()

        self.flag0 = br.read_uint8()
        self.flag1 = br.read_uint8()
        self.flag2 = br.read_uint8()
        self.flag3 = br.read_uint8()

        self.field08 = br.read_uint32()
        self.field0C = br.read_uint32()
        self.field10 = br.read_uint32()
        self.field14 = br.read_uint32()

        self.nudSize = br.read_uint32()

        if self.flag1 & 0x04:
            self.floats = br.read_float(6)

        try:
            self.nud = BinaryReader(br.buffer()[br.pos(): br.pos() + self.nudSize], Endian.BIG).read_struct(BrNud)
        except:
            print(f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
            self.nud = None
        finally:
            br.seek(self.nudSize, Whence.CUR)

        self.polySetCount = br.read_uint16()
        self.polySetValues = br.read_uint32(self.polySetCount)


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
