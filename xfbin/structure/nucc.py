from binary_reader import BinaryReader


class NuccChunk:
    name: str
    filePath: str

    def read_data(self, br: BinaryReader):
        self.data = br.buffer()

    @classmethod
    def from_nucc_type(cls, s: str) -> 'NuccChunk':
        return globals().get(s[0].upper() + s[1:], cls)()


class NuccChunkNull(NuccChunk):
    # Empty
    pass


class NuccChunkPage(NuccChunk):
    def read_data(self, br: BinaryReader):
        self.pageSize = br.read_uint32()
        self.referenceCount = br.read_uint32()


class NuccChunkIndex(NuccChunk):
    # Does not exist
    pass


class NuccChunkTexture(NuccChunk):
    pass


class NuccChunkDynamics(NuccChunk):
    pass


class NuccChunkAnm(NuccChunk):
    pass


class NuccChunkClump(NuccChunk):
    pass


class NuccChunkModel(NuccChunk):
    pass


class NuccChunkMaterial(NuccChunk):
    pass


class NuccChunkCoord(NuccChunk):
    pass


class NuccChunkBillboard(NuccChunk):
    pass


class NuccChunkTrail(NuccChunk):
    pass


class NuccChunkCamera(NuccChunk):
    pass


class NuccChunkParticle(NuccChunk):
    pass


class NuccChunkBinary(NuccChunk):
    pass
