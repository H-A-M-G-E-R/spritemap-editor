from src.romhandler import RomHandlerParent
from src.gfx import add_to_canvas_from_spritemap, bounding_box, to_qimage
from src.decompress import decompress
import base64, os, struct

def decode_spritemap_entry(entry):
    return {
        'x': entry[0] - (0x100 if entry[1] & 0x01 else 0),
        'y': (entry[2] & 0x7F) - (0x80 if entry[2] & 0x80 else 0),
        'big': entry[1] & 0x80 == 0x80,
        'tile': entry[3] + (0x100 if entry[4] & 0x01 else 0),
        'palette': entry[4] >> 1 & 0b111,
        'bg_priority': entry[4] >> 4 & 0b11,
        'h_flip': entry[4] & 0x40 == 0x40,
        'v_flip': entry[4] & 0x80 == 0x80
    }

def encode_spritemap_entry(entry):
    return (
        entry['x'] & 0xFF,
        ((entry['x'] & 0x100) >> 8) | (0x80 * entry['big']),
        entry['y'] & 0xFF,
        entry['tile'] & 0xFF,
        ((entry['tile'] & 0x100) >> 8) | ((entry['palette'] & 0b111) << 1) | ((entry['bg_priority'] & 0b11) << 4) | (0x40 * entry['h_flip']) | (0x80 * entry['v_flip'])
    )

def extract_generic(rom, gfx_addr, gfx_size, gfx_offset, pal_addr, pal_count, pal_offset, spritemap_range, ext_hitbox_range, ext_spritemap_range, name, compressed_gfx=False):
    if compressed_gfx:
        gfx = decompress(rom, gfx_addr) # ignore size when gfx is compressed
    else:
        gfx = rom.bulk_read_from_snes_address(gfx_addr, gfx_size*32)

    palette555 = rom.read_from_snes_address(pal_addr, '2'*(16*pal_count))
    palette888 = [int.from_bytes([
        255,                         # A
        (color555 & 0x1F) << 3,      # R
        (color555 >> 5 & 0x1F) << 3, # G
        (color555 >> 10 & 0x1F) << 3 # B
    ], 'big') for color555 in palette555]

    spritemaps = []
    curr_addr = spritemap_range[0]
    spritemap_i = 0
    while True:
        if spritemap_range[1] != None and curr_addr >= spritemap_range[1]:
            break

        count = rom.read_from_snes_address(curr_addr, 2)
        if count > 128: # there's a maximum of 128 OAM tiles
            break

        if curr_addr+2+count*5 > (spritemap_range[0] & 0xFF0000) + 0x10000: # abort if bankcross
            break

        spritemap = []
        for i in range(count):
            spritemap.append(decode_spritemap_entry(rom.bulk_read_from_snes_address(curr_addr+2+i*5, 5)))

        spritemaps.append({
            'name': f'{name}Spritemap_{spritemap_i:X}_{curr_addr:06X}',
            'spritemap': spritemap
        })
        curr_addr += 2+count*5
        spritemap_i += 1

    ext_hitboxes = []
    if ext_hitbox_range[0] != None:
        curr_addr = ext_hitbox_range[0]
        hitbox_i = 0
        while True:
            if ext_hitbox_range[1] != None and curr_addr >= ext_hitbox_range[1]:
                break

            count = rom.read_from_snes_address(curr_addr, 2)
            if curr_addr+2+count*12 > (ext_hitbox_range[0] & 0xFF0000) + 0x10000: # abort if bankcross
                break

            hitbox = []
            valid = True
            for i in range(count):
                left, top, right, bottom, touch, shot = rom.read_from_snes_address(curr_addr+2+i*12, '2'*6)
                if touch < 0x8000 or shot < 0x8000:
                    valid = False
                    break
                hitbox.append({
                    'left': left - (0x10000 if left >= 0x8000 else 0),
                    'top': top - (0x10000 if top >= 0x8000 else 0),
                    'right': right - (0x10000 if right >= 0x8000 else 0),
                    'bottom': bottom - (0x10000 if bottom >= 0x8000 else 0),
                    'touch': f'${touch:04X}',
                    'shot': f'${shot:04X}'
                })
            if not valid:
                break

            ext_hitboxes.append({
                'name': f'{name}Hitbox_{hitbox_i:X}_{curr_addr:06X}',
                'spritemap': None,
                'hitbox': hitbox
            })
            curr_addr += 2+count*12
            hitbox_i += 1

    ext_spritemaps = []
    if ext_spritemap_range[0] != None:
        curr_addr = ext_spritemap_range[0]
        ext_spritemap_i = 0
        while True:
            if ext_spritemap_range[1] != None and curr_addr >= ext_spritemap_range[1]:
                break

            count = rom.read_from_snes_address(curr_addr, 2)
            if count > 255: # for some reason there's a hard limit of 255 entries
                break

            if curr_addr+2+count*8 > (ext_spritemap_range[0] & 0xFF0000) + 0x10000: # abort if bankcross
                break

            ext_spritemap = []
            valid = True
            for i in range(count):
                x, y, spritemap, hitbox = rom.read_from_snes_address(curr_addr+2+i*8, '2'*4)
                if spritemap < 0x8000 or hitbox < 0x8000:
                    valid = False
                    break

                spritemap_found = False
                for s in spritemaps:
                    if f'{(spritemap_range[0]&0xFF0000)+spritemap:06X}' in s['name']:
                        spritemap = s['name']
                        spritemap_found = True
                        break
                if not spritemap_found:
                    spritemap = f'${spritemap:04X}'

                hitbox_found = False
                for h in ext_hitboxes:
                    if f'{(ext_hitbox_range[0]&0xFF0000)+hitbox:06X}' in h['name']:
                        hitbox = h['name']
                        if spritemap_found:
                            h['spritemap'] = spritemap
                        hitbox_found = True
                        break
                if not hitbox_found:
                    hitbox = f'${hitbox:04X}'

                ext_spritemap.append({
                    'x': x - (0x10000 if x >= 0x8000 else 0),
                    'y': y - (0x10000 if y >= 0x8000 else 0),
                    'spritemap': spritemap,
                    'hitbox': hitbox
                })
            if not valid:
                break

            ext_spritemaps.append({
                'name': f'{name}ExtSpritemap_{ext_spritemap_i:X}_{curr_addr:06X}',
                'ext_spritemap': ext_spritemap
            })
            curr_addr += 2+count*8
            ext_spritemap_i += 1

    return {
        'game': 'sm',
        'name': name,
        'gfx': str(base64.b64encode(gfx), 'utf8'),
        'palette': palette888,
        'gfx_offset': gfx_offset,
        'palette_offset': pal_offset,
        'spritemaps': spritemaps,
        'ext_hitboxes': ext_hitboxes,
        'ext_spritemaps': ext_spritemaps
    }

def extract_enemy(rom, id, spritemap_range, ext_hitbox_range, ext_spritemap_range, name):
    gfx_size = (rom.read_from_snes_address(0xA00000+id, 2) & 0x7FFF) // 32
    bank = rom.read_from_snes_address(0xA00000+id+0xC, 1)
    pal_addr = (bank<<16)+rom.read_from_snes_address(0xA00000+id+2, 2)
    gfx_addr = rom.read_from_snes_address(0xA00000+id+0x36, 3)

    return extract_generic(rom, gfx_addr, gfx_size, 256, pal_addr, 1, 0, spritemap_range, ext_hitbox_range, ext_spritemap_range, name)

def export_to_asm(data, folder_name):
    file = open(os.path.join(folder_name, data['name']+'.asm') , 'w')

    file.write(f'{data['name']}Gfx:\nincbin \"{data['name']+'.gfx'}\"\n\n')
    file.write(f'{data['name']}Pal:\nincbin \"{data['name']+'.pal'}\"\n')

    for spritemap in data['spritemaps']:
        file.write(f'\n{spritemap['name']}:\n')
        file.write(f'dw ${len(spritemap['spritemap']):04X}')
        if len(spritemap['spritemap']) > 0:
            file.write(' : db ' + ', '.join(','.join(f'${b:02X}' for b in encode_spritemap_entry(entry)) for entry in spritemap['spritemap']))
        file.write('\n')

    for hitbox in data['ext_hitboxes']:
        file.write(f'\n{hitbox['name']}:\n')
        file.write(f'dw ${len(hitbox['hitbox']):04X}')
        if len(hitbox['hitbox']) > 0:
            file.write(', ' + ', '.join(f'{entry['left']},{entry['top']},{entry['right']},{entry['bottom']},{entry['touch']},{entry['shot']}' for entry in hitbox['hitbox']))
        file.write('\n')

    for ext_spritemap in data['ext_spritemaps']:
        file.write(f'\n{ext_spritemap['name']}:\n')
        file.write(f'dw ${len(ext_spritemap['ext_spritemap']):04X}')
        if len(ext_spritemap['ext_spritemap']) > 0:
            file.write(', ' + ', '.join(f'{entry['x']},{entry['y']},{entry['spritemap']},{entry['hitbox']}' for entry in ext_spritemap['ext_spritemap']))
        file.write('\n')
    
    file = open(os.path.join(folder_name, data['name']+'.gfx') , 'wb')
    file.write(base64.b64decode(bytes(data['gfx'], 'utf8')))

    file = open(os.path.join(folder_name, data['name']+'.pal') , 'wb')
    palette555 = bytearray()
    for color in data['palette']:
        r = (color >> 16 & 0xFF) >> 3
        g = (color >> 8 & 0xFF) >> 3 << 5
        b = (color & 0xFF) >> 3 << 10
        palette555.extend(struct.pack('<H', r | g | b))
    file.write(palette555)

def export_to_png(data, folder_name):
    gfx = bytearray(base64.b64decode(bytes(data['gfx'], 'utf8')))
    palettes = []
    for i in range(data['palette_offset']):
        palettes.extend([0]+[0xFF000000]*16)
    for i in range(0, len(data['palette']), 16):
        palettes.extend([0]+data['palette'][i+1:i+16])
    for i in range(8-len(palettes)):
        palettes.extend([0]+[0xFF000000]*16)

    for spritemap in data['spritemaps']:
        canvas = {}
        for entry in reversed(spritemap['spritemap']):
            copied = entry.copy()
            copied['tile'] = entry['tile']-data['gfx_offset']
            copied['palette'] = entry['palette']-data['palette_offset']
            add_to_canvas_from_spritemap(canvas, [copied], gfx)

        (width, height) = bounding_box(canvas)
        image = to_qimage(canvas, palettes, -width, -height, width, height)
        image.save(os.path.join(folder_name, spritemap['name']+'.png'))

    for ext_spritemap in data['ext_spritemaps']:
        canvas = {}
        for ext_spritemap_entry in reversed(ext_spritemap['ext_spritemap']):
            spritemap_name = ext_spritemap_entry['spritemap']
            for spritemap in data['spritemaps']:
                if spritemap['name'] == spritemap_name:
                    break

            for entry in reversed(spritemap['spritemap']):
                copied = entry.copy()
                copied['x'] += ext_spritemap_entry['x']
                copied['y'] += ext_spritemap_entry['y']
                copied['tile'] = entry['tile']-data['gfx_offset']
                copied['palette'] = entry['palette']-data['palette_offset']
                add_to_canvas_from_spritemap(canvas, [copied], gfx)

        (width, height) = bounding_box(canvas)
        image = to_qimage(canvas, palettes, -width, -height, width, height)
        image.save(os.path.join(folder_name, ext_spritemap['name']+'.png'))
