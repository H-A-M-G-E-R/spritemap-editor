from src.romhandler import RomHandlerParent

''' Based on https://patrickjohnston.org/ASM/ROM%20data/Super%20Metroid/decompress.py '''
def decompress(rom, start):
    curr_addr = rom.convert_to_pc_address(start) # for bankcross
    decompressed = bytearray()
    while True:
        byte = rom.read(curr_addr, 1)
        curr_addr += 1
        if byte == 0xFF:
            break

        command = byte >> 5
        if command != 7:
            size = (byte & 0x1F) + 1
        else:
            size = ((byte & 3) << 8 | rom.read(curr_addr, 1)) + 1
            curr_addr += 1
            command = byte >> 2 & 7

        if command == 0:
            decompressed.extend(rom.bulk_read(curr_addr, size))
            curr_addr += size
        elif command == 1:
            decompressed.extend([rom.read(curr_addr, 1)] * size)
            curr_addr += 1
        elif command == 2:
            byte = rom.read(curr_addr, 1)
            curr_addr += 1
            decompressed.extend([byte, rom.read(curr_addr, 1)] * (size >> 1))
            curr_addr += 1
            if size & 1:
                decompressed.append(byte)
        elif command == 3:
            byte = rom.read(curr_addr, 1)
            curr_addr += 1
            decompressed.extend(b & 0xFF for b in range(byte, byte + size))
        elif command == 4:
            offset = rom.read(curr_addr, 2)
            curr_addr += 2
            for i in range(offset, offset + size):
                decompressed.append(decompressed[i])
        elif command == 5:
            offset = rom.read(curr_addr, 2)
            curr_addr += 2
            for i in range(offset, offset + size):
                decompressed.append(decompressed[i] ^ 0xFF)
        elif command == 6:
            offset = len(decompressed) - rom.read(curr_addr, 1)
            curr_addr += 1
            for i in range(offset, offset + size):
                decompressed.append(decompressed[i])
        elif command == 7:
            offset = len(decompressed) - rom.read(curr_addr, 1)
            curr_addr += 1
            for i in range(offset, offset + size):
                decompressed.append(decompressed[i] ^ 0xFF)

    return decompressed
