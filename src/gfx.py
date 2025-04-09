import numpy as np
from PySide6.QtGui import QImage

''' Modified From SpriteSomething (https://github.com/Artheau/SpriteSomething) '''
def add_to_canvas_from_spritemap(canvas, tilemaps, graphics, priority_filter=None):
    # expects:
    #  a dictionary of spritemap entries
    #  a bytearray or list of bytes of 4bpp graphics

    for tilemap in reversed(tilemaps):
        x_offset = tilemap['x']
        y_offset = tilemap['y']
        big_tile = tilemap['big']
        index = tilemap['tile']
        palette = tilemap['palette']
        priority = tilemap['bg_priority']
        h_flip = tilemap['h_flip']
        v_flip = tilemap['v_flip']

        def draw_tile_to_canvas(new_x_offset, new_y_offset, new_index):
            if new_index < 0 or new_index*32 > len(graphics)-32: # check for oob
                return
            tile_to_write = convert_tile_from_bitplanes(graphics[new_index*32:new_index*32+32])
            if h_flip:
                tile_to_write = np.fliplr(tile_to_write)
            if v_flip:
                tile_to_write = np.flipud(tile_to_write)
            for (i, j), value in np.ndenumerate(tile_to_write):
                if value != 0:  # if not transparent
                    canvas[(new_x_offset + j, new_y_offset + i)] = palette * 0x10 + int(value)

        if priority_filter != None and priority != priority_filter:
            break

        if big_tile:  # draw all four 8x8 tiles
            draw_tile_to_canvas(x_offset + (8 if h_flip else 0),
                                y_offset + (8 if v_flip else 0), index)
            draw_tile_to_canvas(x_offset + (0 if h_flip else 8),
                                y_offset + (8 if v_flip else 0), index + 0x01)
            draw_tile_to_canvas(x_offset + (8 if h_flip else 0),
                                y_offset + (0 if v_flip else 8), index + 0x10)
            draw_tile_to_canvas(x_offset + (0 if h_flip else 8),
                                y_offset + (0 if v_flip else 8), index + 0x11)
        else:
            draw_tile_to_canvas(x_offset, y_offset, index)

def bounding_box(canvas):
    '''Returns the minimum bounding box centered at the middle without cropping a single pixel'''
    if canvas.keys():
        x_min = min([x for (x, y) in canvas.keys()])
        x_max = max([x for (x, y) in canvas.keys()]) + 1
        y_min = min([y for (x, y) in canvas.keys()])
        y_max = max([y for (x, y) in canvas.keys()]) + 1

        return (max(abs(x_min), abs(x_max)), max(abs(y_min), abs(y_max)))
    else:
        return (0, 0)

def to_qimage(canvas, palette, left, top, right, bottom):
    '''Returns a QImage cropped by a bounding box'''
    image = QImage(right-left, bottom-top, QImage.Format_Indexed8)
    image.fill(0) # fill image with transparency

    # add the palette
    image.setColorTable(palette)

    # add the pixels
    if canvas.keys():
        for (i, j), value in canvas.items():
            image.setPixel(i-left, j-top, value)

    return image

def convert_tile_from_bitplanes(raw_tile):
    # See https://snes.nesdev.org/wiki/Tiles for the format
    # an attempt to make this ugly process mildly efficient

    # axes 1 and 0 are the rows and columns of the image, respectively
    # numpy has the axes swapped
    tile = np.zeros((8, 1, 4), dtype=np.uint8)

    tile[:, 0, 0] = raw_tile[0:16:2] # bitplane 0
    tile[:, 0, 1] = raw_tile[1:17:2] # bitplane 1
    tile[:, 0, 2] = raw_tile[16:32:2] # bitplane 2
    tile[:, 0, 3] = raw_tile[17:33:2] # bitplane 3

    tile_bits = np.unpackbits(tile, axis=1, bitorder='big') # decompose the bitplanes to rows
    fixed_bits = np.packbits(tile_bits, axis=2, bitorder='little') # combine the bitplanes
    returnvalue = fixed_bits.reshape(8, 8)
    return returnvalue

def convert_to_4bpp(image):
    '''Converts a QImage to SNES 4bpp tiles as bytearray'''
    if image.format() != QImage.Format_Indexed8:
        raise AssertionError('Format must be indexed color')

    output = bytearray()

    for y in range(0, image.height(), 8):
        for x in range(0, image.width(), 8):
            tile = image.copy(x, y, 8, 8)
            output.extend(convert_indexed_tile_to_bitplanes(tile.constBits()))

    return output

def convert_indexed_tile_to_bitplanes(indexed_tile):
    # this should literally just be the inverse of
    #  convert_tile_from_bitplanes(), and so it was written in this way
    fixed_bits = np.array(indexed_tile, dtype=np.uint8).reshape(8, 8, 1)
    tile_bits = np.unpackbits(fixed_bits, axis=2, bitorder='little')
    tile = np.packbits(tile_bits, axis=1, bitorder='big')

    low_bitplanes = np.ravel(tile[:, 0, 0:2])
    high_bitplanes = np.ravel(tile[:, 0, 2:4])
    return np.append(low_bitplanes, high_bitplanes)
