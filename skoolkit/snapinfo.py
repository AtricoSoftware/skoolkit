# -*- coding: utf-8 -*-

# Copyright 2013-2016 Richard Dymond (rjdymond@gmail.com)
#
# This file is part of SkoolKit.
#
# SkoolKit is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# SkoolKit is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# SkoolKit. If not, see <http://www.gnu.org/licenses/>.

import argparse

from skoolkit import SkoolKitError, get_dword, get_int_param, get_word, read_bin_file, write_text, VERSION
from skoolkit.snapshot import get_snapshot

TOKENS = {
    165: 'RND',
    166: 'INKEY$',
    167: 'PI',
    168: 'FN',
    169: 'POINT',
    170: 'SCREEN$',
    171: 'ATTR',
    172: 'AT',
    173: 'TAB',
    174: 'VAL$',
    175: 'CODE',
    176: 'VAL',
    177: 'LEN',
    178: 'SIN',
    179: 'COS',
    180: 'TAN',
    181: 'ASN',
    182: 'ACS',
    183: 'ATN',
    184: 'LN',
    185: 'EXP',
    186: 'INT',
    187: 'SQR',
    188: 'SGN',
    189: 'ABS',
    190: 'PEEK',
    191: 'IN',
    192: 'USR',
    193: 'STR$',
    194: 'CHR$',
    195: 'NOT',
    196: 'BIN',
    197: 'OR',
    198: 'AND',
    199: '<=',
    200: '>=',
    201: '<>',
    202: 'LINE',
    203: 'THEN',
    204: 'TO',
    205: 'STEP',
    206: 'DEF FN',
    207: 'CAT',
    208: 'FORMAT',
    209: 'MOVE',
    210: 'ERASE',
    211: 'OPEN #',
    212: 'CLOSE #',
    213: 'MERGE',
    214: 'VERIFY',
    215: 'BEEP',
    216: 'CIRCLE',
    217: 'INK',
    218: 'PAPER',
    219: 'FLASH',
    220: 'BRIGHT',
    221: 'INVERSE',
    222: 'OVER',
    223: 'OUT',
    224: 'LPRINT',
    225: 'LLIST',
    226: 'STOP',
    227: 'READ',
    228: 'DATA',
    229: 'RESTORE',
    230: 'NEW',
    231: 'BORDER',
    232: 'CONTINUE',
    233: 'DIM',
    234: 'REM',
    235: 'FOR',
    236: 'GO TO',
    237: 'GO SUB',
    238: 'INPUT',
    239: 'LOAD',
    240: 'LIST',
    241: 'LET',
    242: 'PAUSE',
    243: 'NEXT',
    244: 'POKE',
    245: 'PRINT',
    246: 'PLOT',
    247: 'RUN',
    248: 'SAVE',
    249: 'RANDOMIZE',
    250: 'IF',
    251: 'CLS',
    252: 'DRAW',
    253: 'CLEAR',
    254: 'RETURN',
    255: 'COPY'
}

class BasicLister:
    def list_basic(self, snapshot):
        self.snapshot = snapshot
        i = (snapshot[23635] + 256 * snapshot[23636]) or 23755
        while i < len(snapshot) and snapshot[i] < 64:
            write_text('{: 4} '.format(snapshot[i] * 256 + snapshot[i + 1]))
            self.lspace = False
            i = self._print_basic_line(i + 4)

    def _print_basic_line(self, i):
        while self.snapshot[i] != 13:
            if self.snapshot[i] == 14:
                write_text(self._get_fp_num(i))
                i += 6
            else:
                write_text(self._get_chars(self.snapshot[i]))
                i += 1
        write_text('\n')
        return i + 1

    def _get_chars(self, code):
        if code <= 32:
            self.lspace = False
            return self._get_char(code)
        if code <= 164:
            self.lspace = True
            return self._get_char(code)
        return self._get_token(code)

    def _get_fp_num(self, i):
        j = i - 1
        num_str = ''
        while chr(self.snapshot[j]) in '0123456789.':
            num_str = chr(self.snapshot[j]) + num_str
            j -= 1
        if num_str:
            if self.snapshot[i + 1] == 0:
                sign = -1 if self.snapshot[i + 2] else 1
                num = sign * get_word(self.snapshot, i + 3)
            else:
                exponent = self.snapshot[i + 1] - 160
                sign = -1 if self.snapshot[i + 2] & 128 else 1
                mantissa = float(16777216 * (self.snapshot[i + 2] | 128)
                                 + 65536 * self.snapshot[i + 3]
                                 + 256 * self.snapshot[i + 4]
                                 + self.snapshot[i + 5])
                num = sign * mantissa * (2 ** exponent)
            if num and abs(1 - float(num_str) / num) > 1e-10:
                return '{{{}}}'.format(num)
        return ''

    def _get_char(self, code):
        if code == 94:
            return '↑'
        if code == 96:
            return '£'
        if code == 127:
            return '©'
        if 32 <= code <= 126:
            return chr(code)
        return '{{0x{:02X}}}'.format(code)

    def _get_token(self, code):
        token = TOKENS[code]
        if self.lspace and code >= 197 and token[0] >= 'A':
            token = ' ' + token
        self.lspace = True
        if code < 168 or code == 203 or token[-1] in '#=>':
            # RND, INKEY$, PI, THEN, '<=', '>=', '<>', 'OPEN #', 'CLOSE #'
            return token
        return token + ' '

class Registers:
    reg_map = {
        'b': 'bc', 'c': 'bc', 'b2': 'bc2', 'c2': 'bc2',
        'd': 'de', 'e': 'de', 'd2': 'de2', 'e2': 'de2',
        'h': 'hl', 'l': 'hl', 'h2': 'hl2', 'l2': 'hl2'
    }

    def get_lines(self):
        lines = []
        sep = ' ' * 4
        for row in (
            ('pc', 'sp'), ('ix', 'iy'), ('i', 'r'),
            ('b', 'b2'), ('c', 'c2'), ('bc', 'bc2'),
            ('d', 'd2'), ('e', 'e2'), ('de', 'de2'),
            ('h', 'h2'), ('l', 'l2'), ('hl', 'hl2'),
            ('a', 'a2')
        ):
            lines.append(self._reg(sep, *row))
        lines.append("  {0}    {1}   {0}".format("SZ5H3PNC", sep))
        lines.append("F {:08b}    {}F' {:08b}".format(self.f, sep, self.f2))
        return lines

    def _reg(self, sep, *registers):
        strings = []
        for reg in registers:
            name = reg.upper().replace('2', "'")
            size = len(name) - 1 if name.endswith("'") else len(name)
            value = self._get_value(reg)
            strings.append("{0:<3} {1:>5} {2:<{3}}{1:0{4}X}".format(name, value, "", (2 - size) * 2, size * 2))
        return sep.join(strings)

    def _get_value(self, register):
        try:
            return getattr(self, register)
        except AttributeError:
            reg_pair = self.reg_map[register]
            word = getattr(self, reg_pair)
            if register[0] == reg_pair[0]:
                return word // 256
            return word % 256

###############################################################################

# http://www.worldofspectrum.org/faq/reference/z80format.htm
# http://www.worldofspectrum.org/faq/reference/128kreference.htm

BLOCK_ADDRESSES_48K = {
    4: '32768-49151 8000-BFFF',
    5: '49152-65535 C000-FFFF',
    8: '16384-32767 4000-7FFF'
}

BLOCK_ADDRESSES_128K = {
    5: '32768-49151 8000-BFFF',
    8: '16384-32767 4000-7FFF'
}

V2_MACHINES = {
    0: ('48K Spectrum', '16K Spectrum', True),
    1: ('48K Spectrum + IF1', '16K Spectrum + IF1', True),
    2: ('SamRam', 'SamRam', False),
    3: ('128K Spectrum', 'Spectrum +2', False),
    4: ('128K Spectrum + IF1', 'Spectrum +2 + IF1', False)
}

V3_MACHINES = {
    0: ('48K Spectrum', '16K Spectrum', True),
    1: ('48K Spectrum + IF1', '16K Spectrum + IF1', True),
    2: ('SamRam', 'SamRam', False),
    3: ('48K Spectrum + MGT', '16K Spectrum + MGT', True),
    4: ('128K Spectrum', 'Spectrum +2', False),
    5: ('128K Spectrum + IF1', 'Spectrum +2 + IF1', False),
    6: ('128K Spectrum + MGT' 'Spectrum +2 + MGT', False),
}

MACHINES = {
    7: ('Spectrum +3', 'Spectrum +2A', False),
    8: ('Spectrum +3', 'Spectrum +2A', False),
    9: ('Pentagon (128K)', 'Pentagon (128K)', False),
    10: ('Scorpion (256K)', 'Scorpion (256K)', False),
    11: ('Didaktik+Kompakt', 'Didaktik+Kompakt', False),
    12: ('Spectrum +2', 'Spectrum +2', False),
    13: ('Spectrum +2A', 'Spectrum +2A', False),
    14: ('TC2048', 'TC2048', False),
    15: ('TC2068', 'TC2068', False),
    128: ('TS2068', 'TS2068', False),
}

def _analyse_z80(z80file):
    data = read_bin_file(z80file)

    # Extract header and RAM block(s)
    if get_word(data, 6) > 0:
        version = 1
        header = data[:30]
        ram_blocks = data[30:]
    else:
        header_len = 32 + get_word(data, 30)
        header = data[:header_len]
        ram_blocks = data[header_len:]
        version = 2 if header_len == 55 else 3

    # Print file name, version, machine, interrupt status, border, port $7FFD
    print('Z80 file: {}'.format(z80file))
    print('Version: {}'.format(version))
    bank = None
    if version == 1:
        machine = '48K Spectrum'
        block_dict = BLOCK_ADDRESSES_48K
    else:
        machine_dict = V2_MACHINES if version == 2 else V3_MACHINES
        machine_id = header[34]
        index = header[37] // 128
        machine_spec = machine_dict.get(machine_id, MACHINES.get(machine_id, ('Unknown', 'Unknown', True)))
        machine = machine_spec[index]
        if machine_spec[2]:
            block_dict = BLOCK_ADDRESSES_48K
        else:
            block_dict = BLOCK_ADDRESSES_128K
            bank = header[35] & 7
    print('Machine: {}'.format(machine))
    print('Interrupts: {}abled'.format('en' if header[28] else 'dis'))
    print('Interrupt mode: {}'.format(header[29] & 3))
    print('Border: {}'.format((header[12] // 2) & 7))
    if bank is not None:
        print('Port $7FFD: {} - bank {} (block {}) paged into 49152-65535 C000-FFFF'.format(header[35], bank, bank + 3))

    # Print register contents
    reg = Registers()
    reg.a = header[0]
    reg.f = header[1]
    reg.bc = get_word(header, 2)
    reg.hl = get_word(header, 4)
    if version == 1:
        reg.pc = get_word(header, 6)
    else:
        reg.pc = get_word(header, 32)
    reg.sp = get_word(header, 8)
    reg.i = header[10]
    reg.r = 128 * (header[12] & 1) + (header[11] & 127)
    reg.de = get_word(header, 13)
    reg.bc2 = get_word(header, 15)
    reg.de2 = get_word(header, 17)
    reg.hl2 = get_word(header, 19)
    reg.a2 = header[21]
    reg.f2 = header[22]
    reg.iy = get_word(header, 23)
    reg.ix = get_word(header, 25)
    print('Registers:')
    for line in reg.get_lines():
        print('  ' + line)

    # Print RAM block info
    if version == 1:
        block_len = len(ram_blocks)
        prefix = '' if header[12] & 32 else 'un'
        print('48K RAM block (16384-65535 4000-FFFF): {} bytes ({}compressed)'.format(block_len, prefix))
    else:
        i = 0
        while i < len(ram_blocks):
            block_len = get_word(ram_blocks, i)
            page_num = ram_blocks[i + 2]
            addr_range = block_dict.get(page_num)
            if addr_range is None:
                if page_num == bank + 3:
                    addr_range = '49152-65535 C000-FFFF'
            if addr_range:
                addr_range = ' ({})'.format(addr_range)
            else:
                addr_range = ''
            i += 3
            if block_len == 65535:
                block_len = 16384
                prefix = 'un'
            else:
                prefix = ''
            print('RAM block {}{}: {} bytes ({}compressed)'.format(page_num, addr_range, block_len, prefix))
            i += block_len

###############################################################################

# http://www.spectaculator.com/docs/zx-state/intro.shtml

SZX_MACHINES = {
    0: '16K ZX Spectrum',
    1: '48K ZX Spectrum',
    2: 'ZX Spectrum 128',
    3: 'ZX Spectrum +2',
    4: 'ZX Spectrum +2A/+2B',
    5: 'ZX Spectrum +3',
    6: 'ZX Spectrum +3e'
}

def _get_block_id(data, index):
    return ''.join([chr(b) for b in data[index:index+ 4]])

def _print_ramp(block, variables):
    lines = []
    flags = get_word(block, 0)
    compressed = 'compressed' if flags & 1 else 'uncompressed'
    page = block[2]
    ram = block[3:]
    lines.append("Page: {}".format(page))
    machine_id = variables['chMachineId']
    addresses = ''
    if page == 5:
        addresses = '16384-32767 4000-7FFF'
    elif page == 2:
        addresses = '32768-49151 8000-BFFF'
    elif machine_id > 1 and page == variables['ch7ffd'] & 7:
        addresses = '49152-65535 C000-FFFF'
    if addresses:
        addresses += ': '
    lines.append("RAM: {}{} bytes, {}".format(addresses, len(ram), compressed))
    return lines

def _print_spcr(block, variables):
    lines = []
    lines.append('Border: {}'.format(block[0]))
    ch7ffd = block[1]
    variables['ch7ffd'] = ch7ffd
    bank = ch7ffd & 7
    lines.append('Port $7FFD: {} (bank {} paged into 49152-65535 C000-FFFF)'.format(ch7ffd, bank))
    return lines

def _print_z80r(block, variables):
    lines = []
    lines.append('Interrupts: {}abled'.format('en' if block[27] else 'dis'))
    lines.append('Interrupt mode: {}'.format(block[28]))
    reg = Registers()
    reg.f = block[0]
    reg.a = block[1]
    reg.bc = get_word(block, 2)
    reg.de = get_word(block, 4)
    reg.hl = get_word(block, 6)
    reg.f2 = block[8]
    reg.a2 = block[9]
    reg.bc2 = get_word(block, 10)
    reg.de2 = get_word(block, 12)
    reg.hl2 = get_word(block, 14)
    reg.ix = get_word(block, 16)
    reg.iy = get_word(block, 18)
    reg.sp = get_word(block, 20)
    reg.pc = get_word(block, 22)
    reg.i = block[24]
    reg.r = block[25]
    return lines + reg.get_lines()

SZX_BLOCK_PRINTERS = {
    'RAMP': _print_ramp,
    'SPCR': _print_spcr,
    'Z80R': _print_z80r
}

def _analyse_szx(szxfile):
    szx = read_bin_file(szxfile)

    magic = _get_block_id(szx, 0)
    if magic != 'ZXST':
        raise SkoolKitError("{} is not an SZX file".format(szxfile))

    print('Version: {}.{}'.format(szx[4], szx[5]))
    machine_id = szx[6]
    print('Machine: {}'.format(SZX_MACHINES.get(machine_id, 'Unknown')))
    variables = {'chMachineId': machine_id}

    i = 8
    while i < len(szx):
        block_id = _get_block_id(szx, i)
        block_size = get_dword(szx, i + 4)
        i += 8
        print('{}: {} bytes'.format(block_id, block_size))
        printer = SZX_BLOCK_PRINTERS.get(block_id)
        if printer:
            for line in printer(szx[i:i + block_size], variables):
                print("  " + line)
        i += block_size

###############################################################################

# http://www.worldofspectrum.org/faq/reference/formats.htm#SNA

def _print_ram_banks(sna):
    bank = sna[49181] & 7
    print('RAM bank 5 (16384 bytes: 16384-32767 4000-7FFF)')
    print('RAM bank 2 (16384 bytes: 32768-49151 8000-BFFF)')
    print('RAM bank {} (16384 bytes: 49152-65535 C000-FFFF)'.format(bank))
    size = len(sna) - 49183
    for b in sorted({0, 1, 3, 4, 6, 7} - {bank}):
        prefix = 'RAM bank {}'.format(b)
        if size >= 16384:
            desc = '16384 bytes'
        elif size > 0:
            desc = 'truncated: {} bytes'.format(size)
        else:
            desc = 'missing'
        print('RAM bank {} ({})'.format(b, desc))
        size -= 16384

def _analyse_sna(snafile):
    sna = read_bin_file(snafile, 147487)
    is128 = len(sna) > 49179

    print('RAM: {}K'.format(128 if is128 else 48))
    print('Interrupts: {}abled'.format('en' if sna[19] & 4 else 'dis'))
    print('Interrupt mode: {}'.format(sna[25]))
    print('Border: {}'.format(sna[26] & 7))

    # Print register contents
    reg = Registers()
    reg.i = sna[0]
    reg.hl2 = get_word(sna, 1)
    reg.de2 = get_word(sna, 3)
    reg.bc2 = get_word(sna, 5)
    reg.f2 = sna[7]
    reg.a2 = sna[8]
    reg.hl = get_word(sna, 9)
    reg.de = get_word(sna, 11)
    reg.bc = get_word(sna, 13)
    reg.iy = get_word(sna, 15)
    reg.ix = get_word(sna, 17)
    reg.r = sna[20]
    reg.f = sna[21]
    reg.a = sna[22]
    reg.sp = get_word(sna, 23)
    if is128:
        reg.pc = get_word(sna, 49179)
    else:
        reg.pc = get_word(sna, reg.sp - 16357)
    print('Registers:')
    for line in reg.get_lines():
        print('  ' + line)

    if is128:
        _print_ram_banks(sna)

###############################################################################

def _find(infile, byte_seq):
    step = 1
    if '-' in byte_seq:
        byte_seq, step = byte_seq.split('-', 1)
        step = get_int_param(step)
    byte_values = [get_int_param(i) for i in byte_seq.split(',')]
    offset = step * len(byte_values)
    snapshot = get_snapshot(infile)
    for a in range(16384, 65537 - offset):
        if snapshot[a:a + offset:step] == byte_values:
            print("{0}-{1}-{2} {0:04X}-{1:04X}-{2}: {3}".format(a, a + offset - step, step, byte_seq))

def _find_text(infile, text):
    size = len(text)
    byte_values = [ord(c) for c in text]
    snapshot = get_snapshot(infile)
    for a in range(16384, 65536 - size + 1):
        if snapshot[a:a + size] == byte_values:
            print("{0}-{1} {0:04X}-{1:04X}: {2}".format(a, a + size - 1, text))

def _peek(infile, specs):
    snapshot = get_snapshot(infile)
    for addr_range in specs:
        step = 1
        if '-' in addr_range:
            addr1, addr2 = addr_range.split('-', 1)
            addr1 = get_int_param(addr1)
            if '-' in addr2:
                addr2, step = [get_int_param(i) for i in addr2.split('-', 1)]
            else:
                addr2 = get_int_param(addr2)
        else:
            addr1 = addr2 = get_int_param(addr_range)
        for a in range(addr1, addr2 + 1, step):
            value = snapshot[a]
            if 32 <= value <= 126:
                char = chr(value)
            else:
                char = ''
            print('{0:>5} {0:04X}: {1:>3}  {1:02X}  {1:08b}  {2}'.format(a, value, char))

def main(args):
    parser = argparse.ArgumentParser(
        usage='snapinfo.py [options] file',
        description="Analyse an SNA, SZX or Z80 snapshot.",
        add_help=False
    )
    parser.add_argument('infile', help=argparse.SUPPRESS, nargs='?')
    group = parser.add_argument_group('Options')
    group.add_argument('-b', '--basic', action='store_true',
                       help='List the BASIC program')
    group.add_argument('-f', '--find', metavar='A[,B...[-N]]',
                       help='Search for the byte sequence A,B... with distance N (default=1) between bytes')
    group.add_argument('-p', '--peek', metavar='A[-B[-C]]', action='append',
                       help='Show the contents of addresses A TO B STEP C; this option may be used multiple times')
    group.add_argument('-t', '--find-text', dest='text', metavar='TEXT',
                       help='Search for a text string')
    group.add_argument('-V', '--version', action='version', version='SkoolKit {}'.format(VERSION),
                       help='Show SkoolKit version number and exit')
    namespace, unknown_args = parser.parse_known_args(args)
    if unknown_args or namespace.infile is None:
        parser.exit(2, parser.format_help())
    infile = namespace.infile
    snapshot_type = infile[-4:].lower()
    if snapshot_type not in ('.sna', '.szx', '.z80'):
        raise SkoolKitError('Unrecognised snapshot type')

    if namespace.find is not None:
        _find(infile, namespace.find)
    elif namespace.text is not None:
        _find_text(infile, namespace.text)
    elif namespace.peek is not None:
        _peek(infile, namespace.peek)
    elif namespace.basic:
        BasicLister().list_basic(get_snapshot(infile))
    elif snapshot_type == '.sna':
        _analyse_sna(infile)
    elif snapshot_type == '.z80':
        _analyse_z80(infile)
    else:
        _analyse_szx(infile)