from ...util import *


class BrNut(BrStruct):
    def __br_read__(self, br: BinaryReader) -> None:
        self.magic = br.read_str(4)

        if self.magic != "NTP3":
            raise Exception('Invalid NUD magic.')

        self.version = br.read_uint16()

        self.textureCount = br.read_uint16()

        br.read_uint32(2)

        self.textures = br.read_struct(BrNutTexture, self.textureCount, self)


class BrNutTexture(BrStruct):
    def __br_read__(self, br: BinaryReader, nut: BrNut) -> None:
        self.totalSize = br.read_uint32()
        br.read_uint32()

        self.dataSize = br.read_uint32()
        self.headerSize = br.read_uint16()
        br.read_uint16()

        br.read_uint8()
        self.mipmapCount = br.read_uint8()
        br.read_uint8()
        self.pixelFormat = br.read_uint8()

        self.width = br.read_uint16()
        self.height = br.read_uint16()

        br.read_uint32()
        self.cubeMapFormat = br.read_uint32()

        self.isCubemap = False
        if self.cubeMapFormat & 0x200:
            self.isCubemap = True

        if nut.version < 0x200:
            self.dataOffset = 0x10 + self.headerSize
            br.read_uint32(4)
        else:
            self.dataOffset = br.read_uint32(4)[0]

        if self.isCubemap:
            (self.cubemapSize1, self.cubemapSize2, _, _) = br.read_uint32(4)

        if self.mipmapCount > 1:
            self.mipmapSizes = br.read_uint32(self.mipmapCount)
            br.align_pos(0x10)

        # eXt and GIDX
        br.seek(0x18, Whence.CUR)

        # Probably always 0 in xfbins
        self.hashId = br.read_uint32()
        br.read_uint32()

        # TODO: Read individual mipmaps/cubemap faces
        self.textureData = self.dataSize
