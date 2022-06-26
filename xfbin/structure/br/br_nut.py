from ...util import *


# Based on Smash Forge Nut implementation
# https://github.com/jam1garner/Smash-Forge/blob/master/Smash%20Forge/Filetypes/Textures/NUT.cs
class BrNut(BrStruct):
    def __br_read__(self, br: BinaryReader) -> None:
        self.magic = br.read_str(4)

        if self.magic != "NTP3":
            raise Exception('Invalid NUD magic.')

        self.version = br.read_uint16()

        self.texture_count = br.read_uint16()

        br.read_uint32(2)

        self.textures = br.read_struct(BrNutTexture, self.texture_count, self)


class BrNutTexture(BrStruct):
    def __br_read__(self, br: BinaryReader, nut: BrNut) -> None:
        self.total_size = br.read_uint32()
        br.read_uint32()

        self.data_size = br.read_uint32()
        self.header_size = br.read_uint16()
        br.read_uint16()

        br.read_uint8()
        self.mipmap_count = br.read_uint8()
        br.read_uint8()
        self.pixel_format = br.read_uint8()

        self.width = br.read_uint16()
        self.height = br.read_uint16()

        br.read_uint32()
        self.cubemap_format = br.read_uint32()

        self.is_cube_map = False
        if self.cubemap_format & 0x200:
            self.is_cube_map = True

        if nut.version < 0x200:
            self.data_offset = 0x10 + self.header_size
            br.read_uint32(4)
        else:
            self.data_offset = br.read_uint32(4)[0]

        if self.is_cube_map:
            (self.cubemap_size1, self.cubemap_size2, _, _) = br.read_uint32(4)

        if self.mipmap_count > 1:
            self.mipmap_sizes = br.read_uint32(self.mipmap_count)
            br.align_pos(0x10)

        # eXt and GIDX
        br.seek(0x18, Whence.CUR)

        # Probably always 0 in xfbins
        self.hash_id = br.read_uint32()
        br.read_uint32()

        # TODO: Read individual mipmaps/cubemap faces
        
        self.texture_data = br.read_bytes(self.data_size)
