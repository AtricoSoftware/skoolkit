# Copyright 2022, 2023 Richard Dymond (rjdymond@gmail.com)
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

class Accelerator:
    def __init__(self, name, code, in_time, loop_time, loop_r_inc, ear_mask):
        self.name = name
        self.opcode = code[0]
        self.code = code[1:]
        self.in_time = in_time
        self.loop_time = loop_time
        self.loop_r_inc = loop_r_inc
        self.ear_mask = ear_mask

ACCELERATORS = {
    'alkatraz': Accelerator(
        'alkatraz',
        [
            0x04,             # LD_SAMPLE  INC B            [4]
            0x20, 0x03,       #            JR NZ,LD_SAMPLE2 [12/7]
            None, None, None, #
            0xDB, 0xFE,       # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,             #            RRA              [4]
            0xC8,             #            RET Z            [11/5]
            0xA9,             #            XOR C            [4]
            0xE6, 0x20,       #            AND $20          [7]
            0x28, 0xF1        #            JR Z,LD_SAMPLE   [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alkatraz-05': Accelerator(
        'alkatraz-05',
        [
            0x04,                         # LD_SAMPLE  INC B            [4]
            0x20, 0x05,                   #            JR NZ,LD_SAMPLE2 [12/7]
            None, None, None, None, None, #
            0xDB, 0xFE,                   # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,                         #            RRA              [4]
            0xC8,                         #            RET Z            [11/5]
            0xA9,                         #            XOR C            [4]
            0xE6, 0x20,                   #            AND $20          [7]
            0x28, 0xEF                    #            JR Z,LD_SAMPLE   [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alkatraz-09': Accelerator(
        'alkatraz-09',
        [
            0x04,                         # LD_SAMPLE  INC B            [4]
            0x20, 0x09,                   #            JR NZ,LD_SAMPLE2 [12/7]
            None, None, None, None, None, #
            None, None, None, None,       #
            0xDB, 0xFE,                   # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,                         #            RRA              [4]
            0xC8,                         #            RET Z            [11/5]
            0xA9,                         #            XOR C            [4]
            0xE6, 0x20,                   #            AND $20          [7]
            0x28, 0xEB                    #            JR Z,LD_SAMPLE   [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alkatraz-0a': Accelerator(
        'alkatraz-0a',
        [
            0x04,                         # LD_SAMPLE  INC B            [4]
            0x20, 0x0A,                   #            JR NZ,LD_SAMPLE2 [12/7]
            None, None, None, None, None, #
            None, None, None, None, None, #
            0xDB, 0xFE,                   # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,                         #            RRA              [4]
            0xC8,                         #            RET Z            [11/5]
            0xA9,                         #            XOR C            [4]
            0xE6, 0x20,                   #            AND $20          [7]
            0x28, 0xEA,                   #            JR Z,LD_SAMPLE   [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alkatraz-0b': Accelerator(
        'alkatraz-0b',
        [
            0x04,                         # LD_SAMPLE  INC B            [4]
            0x20, 0x0B,                   #            JR NZ,LD_SAMPLE2 [12/7]
            None, None, None, None, None, #
            None, None, None, None, None, #
            None,                         #
            0xDB, 0xFE,                   # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,                         #            RRA              [4]
            0xC8,                         #            RET Z            [11/5]
            0xA9,                         #            XOR C            [4]
            0xE6, 0x20,                   #            AND $20          [7]
            0x28, 0xE9,                   #           JR Z,LD_SAMPLE    [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alkatraz2': Accelerator(
        'alkatraz2',
        [
            0x04,       # LD_SAMPLE  INC B            [4]
            0x20, 0x01, #            JR NZ,LD_SAMPLE2 [12/7]
            0xC9,       #            RET              [10]
            0xDB, 0xFE, # LD_SAMPLE2 IN A,($FE)       [11]
            0x1F,       #            RRA              [4]
            0xC8,       #            RET Z            [11/5]
            0xA9,       #            XOR C            [4]
            0xE6, 0x20, #            AND $20          [7]
            0x28, 0xF3  #            JR Z,LD_SAMPLE   [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alternative': Accelerator(
        'alternative',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xCB, 0x1F, #           RR A           [8]
            0x00,       #           NOP            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF2  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        62,   # 62 T-states per loop iteration
        10,   # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'alternative2': Accelerator(
        'alternative2',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xCB, 0x1F, #           RR A           [8]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF2  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        63,   # 63 T-states per loop iteration
        10,   # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'bleepload': Accelerator(
        'bleepload',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0x00,       #           NOP            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        58,   # 58 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'boguslaw-juza': Accelerator(
        'boguslaw-juza',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xD6, 0x00, #           SUB $00        [7]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF2  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        61,   # 61 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'crl': Accelerator(
        'crl',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xB7,       #           OR A           [4]
            0xD8,       #           RET C          [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'crl2': Accelerator(
        'crl2',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        21,   # 21 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'crl3': Accelerator(
        'crl3',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0x28, None, #           JR Z,nn        [12/7]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0x30, None, #           JR NC,nn       [12/7]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF1, #           JR Z,LD_SAMPLE [12/7]
        ],
        18,   # 18 T-states until first IN A,($FE)
        63,   # 63 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'crl4': Accelerator(
        'crl4',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF2  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        61,   # 61 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'cybexlab': Accelerator(
        'cybexlab',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xAF      , #           XOR A          [4]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF4  #           JR Z,LD_SAMPLE [12/7]
        ],
        13,   # 13 T-states until first IN A,($FE)
        56,   # 56 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'd-and-h': Accelerator(
        'd-and-h',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xED, 0x4F, #           LD R,A         [9]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF3, #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        0,    # R register increment per loop iteration (irrelevant)
        0x40  # EAR mask
    ),

    'delphine': Accelerator(
        'delphine',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA7,       #           AND A          [4]
            0xD8,       #           RET C          [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF3, #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'design-design': Accelerator(
        'design-design',
        [
            0x04,             # LD_SAMPLE INC B          [4]
            0xCA, None, None, #           JP Z,nn        [10]
            0x3E, 0x7F,       #           LD A,$7F       [7]
            0xDB, 0xFE,       #           IN A,($FE)     [11]
            0x1F,             #           RRA            [4]
            0xA9,             #           XOR C          [4]
            0xE6, 0x20,       #           AND $20        [7]
            0x28, 0xF2        #           JR Z,LD_SAMPLE [12/7]
        ],
        21,   # 21 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'digital-integration': Accelerator(
        'digital-integration',
        [
            0x05,       # LD_SAMPLE DEC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0xCA        #           JP Z,LD_SAMPLE [10]
        ],
        9,    # 9 T-states until first IN A,($FE)
        41,   # 41 T-states per loop iteration
        6,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'dinaload': Accelerator(
        'dinaload',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0xFF, #           LD A,$FF       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'gremlin': Accelerator(
        'gremlin',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF5  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        50,   # 50 T-states per loop iteration
        7,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'gremlin2': Accelerator(
        'gremlin2',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0xFF, #           LD A,$FF       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0xD8,       #           RET C          [11/5]
            0x00,       #           NOP            [4]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'microprose': Accelerator(
        'microprose',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xC8,       #           RET Z          [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF5  #           JR Z,LD_SAMPLE [12/7]
        ],
        9,    # 9 T-states until first IN A,($FE)
        52,   # 52 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'microsphere': Accelerator(
        'microsphere',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA7,       #           AND A          [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        58,   # 58 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'micro-style': Accelerator(
        'micro-style',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0x00,       #           NOP            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF1, #           JR Z,LD_SAMPLE [12/7]
        ],
        23,   # 23 T-states until first IN A,($FE)
        65,   # 65 T-states per loop iteration
        10,   # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'palas': Accelerator(
        'palas',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xAF,       #           XOR A          [4]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xB7,       #           OR A           [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF4, #           JR Z,LD_SAMPLE [12/7]
        ],
        13,   # 13 T-states until first IN A,($FE)
        55,   # 55 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'paul-owens': Accelerator(
        'paul-owens',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xC8,       #           RET Z          [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'raxoft': Accelerator(
        'raxoft',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xAF,       #           XOR A          [4]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0x00,       #           NOP            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF4  #           JR Z,LD_SAMPLE [12/7]
        ],
        13,   # 13 T-states until first IN A,($FE)
        55,   # 55 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'realtime': Accelerator(
        'realtime',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x00,       #           NOP            [4]
            0x00,       #           NOP            [4]
            0x00,       #           NOP            [4]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        21,   # 21 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        10,   # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'rom': Accelerator(
        'rom',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'search-loader': Accelerator(
        'search-loader',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x00, #           LD A,$00       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0xD8,       #           RET C          [11/5]
            0x00,       #           NOP            [4]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'silverbird': Accelerator(
        'silverbird',
        [
            0x04,             # LD_SAMPLE INC B          [4]
            0x28, None,       #           JR Z,nn        [12/7]
            0x3A, 0x00, 0x00, #           LD A,(0)       [13]
            0x7F,             #           LD A,A         [4]
            0xDB, 0xFE,       #           IN A,($FE)     [11]
            0xA9,             #           XOR C          [4]
            0xE6, 0x40,       #           AND $40        [7]
            0x28, 0xF2        #           JR Z,LD_SAMPLE [12/7]
        ],
        28,   # 28 T-states until first IN A,($FE)
        62,   # 62 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'sparklers': Accelerator(
        'sparklers',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xAF,       #           XOR A          [4]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0x00,       #           NOP            [4]
            0x00,       #           NOP            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        13,   # 13 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        10,   # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'speedlock': Accelerator(
        'speedlock',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF4  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        54,   # 54 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'suzy-soft': Accelerator(
        'suzy-soft',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0xFB, #           LD A,$FB       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'suzy-soft2': Accelerator(
        'suzy-soft2',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0xF7, #           LD A,$F7       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x1F,       #           RRA            [4]
            0xA9,       #           XOR C          [4]
            0xE6, 0x20, #           AND $20        [7]
            0x28, 0xF4  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        54,   # 54 T-states per loop iteration
        8,    # R register increment per loop iteration
        0x20  # EAR mask
    ),

    'tiny': Accelerator(
        'tiny',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF7  #           JR Z,LD_SAMPLE [12/7]
        ],
        9,    # 9 T-states until first IN A,($FE)
        43,   # 43 T-states per loop iteration
        6,    # R register increment per loop iteration
        0x40  # EAR mask
    ),

    'weird-science': Accelerator(
        'weird-science',
        [
            0x04,       # LD_SAMPLE INC B          [4]
            0xC8,       #           RET Z          [11/5]
            0x3E, 0x7F, #           LD A,$7F       [7]
            0xDB, 0xFE, #           IN A,($FE)     [11]
            0x37,       #           SCF            [4]
            0xD0,       #           RET NC         [11/5]
            0xA9,       #           XOR C          [4]
            0xE6, 0x40, #           AND $40        [7]
            0x28, 0xF3  #           JR Z,LD_SAMPLE [12/7]
        ],
        16,   # 16 T-states until first IN A,($FE)
        59,   # 59 T-states per loop iteration
        9,    # R register increment per loop iteration
        0x40  # EAR mask
    ),
}

ACCELERATORS['cyberlode'] = ACCELERATORS['bleepload']
ACCELERATORS['edge'] = ACCELERATORS['rom']
ACCELERATORS['elite-uni-loader'] = ACCELERATORS['speedlock']
ACCELERATORS['excelerator'] = ACCELERATORS['bleepload']
ACCELERATORS['flash-loader'] = ACCELERATORS['rom']
ACCELERATORS['ftl'] = ACCELERATORS['speedlock']
ACCELERATORS['gargoyle'] = ACCELERATORS['speedlock']
ACCELERATORS['hewson-slowload'] = ACCELERATORS['rom']
ACCELERATORS['injectaload'] = ACCELERATORS['bleepload']
ACCELERATORS['poliload'] = ACCELERATORS['dinaload']
ACCELERATORS['power-load'] = ACCELERATORS['bleepload']
ACCELERATORS['softlock'] = ACCELERATORS['rom']
ACCELERATORS['zydroload'] = ACCELERATORS['speedlock']
