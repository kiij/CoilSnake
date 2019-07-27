from coilsnake.exceptions.common.exceptions import CoilSnakeTraceableError
from coilsnake.model.eb.blocks import EbCompressibleBlock
from coilsnake.model.eb.graphics import EbGraphicTileset, EbTileArrangement
from coilsnake.model.eb.palettes import EbPalette
from coilsnake.model.eb.table import eb_table_from_offset
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.eb.pointer import from_snes_address, to_snes_address
from coilsnake.util.common.image import open_indexed_image
from coilsnake.util.common.yml import yml_dump, yml_load

import logging

log = logging.getLogger(__name__)

# The address of the animation table is hardcoded in two places in the rom.
# It is stored in the operands of a 'lda' instruction, which loads the value
# of its operand into the 'a' register. The registers are only 16-bits wide,
# so each time the 24-bit animation table address is loaded,
# it takes two of these instructions.
LDA_TABLE_ADDRESS_LOW    = from_snes_address(0xc47ab0)
LDA_TABLE_ADDRESS_HIGH   = from_snes_address(0xc47ab5)
LDA_TABLE_ADDRESS_2_LOW  = from_snes_address(0xc47b94)
LDA_TABLE_ADDRESS_2_HIGH = from_snes_address(0xc47b99)

# This is the default address of the animation table in the rom, pointed to by the
# 'lda' instructions above. We need this to get the format of the table from eb.yml.
ANIMATION_TABLE_DEFAULT_ADDRESS = 0xcc2de1

# All animations take up the entirety of the screen
SCREEN_WIDTH_TILES  = 32
SCREEN_HEIGHT_TILES = 28
TILE_WIDTH          = 8
TILE_HEIGHT         = 8
TILE_BPP            = 2


# Writes the new address of animation table into the assembly code
def write_animation_table_address(rom, address):
    # Replace operands in 'lda' instructions with our new offset
    address_low  =  address & 0x00FFFF
    address_high = (address & 0xFF0000) >> 16
    rom.write_multi(LDA_TABLE_ADDRESS_LOW    + 1, address_low,  2)
    rom.write_multi(LDA_TABLE_ADDRESS_HIGH   + 1, address_high, 1)
    rom.write_multi(LDA_TABLE_ADDRESS_2_LOW  + 1, address_low,  2)
    rom.write_multi(LDA_TABLE_ADDRESS_2_HIGH + 1, address_high, 1)

# Reads the address of the animation table from the assembly code
def read_animation_table_address(rom):
    # This is an immediate mode 'lda' instruction, so just skip the opcode and grab the operands
    low  = rom.read_multi(LDA_TABLE_ADDRESS_LOW  + 1, 2)
    high = rom.read_multi(LDA_TABLE_ADDRESS_HIGH + 1, 1)
    return (high << 16) | low


# Maybe make EbCompressedGraphic, but need support for multiple arrangements
class Animation:
    def __init__(self, frames, unknown, graphics_data_size=None):
        self.graphics_data_size = graphics_data_size
        self.frames = frames
        self.unknown = unknown

        if graphics_data_size:
            num_tiles = EbGraphicTileset.tiles_from_parameters(graphics_data_size, TILE_WIDTH, TILE_HEIGHT, TILE_BPP)
        else: # Make tileset with maximum number of tiles possible for each frame of animation
            num_tiles = SCREEN_WIDTH_TILES * SCREEN_HEIGHT_TILES * frames

        # Animations are 2 bpp, so the palette will have 4 colors
        self.palette = EbPalette(num_subpalettes=1, subpalette_length=4)
        self.graphics = EbGraphicTileset(num_tiles=num_tiles, tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
        self.arrangements = [EbTileArrangement(width=SCREEN_WIDTH_TILES, height=SCREEN_HEIGHT_TILES)
                             for i in range(self.frames)]

    def from_block(self, block, offset):
        with EbCompressibleBlock() as compressed_block:
            compressed_block.from_compressed_block(block=block, offset=offset)
            self.graphics.from_block(block=compressed_block, offset=0, bpp=TILE_BPP)
            next_offset = self.graphics_data_size
            self.palette.from_block(block=compressed_block, offset=next_offset)
            next_offset += self.palette.block_size()

            for arrangement in self.arrangements:
                arrangement.from_block(block=compressed_block, offset=next_offset)
                next_offset += arrangement.block_size()

    def to_block(self, block):
        self.graphics_data_size = self.graphics.block_size(bpp=TILE_BPP, trimmed=True)
        total_block_size = (self.graphics_data_size + self.palette.block_size() +
                            sum(arrangement.block_size() for arrangement in self.arrangements))

        with EbCompressibleBlock(total_block_size) as compressed_block:
            self.graphics.to_block(block=compressed_block, offset=0, bpp=TILE_BPP)
            next_offset = self.graphics_data_size
            self.palette.to_block(block=compressed_block, offset=next_offset)
            next_offset += self.palette.block_size()

            for arrangement in self.arrangements:
                arrangement.to_block(block=compressed_block, offset=next_offset)
                next_offset += arrangement.block_size()

            compressed_block.compress()
            return block.allocate(data=compressed_block)

    def images(self, arrangements=None):
        return [arrangement.image(self.graphics, self.palette) for arrangement in self.arrangements]

    def add_frame_from_image(self, image, frame_id):
        self.arrangements[frame_id].from_image(image, self.graphics, self.palette, is_animation=True)


class AnimationModule(EbModule):
    """ Extracts non-battle animations from Earthbound. """
    NAME = 'Animations'

    # Animation Data and Animation Sequence Pointers Table
    FREE_RANGES = [(0x0C0000, 0x0C2E18)]

    def __init__(self):
        super(AnimationModule, self).__init__()
        self.table = eb_table_from_offset(offset=ANIMATION_TABLE_DEFAULT_ADDRESS)
        self.animations = []

    def read_from_rom(self, rom):
        self.table.from_block(
            rom, offset=from_snes_address(read_animation_table_address(rom)))

        for index in range(self.table.num_rows):
            row = self.table[index]
            offset = row[0]
            graphics_data_size = row[1]
            frames  = row[2]
            unknown = row[3] # This field appears to be related somewhat to animation speed

            if graphics_data_size > 0: # Only add animations that have data
                animation = Animation(graphics_data_size=graphics_data_size, frames=frames, unknown=unknown)
                animation.from_block(rom, from_snes_address(offset))
                self.animations.append(animation)

    def write_to_rom(self, rom):
        # Write animations to rom
        animation_offsets = []
        for animation in self.animations:
            offset = animation.to_block(rom)
            animation_offsets.append(offset)

        # Build up animation table
        new_num_rows = len(self.animations) + 1 # Add 1 because the table is prefixed with an empty entry
        if self.table.num_rows != new_num_rows:
            self.table.recreate(new_num_rows)

        self.table[0] = [0, 0, 0, 0] # The first entry should be empty
        for i, animation in enumerate(self.animations):
            self.table[i + 1] = [to_snes_address(animation_offsets[i]), animation.graphics_data_size,
                                 animation.frames, animation.unknown]

        # Relocate animation table so we can store more than six animations
        new_table_offset = rom.allocate(size=self.table.size)
        write_animation_table_address(rom, to_snes_address(new_table_offset))
        self.table.to_block(rom, offset=new_table_offset)

    def read_from_project(self, resource_open):
        with resource_open('Animations/animations', 'yml', True) as f:
            animation_data = yml_load(f)

        for animation_id in animation_data:
            frames  = animation_data[animation_id]['frames']
            unknown = animation_data[animation_id]['unknown']
            animation = Animation(frames=frames, unknown=unknown)
            self.animations.append(animation)

            for frame_id in range(frames):
                with resource_open('Animations/{}/{}'.format(animation_id, str(frame_id).zfill(3)), 'png') as f:
                    image = open_indexed_image(f)
                    try:
                        animation.add_frame_from_image(image, frame_id)
                    except Exception as e:
                        message = 'Encountered error while reading frame #{} of Animation #{}'.format(frame_id,
                                                                                                      animation_id)
                        raise CoilSnakeTraceableError(message, e)

    def write_to_project(self, resource_open):
        animation_data = {}
        for i, animation in enumerate(self.animations):
            animation_data[i] = {'frames': animation.frames, 'unknown': animation.unknown}
            for j, image in enumerate(animation.images()):
                with resource_open('Animations/{}/{}'.format(i, str(j).zfill(3)), 'png') as f:
                    image.save(f, 'png')

        with resource_open('Animations/animations', 'yml', True) as f:
            yml_dump(animation_data, f, default_flow_style=False)

    def upgrade_project(self, old_version, new_version, rom, resource_open_r, resource_open_w, resource_delete):
        if old_version < 10:
            self.read_from_rom(rom)
            self.write_to_project(resource_open_w)
