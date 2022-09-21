from utils.xfbin_lib.xfbin.structure.nut import Nut
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

        # Try to add the referenced chunks in the same order they were added
        # This should work fine unless some other chunk in this page (before this chunk) got modified
        # TODO: Maybe replace this with a better solution later
        chunkIndexDict.update_or_next(self.nuccChunk.chunks)

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

        try:
            self.nut_data = br.buffer()[br.pos(): br.pos() + self.nutSize]
            self.brNut = BinaryReader(
                self.nut_data, Endian.BIG).read_struct(BrNut)
        except:
            print(
                f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
            self.brNut = None

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):

        br.write_uint16(0)  # Placeholder values
        br.write_uint16(
            self.nuccChunk.nut.textures[0].width if self.nuccChunk.nut.textures else 0)
        br.write_uint16(
            self.nuccChunk.nut.textures[0].height if self.nuccChunk.nut.textures else 0)
        br.write_uint16(0)

        with BinaryReader(endianness=Endian.BIG) as br_internal:
            br_internal.write_struct(BrNut(), self.nuccChunk.nut)

            # Write the nut size
            br.write_uint32(br_internal.size())
            # Write the nut data
            br.extend(br_internal.buffer())
            # Advance the position
            br.seek(br_internal.size(), Whence.CUR)


class BrNuccChunkDynamics(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.SPGroupCount = br.read_uint16()
        self.ColSphereCount = br.read_uint16()

        # Chunk index of the clump of this model, but relative to this page
        self.clumpChunkIndex = br.read_uint32()

        self.SPGroup = br.read_struct(BrDynamics1, self.SPGroupCount)
        self.ColSphere = br.read_struct(BrDynamics2, self.ColSphereCount)

        # Read all shorts as a single tuple for now
        self.section1Shorts = br.read_uint16(
            sum(map(lambda x: x.BonesCount, self.SPGroup)))
        # print(self.section1Shorts)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        chunk = self.nuccChunk

        br.write_uint16(chunk.SPGroupCount)
        br.write_uint16(chunk.ColSphereCount)

        br.write_uint32(chunkIndexDict.get_or_next(chunk.clump_chunk))

        # Write the section 1 shorts while iterating over it
        br_sec1_shorts = BinaryReader(endianness=Endian.BIG)

        for sec1 in chunk.SPGroup:
            br.write_struct(BrDynamics1(), sec1)
            br_sec1_shorts.write_uint16(sec1.shorts)

        for sec2 in chunk.ColSphere:
            br.write_struct(BrDynamics2(), sec2)

        br.extend(br_sec1_shorts.buffer())
        br.seek(br_sec1_shorts.size(), Whence.CUR)


# Placeholder names for now
class BrDynamics1(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):
        self.Bounciness = br.read_float()
        self.Elasticity = br.read_float()
        self.Stiffness = br.read_float()
        self.Movement = br.read_float()

        # Coord index in the clump's coord indices
        self.coordIndex = br.read_uint16()
        self.BonesCount = br.read_uint16()

    def __br_write__(self, br: 'BinaryReader', sec1: 'Dynamics1'):
        br.write_float(sec1.Bounciness)
        br.write_float(sec1.Elasticity)
        br.write_float(sec1.Stiffness)
        br.write_float(sec1.Movement)

        br.write_uint16(sec1.coord_index)
        br.write_uint16(len(sec1.shorts))


class BrDynamics2(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):
        self.offset_x = br.read_float()
        self.offset_y = br.read_float()
        self.offset_z = br.read_float()
        self.scale_x = br.read_float()
        self.scale_y = br.read_float()
        self.scale_z = br.read_float()

        self.coordIndex = br.read_uint16()
        self.boolflag = br.read_uint16()

        self.negativeUnk = br.read_int16()
        br.read_uint16()

        self.attached_groups_count = 0
        self.attached_groups = 0

        self.attached_groups = list()
        if self.boolflag == 1:
            self.attached_groups_count = br.read_uint16()
            self.attached_groups = br.read_uint16(self.attached_groups_count)

    def __br_write__(self, br: 'BinaryReader', sec2: 'Dynamics2'):
        br.write_float(sec2.offset_x)
        br.write_float(sec2.offset_y)
        br.write_float(sec2.offset_z)
        br.write_float(sec2.scale_x)
        br.write_float(sec2.scale_y)
        br.write_float(sec2.scale_z)

        br.write_uint16(sec2.coord_index)
        br.write_uint16(sec2.attach_groups)
        br.write_int16(sec2.negative_unk)
        br.write_uint16(0)

        if sec2.attach_groups == 1:
            br.write_uint16(sec2.attached_groups_count)
            for g in sec2.attached_groups:
                br.write_uint16(g)


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

        coord_chunks = tuple(
            map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.coord_chunks))

        for coord in self.nuccChunk.coord_chunks:
            br.write_int16(
                coord_chunks_dict[coord.node.parent.chunk] if coord.node.parent else -1)

        br.write_uint32(coord_chunks)

        br.write_uint16(len(self.nuccChunk.model_chunks))
        br.write_uint8(self.nuccChunk.model_flag0)
        br.write_uint8(self.nuccChunk.model_flag0)

        # TODO: is this correct?
        br.write_uint32(0)

        br.write_uint32(
            tuple(map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.model_chunks)))

        for group in self.nuccChunk.model_groups:
            br.write_struct(BrClumpModelGroup(), group, chunkIndexDict)

        br.write_int16(-1)


class BrClumpModelGroup(BrStruct):
    def __br_read__(self, br: 'BinaryReader') -> None:
        self.modelCount = br.read_int16()

        if self.modelCount != -1 and not br.eof():
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

        br.write_int32(tuple(map(lambda x: chunkIndexDict.get_or_next(
            x) if x else -1, model_group.model_chunks)))


class BrNuccChunkModel(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.field00 = br.read_uint16()
        # Affects if the model is correctly rigged to its bones or not
        self.riggingFlag = br.read_uint16()

        self.materialFlags = br.read_uint8(4)

        br.read_uint32()  # 0
        self.clumpIndex = br.read_uint32()
        self.hitIndex = br.read_uint32()

        # The mesh bone index might or might not be there. So instead, we look for the start of the NUD
        # to get its size, and then check to see if the "bone index" exists or not
        nudStart = br.buffer().find(b'NDP3')

        if nudStart == -1:
            # This shouldn't happen
            raise Exception(
                f'Could not find NDP3 magic in chunk: {self.name} of type: {type(self).__name__}')

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

        try:
            self.nud_data = br.buffer()[br.pos(): br.pos() + self.nudSize]
            self.brNud = BinaryReader(
                self.nud_data, Endian.BIG).read_struct(BrNud)
        except:
            print(
                f'Failed to read chunk: {self.name} of type: {type(self).__qualname__}')
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
        print(self.nuccChunk.clump_chunk.name)
        br.write_uint32(chunkIndexDict.get_or_next(self.nuccChunk.clump_chunk))
        br.write_uint32(chunkIndexDict.get_or_next(self.nuccChunk.hit_chunk))

        # Index of the mesh bone of this model in the clump
        # This might be shared by multiple models
        br.write_uint32(
            self.nuccChunk.coord_index if self.nuccChunk.coord_index != -1 else 0)

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
        br.write_uint32(tuple(
            map(lambda x: chunkIndexDict.get_or_next(x), self.nuccChunk.material_chunks)))


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

        self.textureGroups = br.read_struct(
            BrMaterialTextureGroup, self.groupCount)

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
        br.write_float(
            self.nuccChunk.floats[:self.float_count(self.nuccChunk.format)])

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
        br.write_uint32(tuple(
            map(lambda x: chunkIndexDict.get_or_next(x), texture_group.texture_chunks)))


class BrNuccChunkCoord(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.position = br.read_float(3)
        self.rotation = br.read_float(3)  # Rotation is in euler
        self.scale = br.read_float(3)
        self.unkFloat = br.read_float()   # Might be part of scale
        self.unkShort = br.read_uint16()  # Not always 0

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        node = self.nuccChunk.node

        br.write_float(node.position)
        br.write_float(node.rotation)
        br.write_float(node.scale)
        br.write_float(node.unkFloat)
        br.write_uint16(node.unkShort)


class BrNuccChunkModelHit(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)

        self.mesh_count = br.read_uint32()
        print(f'Mesh count {self.mesh_count}')
        self.total_vertex_size = br.read_uint32()  # multiplied by 3
        print(f'Total vertex size {self.total_vertex_size}')
        self.vertex_sections = br.read_struct(BrModelHit, self.mesh_count)

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        br.write_uint32(self.nuccChunk.mesh_count)

        br.write_uint32(self.nuccChunk.total_vertex_size)

        for hit in self.nuccChunk.vertex_sections:
            br.write_struct(BrModelHit(), hit)


class BrModelHit(BrStruct):
    def __br_read__(self, br: 'BinaryReader'):

        self.mesh_vertex_size = br.read_uint32()
        print(self.mesh_vertex_size)
        self.unk_count = br.read_uint8()
        print(self.unk_count)
        self.flags = br.read_uint8(3)
        print(self.flags)

        # Check if the next 8 bytes are padded
        if br.read_uint16() != 0:
            # version 79
            br.seek(-2, 1)
        else:
            # version 7A
            br.seek(-2, 1)
            self.unk = br.read_uint64()
        self.vertex_count = self.mesh_vertex_size * 3
        print(self.vertex_count)
        self.mesh_vertices = [br.read_float(3)
                              for i in range(self.vertex_count)]
        print(self.mesh_vertices)

    def __br_write__(self, br: 'BinaryReader', hit: 'ModelHit'):
        br.write_uint32(hit.mesh_vertex_size)
        br.write_uint8(hit.unk_count)
        br.write_uint8(hit.flags)
        for vertices in hit.mesh_vertices:
            br.write_float(vertices)


class BrNuccChunkBillboard(BrNuccChunk):
    def init_data(self, br: BinaryReader):
        super().init_data(br)
        self.data = br.read_uint8(len(br.buffer()))

    def __br_write__(self, br: 'BinaryReader', chunkIndexDict: IterativeDict):
        br.write_uint8(self.nuccChunk.data)
