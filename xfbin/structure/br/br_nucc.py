from ...util import *
from .br_nud import *
from .br_nut import *


class BrNuccChunk(BrStruct):
    name: str
    filePath: str
    data: bytearray

    # Only used when writing
    nuccChunk: 'NuccChunk'

    def __br_read__(self, br: 'BinaryReader', file_path, name) -> None:
        # When the BrNuccChunk is read, the init_data method of the BrNuccChunk type will be called,
        # which means that this method does not have to be overrided in each subclass
        self.filePath = file_path
        self.name = name

        self.init_data(br)

    def init_data(self, br: BinaryReader):
        # Store the data to be given to the NuccChunk instance later
        self.data = br.buffer()
        br.seek(0)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict) -> None:
        # This should be used only when an override does not exist (i.e. don't call this manually)
        br.extend(self.nuccChunk.data)
        br.seek(len(self.nuccChunk.data), Whence.CUR)

    @classmethod
    def get_br_nucc_type_from_str(cls, type_str: str) -> type:
        # Get the type from a string after capitalizing its first character and prepending "Br" to it
        type_name = "Br" + type_str[0].upper() + type_str[1:]
        result = globals().get(type_name, None)

        if result is None:
            # Create a new type and add it to the globals
            result = type(type_name, (cls,), {})
            globals()[type_name] = result

        return result

    @classmethod
    def create_from_nucc_type(cls, type_str, file_path, name, data) -> 'BrNuccChunk':
        # Read a BrNuccChunk struct from the data using the type and set the name and file path
        return BinaryReader(data, Endian.BIG).read_struct(cls.get_br_nucc_type_from_str(type_str), None, file_path, name)


class BrNuccChunkNull(BrNuccChunk):
    # Empty
    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        pass


class BrNuccChunkPage(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.pageSize = br.read_uint32()
        self.referenceSize = br.read_uint32()

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict, chunkReferences: List):
        # Write the size of the dictionary, and add 1 for the index chunk after this chunk
        br.write_uint32(len(chunkIndexDict) + 1)
        br.write_uint32(len(chunkReferences))


class BrNuccChunkIndex(BrNuccChunk):
    # Does not exist
    pass


class BrNuccChunkTexture(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.field00 = br.read_uint16()
        self.width = br.read_uint16()
        self.height = br.read_uint16()
        self.field06 = br.read_uint16()

        self.nutSize = br.read_uint32()

        # TODO: Make a parser option for this, as it needs to be disabled when *not* parsing
        # # Update the data range so that the parser can write the nut only
        # self.data = br.buffer()[br.pos(): br.pos() + self.nutSize]

        try:
            self.nut_data = br.buffer()[br.pos(): br.pos() + self.nutSize]
            self.brNut = BinaryReader(self.nut_data, Endian.BIG).read_struct(BrNut)
        except:
            print(f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
            self.brNut = None

        # Skip the nut size
        br.seek(self.nutSize, Whence.CUR)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        # TODO: Actual NUT writing
        # Read the NUT data to get the width and height
        # This is needed for compatibility with the exporter, until full support is added
        br_nut: BrNut = BinaryReader(self.nuccChunk.nut_data, Endian.BIG).read_struct(BrNut)

        br.write_uint16(0)  # Placeholder values
        br.write_uint16(br_nut.textures[0].width if br_nut.textures else 0)
        br.write_uint16(br_nut.textures[0].height if br_nut.textures else 0)
        br.write_uint16(0)

        nut_data_size = len(self.nuccChunk.nut_data)
        br.write_uint32(nut_data_size)

        br.extend(self.nuccChunk.nut_data)
        br.seek(nut_data_size, Whence.CUR)


class BrNuccChunkDynamics(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.section1Count = br.read_uint16()
        self.section2Count = br.read_uint16()

        # Chunk index of the clump of this model, but relative to this page
        self.clumpChunkIndex = br.read_uint32()

        self.section1 = br.read_struct(BrDynamics1, self.section1Count)
        self.section2 = br.read_struct(BrDynamics2, self.section2Count)

        # Read all shorts as a single tuple for now
        self.section1Shorts = br.read_uint16(sum(map(lambda x: x.unkCount, self.section1)))

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        chunk = self.nuccChunk

        br.write_uint16(len(chunk.section1))
        br.write_uint16(len(chunk.section2))

        br.write_uint32(chunkIndexDict.get_or_next(chunk.clump_chunk))

        # Write the section 1 shorts while iterating over it
        br_sec1_shorts = BinaryReader(endianness=Endian.BIG)

        for sec1 in chunk.section1:
            br.write_struct(BrDynamics1(), sec1)
            br_sec1_shorts.write_uint16(sec1.shorts)

        for sec2 in chunk.section2:
            br.write_struct(BrDynamics2(), sec2)

        br.extend(br_sec1_shorts.buffer())
        br.seek(br_sec1_shorts.size(), Whence.CUR)


# Placeholder names for now
class BrDynamics1(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):
        self.floats = br.read_float(4)

        # Coord index in the clump's coord indices
        self.coordIndex = br.read_uint16()
        self.unkCount = br.read_uint16()

    def __br_write__(self, br: 'BinaryReader', sec1: 'Dynamics1'):
        br.write_float(sec1.floats)

        br.write_uint16(sec1.coord_index)
        br.write_uint16(len(sec1.shorts))


class BrDynamics2(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):
        self.floats = br.read_float(6)

        self.coordIndex = br.read_uint16()
        self.unkCount = br.read_uint16()

        self.negativeUnk = br.read_int16()
        br.read_uint16()

        self.unkShortTuples = list()
        for _ in range(self.unkCount):
            # Each entry contains the count, and the values. They're all 16-bit ints
            self.unkShortTuples.append(br.read_uint16(br.read_uint16()))

    def __br_write__(self, br: 'BinaryReader', sec2: 'Dynamics2'):
        br.write_float(sec2.floats)

        br.write_uint16(sec2.coord_index)
        br.write_uint16(len(sec2.unk_short_tuples))

        br.write_int16(sec2.negative_unk)
        br.write_uint16(0)

        for tup in sec2.unk_short_tuples:
            br.write_uint16(len(tup))
            br.write_uint16(tup)


class BrNuccChunkAnm(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)


class BrNuccChunkClump(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        # 0 or 1 (?)
        self.field00 = br.read_uint32()

        self.coordCount = br.read_uint16()
        self.coordFlag0 = br.read_uint8()
        self.coordFlag1 = br.read_uint8()

        # Signed because root node's parent index is -1
        self.coordNodeParentsIndices = br.read_int16(self.coordCount)
        self.coordNodeIndices = br.read_uint32(self.coordCount)

        self.modelCount = br.read_uint16()
        self.modelFlag0 = br.read_uint8()
        self.modelFlag1 = br.read_uint8()

        # Padding (?)
        br.read_uint32()

        self.modelIndices = br.read_uint32(self.modelCount)

        self.modelGroups = list()
        while True:
            modelGroup: BrClumpModelGroup = br.read_struct(BrClumpModelGroup)

            if modelGroup.modelCount == -1 or br.eof():
                break

            self.modelGroups.append(modelGroup)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        br.write_uint32(self.nuccChunk.field00)

        br.write_uint16(len(self.nuccChunk.coord_chunks))
        br.write_uint8(self.nuccChunk.coord_flag0)
        br.write_uint8(self.nuccChunk.coord_flag1)

        # Enumerate the coord chunks because the parent indices are respective to the local coord indices list, not the page indices
        coord_chunks_dict = IterativeDict()
        coord_chunks_dict.update_or_next(self.nuccChunk.coord_chunks)

        coord_chunks = tuple(map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.coord_chunks))

        for coord in self.nuccChunk.coord_chunks:
            br.write_int16(coord_chunks_dict[coord.node.parent.chunk] if coord.node.parent else -1)

        br.write_uint32(coord_chunks)

        br.write_uint16(len(self.nuccChunk.model_chunks))
        br.write_uint8(self.nuccChunk.model_flag0)
        br.write_uint8(self.nuccChunk.model_flag0)

        # TODO: is this correct?
        br.write_uint32(0)

        br.write_uint32(tuple(map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.model_chunks)))

        for group in self.nuccChunk.model_groups:
            br.write_struct(BrClumpModelGroup(), group, chunkIndexDict)

        br.write_int16(-1)


class BrClumpModelGroup(BrStruct):
    def __br_read__(self, br: 'BinaryReader') -> None:
        self.modelCount = br.read_int16()

        if self.modelCount != -1:
            self.flag0 = br.read_uint8()
            self.flag1 = br.read_uint8()

            # Seems to be some 4 signed 8 bit integers
            self.unk = br.read_int32()

            self.modelIndices = list()
            for _ in range(self.modelCount):
                # There might be -1 indices, but we're not sure what they're used for
                # Can be found in Storm 1 spc xfbins
                self.modelIndices.append(br.read_int32())

    def __br_write__(self, br: 'BinaryReader', model_group: 'ClumpModelGroup', chunkIndexDict: IterativeDict):
        br.write_uint16(len(model_group.model_chunks))

        br.write_uint8(model_group.flag0)
        br.write_uint8(model_group.flag1)

        br.write_int32(model_group.unk)

        br.write_int32(tuple(map(lambda x: chunkIndexDict.get_or_next(x) if x else -1, model_group.model_chunks)))


class BrNuccChunkModel(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.field00 = br.read_uint16()
        self.riggingFlag = br.read_uint16()  # Affects if the model is correctly rigged to its bones or not

        self.materialFlags = br.read_uint8(4)

        br.read_uint32()  # 0
        self.clumpIndex = br.read_uint32()
        br.read_uint32()  # 0

        # The mesh bone index might or might not be there. So instead, we look for the start of the NUD
        # to get its size, and then check to see if the "bone index" exists or not
        nudStart = br.buffer().find(b'NDP3')

        if nudStart == -1:
            # This shouldn't happen
            raise Exception(f'Could not find NDP3 magic in chunk: {self.name} of type: {type(self).__name__}')

        # Read nudSize from inside the NUD itself
        with br.seek_to(nudStart + 4):
            self.nudSize = br.read_uint32()

        # Check if the next int is the bone index, or if it's just the NUD size.
        self.meshBoneIndex = br.read_uint32()
        if self.meshBoneIndex != self.nudSize:
            # Skip the nud size
            br.read_uint32()
        else:
            # This mesh is not attached to a bone
            self.meshBoneIndex = -1

        if self.materialFlags[1] & 0x04:
            self.flag1Floats = br.read_float(6)

        # Seek to nudStart anyway, just in case
        br.seek(nudStart)

        # TODO: Make a parser option for this, as it needs to be disabled when *not* parsing
        # # Update the data range so that the parser can write the nud only
        # self.data = br.buffer()[br.pos(): br.pos() + self.nudSize]

        try:
            self.brNud = BinaryReader(br.buffer()[br.pos(): br.pos() + self.nudSize], Endian.BIG).read_struct(BrNud)
        except:
            print(f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
            self.brNud = None

        # Skip the nud size
        br.seek(self.nudSize, Whence.CUR)

        self.materialCount = br.read_uint16()
        self.materialIndices = br.read_uint32(self.materialCount)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        br.write_uint16(1)  # Can be 0 sometimes, should test more

        br.write_uint8(0)  # Padding for flag in next byte
        br.write_uint8(int(self.nuccChunk.rigging_flag))

        if self.nuccChunk.material_flags:
            br.write_uint8(self.nuccChunk.material_flags)
        else:
            # Some default values for the flags which we don't know the effect of
            br.write_uint8(0)
            br.write_uint8(0)
            br.write_uint8(8)
            br.write_uint8(3)

        br.write_uint32(0)
        br.write_uint32(chunkIndexDict.get_or_next(self.nuccChunk.clump_chunk))
        br.write_uint32(0)

        # Index of the mesh bone of this model in the clump
        # This might be shared by multiple models
        br.write_uint32(self.nuccChunk.coord_index if self.nuccChunk.coord_index != -1 else 0)

        # Write the BrNud using the NuccChunk's NUD
        with BinaryReader(endianness=Endian.BIG) as br_internal:
            br_internal.write_struct(BrNud(), self.nuccChunk.nud)

            # Write NUD size
            br.write_uint32(br_internal.size())

            # Write the flag1 floats, if they exist
            br.write_float(self.nuccChunk.flag1_floats)

            # Write NUD buffer
            br.extend(br_internal.buffer())
            br.seek(br_internal.size(), Whence.CUR)

        # Write material chunk count
        br.write_uint16(len(self.nuccChunk.material_chunks))

        # Write the material chunk indices
        br.write_uint32(tuple(map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.material_chunks)))


class BrNuccChunkMaterial(BrNuccChunk):
    @staticmethod
    def float_count(format) -> int:
        count = 0

        if format & 0x40:
            count += 1
        if format & 0x20:
            count += 1
        if format & 0x10:
            count += 2
        if format & 0x08:
            count += 4
        if format & 0x04:
            count += 4
        if format & 0x02:
            count += 4
        if format & 0x01:
            count += 4

        return count

    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.groupCount = br.read_uint16()

        # 0xFE in Storm 1, 0xCD in JoJo and Storm 4. Should actually find out what it does
        self.field02 = br.read_uint8()
        br.read_uint8()  # 0

        self.field04 = br.read_float()

        # Padding
        br.read_uint8(3)

        self.format = br.read_uint8()
        self.floats = br.read_float(self.float_count(self.format))

        self.textureGroups = br.read_struct(BrMaterialTextureGroup, self.groupCount)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        br.write_uint16(len(self.nuccChunk.texture_groups))

        br.write_uint8(self.nuccChunk.field02)
        br.write_uint8(0)

        # Usually 0, but can be 0.12 and other numbers
        br.write_float(self.nuccChunk.field04)

        # Padding
        br.write_uint8([0] * 3)

        # Float format
        br.write_uint8(self.nuccChunk.format if self.nuccChunk.floats else 0)
        br.write_float(self.nuccChunk.floats[:self.float_count(self.nuccChunk.format)])

        for group in self.nuccChunk.texture_groups:
            br.write_struct(BrMaterialTextureGroup(), group, chunkIndexDict)


class BrMaterialTextureGroup(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):
        self.textureCount = br.read_int16()
        br.read_uint16()

        # Probably a flag
        self.unk = br.read_int32()

        self.textureIndices = br.read_uint32(self.textureCount)

    def __br_write__(self, br: 'BinaryReader', texture_group: 'MaterialTextureGroup', chunkIndexDict: IterativeDict):
        br.write_uint16(len(texture_group.texture_chunks))
        br.write_uint16(0)

        # Can be safely set to 0
        br.write_int32(texture_group.unk)

        # Write the texture chunk indices
        br.write_uint32(tuple(map(lambda x: chunkIndexDict.get_or_next(x), texture_group.texture_chunks)))


class BrNuccChunkCoord(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.position = br.read_float(3)
        self.rotation = br.read_float(3)  # Rotation is in euler
        self.scale = br.read_float(3)
        self.unkFloat = br.read_float()   # Might be part of scale
        self.unkShort = br.read_uint16()  # Not always 0


class BrNuccChunkBillboard(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)


class BrNuccChunkTrail(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)


class BrNuccChunkCamera(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)


class BrNuccChunkParticle(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)


class BrNuccChunkBinary(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
