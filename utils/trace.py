#!/usr/bin/env python3

import argparse
import os
import sys
import time

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, SKOOLKIT_HOME)

from skoolkit import SkoolKitError, get_int_param, integer, read_bin_file
from skoolkit.snapshot import make_snapshot, print_reg_help
from skoolkit.simulator import Simulator

TRACE1 = "{i.time:>9}  {bytes:<8} ${i.address:04X} {i.operation:<16}  [{i.tstates:>2}]"
TRACE2 = TRACE1 + "  A={A:02X} F={F:08b} BC={BC:04X} DE={DE:04X} HL={HL:04X} A'={^A:02X} F'={^F:08b} BC'={BC':04X} DE'={DE':04X} HL'={HL':04X} SP={SP:04X}"

class Tracer:
    def __init__(self, verbose, end=-1, max_operations=0, max_tstates=0):
        self.verbose = verbose
        self.end = end
        self.max_operations = max_operations
        self.max_tstates = max_tstates
        self.operations = 0
        self.spkr = None
        self.out_times = []

    def trace(self, simulator, instruction):
        if self.verbose:
            if self.verbose > 1:
                fmt = TRACE2
            else:
                fmt = TRACE1
            bvals = ''.join(f'{b:02X}' for b in instruction.data)
            registers = simulator.registers.copy()
            registers.update({
                "BC": registers['C'] + 256 * registers['B'],
                "DE": registers['E'] + 256 * registers['D'],
                "HL": registers['L'] + 256 * registers['H'],
                "BC'": registers['^C'] + 256 * registers['^B'],
                "DE'": registers['^E'] + 256 * registers['^D'],
                "HL'": registers['^L'] + 256 * registers['^H']
            })
            print(fmt.format(i=instruction, bytes=bvals, **registers))

        self.operations += 1

        addr = f'${instruction.address:04X}'
        if self.operations >= self.max_operations > 0:
            print(f'Stopped at {addr}: {self.operations} operations')
            return True
        if simulator.tstates >= self.max_tstates > 0:
            print(f'Stopped at {addr}: {simulator.time} T-states')
            return True
        if simulator.pc == self.end:
            print(f'Stopped at {addr}')
            return True
        if simulator.ppcount < 0 and self.max_operations <= 0 and self.max_tstates <= 0 and self.end < 0:
            print(f'Stopped at {addr}: PUSH-POP count is {simulator.ppcount}')
            return True

    def read_port(self, simulator, port):
        return 0xFF

    def write_port(self, simulator, port, value):
        if port & 0xFF == 0xFE and self.spkr is None or self.spkr != value & 0x10:
            self.spkr = value & 0x10
            self.out_times.append(simulator.tstates)

    def read_memory(self, simulator, address, count):
        pass

    def write_memory(self, simulator, address, values):
        pass

def get_registers(specs):
    registers = {}
    for spec in specs:
        reg, sep, val = spec.upper().partition('=')
        if sep:
            try:
                registers[reg] = get_int_param(val, True)
            except ValueError:
                raise SkoolKitError("Cannot parse register value: {}".format(spec))
    return registers

def rle(s, length):
    prev = s[:length]
    s2 = []
    count = 1
    i = length
    while i < len(s):
        prev_s = ', '.join(prev)
        if i + length - 1 < len(s):
            if prev == s[i:i + length]:
                count += 1
            else:
                if count > 1:
                    s2.append(f'[{prev_s}]*{count}')
                else:
                    s2.extend(prev)
                prev = s[i:i + length]
                count = 1
        else:
            if count > 1:
                s2.append(f'[{prev_s}]*{count}')
            else:
                s2.extend(prev)
            s2.extend(s[i:])
            count = 0
        i += length
    if count > 1:
        s2.append('[{}]*{}'.format(','.join(prev), count))
    elif count == 1:
        s2.extend(prev)
    return s2

def simplify(delays, depth):
    s0 = [str(d) for d in delays]
    if s0 and depth > 0:
        length = 1
        while length <= depth:
            s1 = rle(s0, length)
            if s1 == s0:
                break
            if length > 1:
                while 1:
                    s0 = s1
                    s1 = rle(s1, length)
                    if s1 == s0:
                        break
            s0 = s1
            length += 1
    return ', '.join(s0)

def run(snafile, start, options):
    snapshot, start = make_snapshot(snafile, options.org, start)[0:2]
    if options.rom:
        rom = read_bin_file(options.rom, 16384)
        snapshot[:len(rom)] = rom
    simulator = Simulator(snapshot, get_registers(options.reg))
    tracer = Tracer(options.verbose, options.end, options.max_operations, options.max_tstates)
    simulator.set_tracer(tracer)
    begin = time.time()
    simulator.run(start)
    rt = time.time() - begin
    if options.stats:
        z80t = simulator.tstates / 3500000
        speed = z80t / rt
        print(f'Z80 execution time: {simulator.tstates} T-states ({z80t:.03f}s)')
        print(f'Instructions executed: {tracer.operations}')
        print(f'Emulation time: {rt:.03f}s (x{speed:.02f})')
    if options.audio:
        delays = []
        for i, t in enumerate(tracer.out_times[1:]):
            delays.append(t - tracer.out_times[i])
        duration = sum(delays)
        print('Sound duration: {} T-states ({:.03f}s)'.format(duration, duration / 3500000))
        print('Delays: {}'.format(simplify(delays, options.depth)))
    if options.dump:
        with open(options.dump, 'wb') as f:
            f.write(bytearray(simulator.snapshot[16384:]))
        print(f'Snapshot dumped to {options.dump}')

def main(args):
    parser = argparse.ArgumentParser(
        usage='trace.py [options] FILE START',
        description="Trace Z80 machine code execution. "
                    "FILE may be a binary (raw memory) file, or a SNA, SZX or Z80 snapshot.",
        add_help=False
    )
    parser.add_argument('snafile', help=argparse.SUPPRESS, nargs='?')
    parser.add_argument('start', type=integer, help=argparse.SUPPRESS, nargs='?')
    group = parser.add_argument_group('Options')
    group.add_argument('--audio', action='store_true',
                       help="Show audio delays.")
    group.add_argument('--depth', type=int, default=2,
                       help='Simplify audio delays to this depth (default: 2).')
    group.add_argument('--dump', metavar='FILE',
                       help='Dump snapshot to this file after execution.')
    group.add_argument('-e', '--end', metavar='ADDR', type=integer, default=-1,
                       help='End execution at this address.')
    group.add_argument('--max-operations', metavar='MAX', type=int, default=0,
                       help='Maximum number of instructions to execute.')
    group.add_argument('--max-tstates', metavar='MAX', type=int, default=0,
                       help='Maximum number of T-states to run for.')
    group.add_argument('-o', '--org', dest='org', metavar='ADDR', type=integer,
                       help='Specify the origin address of a binary (.bin) file (default: 65536 - length).')
    group.add_argument('--reg', metavar='name=value', action='append', default=[],
                       help="Set the value of a register. Do '--reg help' for more information. "
                            "This option may be used multiple times.")
    group.add_argument('--rom', metavar='FILE',
                       help='Patch in a ROM at address 0 from this file.')
    group.add_argument('--stats', action='store_true',
                       help="Show stats after execution.")
    group.add_argument('-v', '--verbose', action='count', default=0,
                       help="Show executed instructions. Repeat this option to show register values too.")
    namespace, unknown_args = parser.parse_known_args(args)
    if 'help' in namespace.reg:
        print_reg_help()
        sys.exit(0)
    if unknown_args or namespace.start is None:
        parser.exit(2, parser.format_help())
    run(namespace.snafile, namespace.start, namespace)

if __name__ == '__main__':
    main(sys.argv[1:])