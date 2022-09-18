#!/usr/bin/env python3

import sys
import os
import unittest

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, f'{SKOOLKIT_HOME}')

from skoolkit.simulator import Simulator
from sim_test_tracers import *

REGISTERS = ('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')

ADD_A_r = '94d11617ef16363974532987b3d6435d'
ADD_A_A = 'b3255524a4f4496f91b72b9487e1c2f2'
ADC_A_r = '2f66412d4427588cce4ad21a6a1f80e8'
ADC_A_A = '215c4452e0a3029867ab60783fe9ce53'
SUB_r = 'fe66eed24306aef98870ab5d36b2e4f4'
SUB_A = 'd4665ee7436c8cdb18ac88d71ce1f745'
SBC_A_r = 'e73292a348f82706587d3adafb2f2bcc'
SBC_A_A = 'e4e7d5586ece48f9c8625f5c9cc2d17a'
AND_r = '6a2b0f982cad3d012db6924b5801a167'
AND_A = '153af0c2fb5636aeb7e887ff3a04d9da'
XOR_r = 'cf1542da7149725f83eba3bc0709be0b'
XOR_A = 'eb543679f6a2a9f3a2afcf22163be7f2'
OR_r = 'a9070d2d8bd3ff554c8e406096dc2bd7'
OR_A = 'a64900a4e9443713cfced1cc9e608c44'
CP_r = '6417db6acd2d6e2bdd0ba27115b4e158'
CP_A = '1fab032e90e72158e53eb5363ab99f9a'
DAA = '4312f5a5e95c582dbee61b482eee9d6b'

class SimulatorFlagsTest(unittest.TestCase):
    def _test_instruction(self, op, tclass, targs, checksum, opcodes, snapshot=None):
        start = 32768
        if snapshot is None:
            snapshot = [0] * 65536
        if isinstance(opcodes, int):
            snapshot[start] = opcodes
        else:
            snapshot[start:start + len(opcodes)] = opcodes
        tracer = tclass(start, *targs)
        simulator = Simulator(snapshot, {'HL': 16384, 'IX': 16385, 'IY': 16386})
        simulator.set_tracer(tracer)
        simulator.run(start)
        reg = targs[0] if targs else ''
        self.assertEqual(tracer.checksum, checksum, f"Checksum failure for '{op}{reg}'")

    def _test_alo(self, op, checksum, opcode):
        snapshot = [0] * 65536

        for i, reg in enumerate(('B', 'C', 'D', 'E', 'H', 'L', '(HL)')):
            self._test_instruction(op, AFRTracer, (reg,), checksum, opcode + i, snapshot)

        self._test_instruction(op, AFRTracer, ('n',), checksum, opcode + 0x46, snapshot)

        self._test_instruction(op, AFRTracer, ('IXh',), checksum, (0xDD, opcode + 0x04), snapshot)
        self._test_instruction(op, AFRTracer, ('IYh',), checksum, (0xFD, opcode + 0x04), snapshot)

        self._test_instruction(op, AFRTracer, ('IXl',), checksum, (0xDD, opcode + 0x05), snapshot)
        self._test_instruction(op, AFRTracer, ('IYl',), checksum, (0xFD, opcode + 0x05), snapshot)

        self._test_instruction(op, AFRTracer, ('(IX+d)',), checksum, (0xDD, opcode + 0x06), snapshot)
        self._test_instruction(op, AFRTracer, ('(IY+d)',), checksum, (0xFD, opcode + 0x06), snapshot)

    def test_add_a_r(self):
        self._test_alo('ADD A,', ADD_A_r, 0x80)

    def test_add_a_a(self):
        self._test_instruction('ADD A,A', AFTracer, (), ADD_A_A, 0x87)

    def test_adc_a_r(self):
        self._test_alo('ADC A,', ADC_A_r, 0x88)

    def test_adc_a_a(self):
        self._test_instruction('ADC A,A', AFTracer, (), ADC_A_A, 0x8F)

    def test_sub_r(self):
        self._test_alo('SUB ', SUB_r, 0x90)

    def test_sub_a(self):
        self._test_instruction('SUB A', AFTracer, (), SUB_A, 0x97)

    def test_sbc_a_r(self):
        self._test_alo('SBC A,', SBC_A_r, 0x98)

    def test_sbc_a_a(self):
        self._test_instruction('SBC A,A', AFTracer, (), SBC_A_A, 0x9F)

    def test_and_r(self):
        self._test_alo('AND ', AND_r, 0xA0)

    def test_and_a(self):
        self._test_instruction('AND A', AFTracer, (), AND_A, 0xA7)

    def test_xor_r(self):
        self._test_alo('XOR ', XOR_r, 0xA8)

    def test_xor_a(self):
        self._test_instruction('XOR A', AFTracer, (), XOR_A, 0xAF)

    def test_or_r(self):
        self._test_alo('OR ', OR_r, 0xB0)

    def test_or_a(self):
        self._test_instruction('OR A', AFTracer, (), OR_A, 0xB7)

    def test_cp_r(self):
        self._test_alo('CP ', CP_r, 0xB8)

    def test_cp_a(self):
        self._test_instruction('CP A', AFTracer, (), CP_A, 0xBF)

    def test_daa(self):
        self._test_instruction('DAA', DAATracer, (), DAA, 0x27)

if __name__ == '__main__':
    unittest.main()