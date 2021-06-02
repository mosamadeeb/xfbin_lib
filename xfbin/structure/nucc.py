from typing import List, Optional

from ..util import *
from .br.br_nucc import *
from .br.br_nud import *
from .br.br_nut import *
from .nud import Nud


class NuccChunk:
    filePath: str
    name: str
    data: bytearray

    extension: str

    def __init__(self, file_path, name):
        self.extension = ''
        self.filePath = file_path
        self.name = name

    def init_data(self, br_chunk: BrNuccChunk, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        """Initializes the data of this `NuccChunk` from a `BrNuccChunk`, using a chunk list and a list of
        local page indices for properly setting references to other `NuccChunk`s
        """
        self.data = br_chunk.data

    @classmethod
    def get_nucc_type_from_str(cls, type_str: str) -> type:
        type_name = type_str[0].upper() + type_str[1:]
        result = globals().get(type_name, None)

        if result is None:
            # Create a new type and add it to the globals
            result = type(type_name, (cls,), {})
            globals()[type_name] = result

        return result

    @classmethod
    def get_nucc_str_from_type(cls, nucc_type: type) -> str:
        return nucc_type.__name__[0].lower() + nucc_type.__name__[1:]

    @classmethod
    def create_from_nucc_type(cls, type_str, file_path, name) -> 'NuccChunk':
        return cls.get_nucc_type_from_str(type_str)(file_path, name)

    @classmethod
    def get_all_nucc_types(cls):
        # This will only return types with names that start with this class's name (but are not this class)
        return [n for (k, n) in globals() if k.startswith(cls.__qualname__) and len(k) > len(cls.__qualname__)]

    def __eq__(self, o: object) -> bool:
        # Treat NuccChunks as ChunkMaps:
        # ChunkMaps are only equal to other ChunkMaps that have the same type, file path, and name
        return isinstance(o, type(self)) and self.filePath == o.filePath and self.name == o.name

    def __hash__(self) -> int:
        # Just a simple hash calculation to allow NuccChunks to be put into a dictionary
        return hash(type(self).__qualname__) ^ hash(self.filePath) ^ hash(self.name)


class NuccChunkNull(NuccChunk):
    # Empty
    def __init__(self, file_path='', name=''):
        super().__init__(file_path, name)


class NuccChunkPage(NuccChunk):
    # Should not be used as a NuccChunk, except when writing
    def __init__(self, file_path='', name='Page0'):
        super().__init__(file_path, name)


class NuccChunkIndex(NuccChunk):
    # Does not exist
    def __init__(self, file_path='', name='index'):
        super().__init__(file_path, name)


class NuccChunkTexture(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkTexture, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.nut'

        self.width = br_chunk.width
        self.height = br_chunk.width

        # TODO: Implement Nut
        #self.nut = Nut(br_chunk.brNut)


class NuccChunkDynamics(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkDynamics, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.dynamics'


class NuccChunkAnm(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkAnm, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.anm'


class NuccChunkClump(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkClump, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.clump'

        # Get the coord chunks
        self.coord_chunks: List[NuccChunkCoord] = list()
        for i in br_chunk.coordNodeIndices:
            self.coord_chunks.append(chunk_list[chunk_indices[i]])

        # Setup the coord node hierarchy
        self.root_nodes: List[CoordNode] = list()
        for i, j in zip(range(len(self.coord_chunks)), br_chunk.coordNodeParentsIndices):
            if j == -1:
                # There could be multiple root nodes: add all of them
                self.root_nodes.append(self.coord_chunks[i].node)
            else:
                # Set the node's parent and add the node to its parent's children
                self.coord_chunks[i].node.parent = self.coord_chunks[j].node
                self.coord_chunks[j].node.children.append(self.coord_chunks[i].node)

        # Get the model chunks
        self.model_chunks: List[NuccChunkModel] = list()
        for i in br_chunk.modelIndices:
            self.model_chunks.append(chunk_list[chunk_indices[i]])

        # Initialize the model groups
        self.model_groups: List[ClumpModelGroup] = list()
        for model_group in br_chunk.modelGroups:
            self.model_groups.append(ClumpModelGroup(model_group, chunk_list, chunk_indices))


class ClumpModelGroup:
    def __init__(self, model_group: BrClumpModelGroup, chunk_list: List['NuccChunk'], chunk_indices: List[int]):
        self.model_chunks: List[NuccChunkModel] = list(
            map(lambda x: chunk_list[chunk_indices[x]], model_group.modelIndices))


class NuccChunkCoord(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkCoord, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.coord'

        self.node = CoordNode(br_chunk)


class CoordNode:
    parent: Optional['CoordNode']
    children: List['CoordNode']

    def __init__(self, coord: BrNuccChunkCoord):
        self.name = coord.name
        self.parent = None
        self.children = list()

        self.position = coord.position
        self.rotation = coord.rotation
        self.scale = coord.scale
        self.unkFloat = coord.unkFloat
        self.unkShort = coord.unkShort

    def get_children_recursive(self) -> List['CoordNode']:
        result = list()

        for child in self.children:
            result.extend(child.get_children_recursive())

        return result


class NuccChunkModel(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkModel, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.nud'

        # Create a Nud from the BrNud
        self.nud = Nud(self.name, br_chunk.brNud)

        # Get the material chunks
        self.material_chunks: List[NuccChunkMaterial] = list()
        for i in br_chunk.materialIndices:
            self.material_chunks.append(chunk_list[chunk_indices[i]])


class NuccChunkMaterial(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkMaterial, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.material'


class NuccChunkBillboard(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkBillboard, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.billboard'


class NuccChunkTrail(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkTrail, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.trail'


class NuccChunkCamera(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkCamera, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.cam'


class NuccChunkParticle(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkParticle, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.particle'


class NuccChunkBinary(NuccChunk):
    def init_data(self, br_chunk: BrNuccChunkBinary, chunk_list: List['NuccChunk'], chunk_indices: List[int], reference_indices: List[int]):
        super().init_data(br_chunk, chunk_list, chunk_indices, reference_indices)
        self.extension = '.bin'
