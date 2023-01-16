import os
import textwrap
import urllib
from zipfile import ZipFile
from io import BytesIO
from unittest.mock import patch, Mock

from skoolkittest import (SkoolKitTestCase, Z80_REGISTERS, create_data_block,
                          create_tap_header_block, create_tap_data_block,
                          create_tzx_header_block, create_tzx_data_block)
from skoolkit import tap2sna, VERSION, SkoolKitError
from skoolkit.snapshot import get_snapshot

def mock_make_z80(*args):
    global make_z80_args
    make_z80_args = args

def mock_write_z80(ram, namespace, z80):
    global snapshot, options
    snapshot = [0] * 16384 + ram
    options = namespace

class Tap2SnaTest(SkoolKitTestCase):
    def _write_tap(self, blocks, zip_archive=False, tap_name=None):
        tap_data = []
        for block in blocks:
            tap_data.extend(block)
        if zip_archive:
            archive_fname = self.write_bin_file(suffix='.zip')
            with ZipFile(archive_fname, 'w') as archive:
                archive.writestr(tap_name or 'game.tap', bytearray(tap_data))
            return archive_fname
        return self.write_bin_file(tap_data, suffix='.tap')

    def _write_tzx(self, blocks):
        tzx_data = [ord(c) for c in "ZXTape!"]
        tzx_data.extend((26, 1, 20))
        for block in blocks:
            tzx_data.extend(block)
        return self.write_bin_file(tzx_data, suffix='.tzx')

    def _write_basic_loader(self, start, data, write=True, program='simloadbas', code='simloadbyt'):
        start_str = [ord(c) for c in str(start)]
        basic_data = [
            0, 10,            # Line 10
            16, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *start_str,       # start address
            34,               # "
            13                # ENTER
        ]
        blocks = [
            create_tap_header_block(program, 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block(code, start, len(data)),
            create_tap_data_block(data)
        ]
        if write:
            return self._write_tap(blocks), basic_data
        return blocks, basic_data

    def _get_snapshot(self, start=16384, data=None, options='', load_options=None, blocks=None, tzx=False):
        if blocks is None:
            blocks = [create_tap_data_block(data)]
        if tzx:
            tape_file = self._write_tzx(blocks)
        else:
            tape_file = self._write_tap(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        if load_options is None:
            load_options = '--ram load=1,{}'.format(start)
        output, error = self.run_tap2sna('--force {} {} {} {}'.format(load_options, options, tape_file, z80file))
        self.assertEqual(output, 'Writing {}\n'.format(z80file))
        self.assertEqual(error, '')
        return get_snapshot(z80file)

    def _test_bad_spec(self, option, exp_error):
        odir = self.make_directory()
        tapfile = self._write_tap([create_tap_data_block([1])])
        z80fname = 'test.z80'
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('--ram load=1,16384 {} -d {} {} {}'.format(option, odir, tapfile, z80fname))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: {}'.format(z80fname, exp_error))

    @patch.object(tap2sna, 'make_z80', mock_make_z80)
    def test_default_option_values(self):
        self.run_tap2sna('in.tap {}/out.z80'.format(self.make_directory()))
        options = make_z80_args[1]
        self.assertIsNone(options.output_dir)
        self.assertFalse(options.force)
        self.assertIsNone(options.stack)
        self.assertEqual([], options.ram_ops)
        self.assertEqual([], options.reg)
        self.assertIsNone(options.start)
        self.assertFalse(options.sim_load)
        self.assertEqual([], options.state)
        self.assertEqual(options.user_agent, '')

    def test_no_arguments(self):
        output, error = self.run_tap2sna(catch_exit=2)
        self.assertEqual(output, '')
        self.assertTrue(error.startswith('usage:'))

    def test_invalid_arguments(self):
        for args in ('--foo', '-k test.zip'):
            output, error = self.run_tap2sna(args, catch_exit=2)
            self.assertEqual(output, '')
            self.assertTrue(error.startswith('usage:'))

    def test_accelerator_help(self):
        output, error = self.run_tap2sna('--accelerator help')
        self.assertTrue(output.startswith('Usage: --accelerator NAME\n'))
        self.assertEqual(error, '')

    def test_accelerator_unrecognised(self):
        blocks = [create_tap_data_block([0])]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna(f'--accelerator nope --sim-load {tapfile} {z80file}')
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot out.z80: Unrecognised accelerator: nope')
        self.assertEqual(self.err.getvalue(), '')

    def test_option_d(self):
        odir = '{}/tap2sna'.format(self.make_directory())
        tapfile = self._write_tap((
            create_tap_header_block(start=16384),
            create_tap_data_block([0])
        ))
        z80_fname = 'test.z80'
        for option in ('-d', '--output-dir'):
            output, error = self.run_tap2sna('{} {} {} {}'.format(option, odir, tapfile, z80_fname))
            self.assertEqual(len(error), 0)
            self.assertTrue(os.path.isfile(os.path.join(odir, z80_fname)))

    @patch.object(tap2sna, 'make_z80', mock_make_z80)
    def test_options_p_stack(self):
        for option, stack in (('-p', 24576), ('--stack', 49152)):
            output, error = self.run_tap2sna('{} {} in.tap {}/out.z80'.format(option, stack, self.make_directory()))
            self.assertEqual(output, '')
            self.assertEqual(error, '')
            url, options, z80 = make_z80_args
            self.assertEqual(['sp={}'.format(stack)], options.reg)

    @patch.object(tap2sna, 'make_z80', mock_make_z80)
    def test_options_p_stack_with_hex_address(self):
        for option, stack in (('-p', '0x6ff0'), ('--stack', '0x9ABC')):
            output, error = self.run_tap2sna('{} {} in.tap {}/out.z80'.format(option, stack, self.make_directory()))
            self.assertEqual(output, '')
            self.assertEqual(error, '')
            url, options, z80 = make_z80_args
            self.assertEqual(['sp={}'.format(int(stack[2:], 16))], options.reg)

    def test_option_p(self):
        tapfile = self._write_tap((
            create_tap_header_block(start=16384),
            create_tap_data_block([0])
        ))
        z80file = self.write_bin_file(suffix='.z80')
        stack = 32768

        output, error = self.run_tap2sna('-f -p {} {} {}'.format(stack, tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(10)
        self.assertEqual(z80_header[8] + 256 * z80_header[9], stack)

    @patch.object(tap2sna, 'make_z80', mock_make_z80)
    def test_options_s_start(self):
        start = 30000
        exp_reg = ['pc={}'.format(start)]
        for option in ('-s', '--start'):
            output, error = self.run_tap2sna('{} {} in.tap {}/out.z80'.format(option, start, self.make_directory()))
            self.assertEqual(output, '')
            self.assertEqual(error, '')
            url, options, z80 = make_z80_args
            self.assertEqual(exp_reg, options.reg)

    @patch.object(tap2sna, 'make_z80', mock_make_z80)
    def test_options_s_start_with_hex_address(self):
        start = 30000
        exp_reg = ['pc={}'.format(start)]
        for option in ('-s', '--start'):
            output, error = self.run_tap2sna('{} 0x{:04X} in.tap {}/out.z80'.format(option, start, self.make_directory()))
            self.assertEqual(output, '')
            self.assertEqual(error, '')
            url, options, z80 = make_z80_args
            self.assertEqual(exp_reg, options.reg)

    def test_option_s(self):
        tapfile = self._write_tap((
            create_tap_header_block(start=16384),
            create_tap_data_block([0])
        ))
        z80file = self.write_bin_file(suffix='.z80')
        start = 40000

        output, error = self.run_tap2sna('-f -s {} {} {}'.format(start, tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(34)
        self.assertEqual(z80_header[32] + 256 * z80_header[33], start)

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    @patch.object(tap2sna, 'urlopen')
    def test_option_u(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(bytes(create_tap_data_block([1])))
        url = 'http://example.com/test.tap'
        for option, user_agent in (('-u', 'Wget/1.18'), ('--user-agent', 'SkoolKit/6.3')):
            output, error = self.run_tap2sna('{} {} --ram load=1,23296 {} {}/test.z80'.format(option, user_agent, url, self.make_directory()))
            self.assertTrue(output.startswith('Downloading {}\n'.format(url)))
            self.assertEqual(error, '')
            request = mock_urlopen.call_args[0][0]
            self.assertEqual({'User-agent': user_agent}, request.headers)
            self.assertEqual(snapshot[23296], 1)
            mock_urlopen.return_value.seek(0)

    def test_option_V(self):
        for option in ('-V', '--version'):
            output, error = self.run_tap2sna(option, catch_exit=0)
            self.assertEqual(output, 'SkoolKit {}\n'.format(VERSION))

    def test_nonexistent_tap_file(self):
        odir = self.make_directory()
        tap_fname = '{}/test.tap'.format(odir)
        z80_fname = 'test.z80'
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('{} {}/{}'.format(tap_fname, odir, z80_fname))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: {}: file not found'.format(z80_fname, tap_fname))

    def test_load_nonexistent_block(self):
        tapfile = self._write_tap([create_tap_data_block([1])])
        block_num = 2
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('--ram load={},16384 {} {}/test.z80'.format(block_num, tapfile, self.make_directory()))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot test.z80: Block {} not found'.format(block_num))

    def test_zip_archive_with_no_tape_file(self):
        archive_fname = self.write_bin_file(suffix='.zip')
        with ZipFile(archive_fname, 'w') as archive:
            archive.writestr('game.txt', bytearray((1, 2)))
        z80_fname = 'test.z80'
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('{} {}/{}'.format(archive_fname, self.make_directory(), z80_fname))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: No TAP or TZX file found'.format(z80_fname))

    def test_standard_load_from_tap_file(self):
        basic_data = [1, 2, 3]
        code_start = 32768
        code = [4, 5]
        blocks = [
            create_tap_header_block(data_type=0),
            create_tap_data_block(basic_data),
            create_tap_header_block(start=code_start),
            create_tap_data_block(code)
        ]

        tapfile = self._write_tap(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force {} {}'.format(tapfile, z80file))
        self.assertEqual(error, '')
        snapshot = get_snapshot(z80file)
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])

    def test_standard_load_ignores_headerless_block(self):
        code_start = 16384
        code = [2]
        blocks = [
            create_tap_header_block(start=code_start),
            create_tap_data_block(code),
            create_tap_data_block([23]),
            create_tap_data_block([97])
        ]

        tapfile = self._write_tap(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force {} {}'.format(tapfile, z80file))
        self.assertEqual(
            error,
            'WARNING: Ignoring headerless block 3\n'
            'WARNING: Ignoring headerless block 4\n'
        )
        snapshot = get_snapshot(z80file)
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])

    def test_standard_load_ignores_truncated_header_block(self):
        code_start = 30000
        code = [2, 3, 4]
        length = len(code)
        blocks = [
            create_tap_header_block(start=code_start)[:-1],
            create_tap_data_block(code),
        ]

        tapfile = self._write_tap(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force {} {}'.format(tapfile, z80file))
        self.assertEqual(error, '')
        snapshot = get_snapshot(z80file)
        self.assertEqual([0] * length, snapshot[code_start:code_start + length])

    def test_standard_load_with_unknown_block_type(self):
        block_type = 1 # Array of numbers
        blocks = [
            create_tap_header_block(data_type=block_type),
            create_tap_data_block([1])
        ]

        tapfile = self._write_tap(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('--force {} {}'.format(tapfile, z80file))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: Unknown block type ({}) in header block 1'.format(z80file, block_type))

    def test_standard_load_from_tzx_file(self):
        basic_data = [6, 7]
        code_start = 49152
        code = [8, 9, 10]
        blocks = [
            [48, 3, 65, 66, 67], # Text description block (0x30): ABC
            create_tzx_header_block(data_type=0),
            create_tzx_data_block(basic_data),
            create_tzx_header_block(start=code_start),
            create_tzx_data_block(code)
        ]

        tzxfile = self._write_tzx(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force {} {}'.format(tzxfile, z80file))
        self.assertEqual(error, '')
        snapshot = get_snapshot(z80file)
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])

    def test_empty_standard_speed_data_block_in_tzx_file_is_ignored(self):
        basic_data = [6, 7]
        code_start = 49152
        code = [8, 9, 10]
        empty_block = [
            16,   # Standard speed data
            0, 0, # Pause (0ms)
            0, 0, # Data length (0)
        ]
        blocks = [
            create_tzx_header_block(data_type=0),
            create_tzx_data_block(basic_data),
            empty_block,
            create_tzx_header_block(start=code_start),
            create_tzx_data_block(code)
        ]

        tzxfile = self._write_tzx(blocks)
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force {} {}'.format(tzxfile, z80file))
        self.assertEqual(error, '')
        snapshot = get_snapshot(z80file)
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])

    def test_ram_call(self):
        ram_module = """
            def fix(snapshot):
                snapshot[65280:] = list(range(256))
        """
        module_dir = self.make_directory()
        module_path = os.path.join(module_dir, 'ram.py')
        module = self.write_text_file(textwrap.dedent(ram_module).strip(), path=module_path)
        blocks = [
            create_tap_header_block(start=16384),
            create_tap_data_block([0])
        ]
        snapshot = self._get_snapshot(load_options=f'--ram call={module_dir}:ram.fix', blocks=blocks)
        self.assertEqual(list(range(256)), snapshot[65280:])

    def test_ram_call_nonexistent_module(self):
        self._test_bad_spec('--ram call=no:nope.never', "Failed to import object nope.never: No module named 'nope'")

    def test_ram_call_nonexistent_function(self):
        module_dir = self.make_directory()
        module_path = os.path.join(module_dir, 'ram.py')
        module = self.write_text_file(path=module_path)
        self._test_bad_spec(f'--ram call={module_dir}:ram.never', "No object named 'never' in module 'ram'")

    def test_ram_call_uncallable(self):
        ram_module = "fix = None"
        module_dir = self.make_directory()
        module_path = os.path.join(module_dir, 'uncallable.py')
        module = self.write_text_file(ram_module, path=module_path)
        self._test_bad_spec(f'--ram call={module_dir}:uncallable.fix', "'NoneType' object is not callable")

    def test_ram_call_function_with_no_arguments(self):
        ram_module = "def fix(): pass"
        module_dir = self.make_directory()
        module_path = os.path.join(module_dir, 'noargs.py')
        module = self.write_text_file(ram_module, path=module_path)
        self._test_bad_spec(f'--ram call={module_dir}:noargs.fix', "fix() takes 0 positional arguments but 1 was given")

    def test_ram_call_function_with_two_positional_arguments(self):
        ram_module = "def fix(snapshot, what): pass"
        module_dir = self.make_directory()
        module_path = os.path.join(module_dir, 'twoargs.py')
        module = self.write_text_file(ram_module, path=module_path)
        self._test_bad_spec(f'--ram call={module_dir}:twoargs.fix', "fix() missing 1 required positional argument: 'what'")

    def test_ram_load(self):
        start = 16384
        data = [237, 1, 1, 1, 1, 1]
        snapshot = self._get_snapshot(start, data)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_ram_load_with_length(self):
        start = 16384
        data = [1, 2, 3, 4]
        length = 2
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,{},{}'.format(start, length))
        self.assertEqual(data[:length], snapshot[start:start + length])
        self.assertEqual([0] * (len(data) - length), snapshot[start + length:start + len(data)])

    def test_ram_load_with_step(self):
        start = 16385
        data = [5, 4, 3]
        step = 2
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,{},,{}'.format(start, step))
        self.assertEqual(data, snapshot[start:start + len(data) * step:step])

    def test_ram_load_with_offset(self):
        start = 16384
        data = [15, 16, 17]
        offset = 5
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,{},,,{}'.format(start, offset))
        self.assertEqual(data, snapshot[start + offset:start + offset + len(data)])

    def test_ram_load_with_increment(self):
        start = 65534
        data = [8, 9, 10]
        inc = 65533
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,{},,,,{}'.format(start, inc))
        self.assertEqual([data[2]] + data[:2], snapshot[65533:])

    def test_ram_load_wraparound_with_step(self):
        start = 65535
        data = [23, 24, 25]
        step = 8193
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,{},,{}'.format(start, step))
        self.assertEqual(snapshot[start], data[0])
        self.assertEqual(snapshot[(start + 2 * step) & 65535], data[2])

    def test_ram_load_with_hexadecimal_parameters(self):
        start = 30000
        data = [1, 2, 3]
        step = 2
        offset = 3
        inc = 0
        snapshot = self._get_snapshot(start, data, load_options='--ram load=1,0x{:04x},0x{:04x},0x{:04x},0x{:04x},0x{:04x}'.format(start, len(data), step, offset, inc))
        self.assertEqual(data, snapshot[30003:30008:2])

    def test_ram_load_bad_address(self):
        self._test_bad_spec('--ram load=1,abcde', 'Invalid integer in load spec: 1,abcde')

    def test_ram_poke_single_address(self):
        start = 16384
        data = [4, 5, 6]
        poke_addr = 16386
        poke_val = 255
        snapshot = self._get_snapshot(start, data, '--ram poke={},{}'.format(poke_addr, poke_val))
        self.assertEqual(data[:2], snapshot[start:start + 2])
        self.assertEqual(snapshot[poke_addr], poke_val)

    def test_ram_poke_address_range(self):
        start = 16384
        data = [1, 1, 1]
        poke_addr_start = 16384
        poke_addr_end = 16383 + len(data)
        poke_val = 254
        snapshot = self._get_snapshot(start, data, '--ram poke={}-{},{}'.format(poke_addr_start, poke_addr_end, poke_val))
        self.assertEqual([poke_val] * len(data), snapshot[poke_addr_start:poke_addr_end + 1])

    def test_ram_poke_address_range_with_xor(self):
        start = 30000
        data = [1, 2, 3]
        end = start + len(data) - 1
        xor_val = 129
        snapshot = self._get_snapshot(start, data, '--ram poke={}-{},^{}'.format(start, end, xor_val))
        exp_data = [b ^ xor_val for b in data]
        self.assertEqual(exp_data, snapshot[start:end + 1])

    def test_ram_poke_address_range_with_add(self):
        start = 40000
        data = [100, 200, 32]
        end = start + len(data) - 1
        add_val = 130
        snapshot = self._get_snapshot(start, data, '--ram poke={}-{},+{}'.format(start, end, add_val))
        exp_data = [(b + add_val) & 255 for b in data]
        self.assertEqual(exp_data, snapshot[start:end + 1])

    def test_ram_poke_address_range_with_step(self):
        snapshot = self._get_snapshot(16384, [2, 9, 2], '--ram poke=16384-16386-2,253')
        self.assertEqual([253, 9, 253], snapshot[16384:16387])

    def test_ram_poke_hex_address(self):
        address, value = 16385, 253
        snapshot = self._get_snapshot(16384, [1], '--ram poke=${:X},{}'.format(address, value))
        self.assertEqual(snapshot[address], value)

    def test_ram_poke_0x_hex_values(self):
        snapshot = self._get_snapshot(16384, [2, 1, 2], '--ram poke=0x4000-0x4002-0x02,0x2a')
        self.assertEqual([42, 1, 42], snapshot[16384:16387])

    def test_ram_poke_bad_value(self):
        self._test_bad_spec('--ram poke=1', 'Value missing in poke spec: 1')
        self._test_bad_spec('--ram poke=q', 'Value missing in poke spec: q')
        self._test_bad_spec('--ram poke=1,x', 'Invalid value in poke spec: 1,x')
        self._test_bad_spec('--ram poke=x,1', 'Invalid address range in poke spec: x,1')
        self._test_bad_spec('--ram poke=1-y,1', 'Invalid address range in poke spec: 1-y,1')
        self._test_bad_spec('--ram poke=1-3-z,1', 'Invalid address range in poke spec: 1-3-z,1')

    def test_ram_move(self):
        start = 16384
        data = [5, 6, 7]
        src = start
        size = len(data)
        dest = 16387
        snapshot = self._get_snapshot(start, data, '--ram move={},{},{}'.format(src, size, dest))
        self.assertEqual(data, snapshot[start:start + len(data)])
        self.assertEqual(data, snapshot[dest:dest + len(data)])

    def test_ram_move_hex_address(self):
        src, size, dest = 16384, 1, 16385
        value = 3
        snapshot = self._get_snapshot(src, [value], '--ram move=${:X},{},${:x}'.format(src, size, dest))
        self.assertEqual(snapshot[dest], value)

    def test_ram_move_0x_hex_values(self):
        src, size, dest = 16385, 1, 16384
        value = 2
        snapshot = self._get_snapshot(src, [value], '--ram move=0x{:X},0x{:X},0x{:x}'.format(src, size, dest))
        self.assertEqual(snapshot[dest], value)

    def test_ram_move_bad_address(self):
        self._test_bad_spec('--ram move=1', 'Not enough arguments in move spec (expected 3): 1')
        self._test_bad_spec('--ram move=1,2', 'Not enough arguments in move spec (expected 3): 1,2')
        self._test_bad_spec('--ram move=x,2,3', 'Invalid integer in move spec: x,2,3')
        self._test_bad_spec('--ram move=1,y,3', 'Invalid integer in move spec: 1,y,3')
        self._test_bad_spec('--ram move=1,2,z', 'Invalid integer in move spec: 1,2,z')

    def test_ram_sysvars(self):
        snapshot = self._get_snapshot(23552, [0], '--ram sysvars')
        self.assertEqual(sum(snapshot[23552:23755]), 7911)
        self.assertEqual(len(snapshot), 65536)

    def test_ram_invalid_operation(self):
        self._test_bad_spec('--ram foo=bar', 'Invalid operation: foo=bar')

    def test_ram_help(self):
        output, error = self.run_tap2sna('--ram help')
        self.assertTrue(output.startswith('Usage: --ram call=[/path/to/moduledir:]module.function\n'))
        self.assertEqual(error, '')

    def test_tap_file_in_zip_archive(self):
        data = [1]
        block = create_tap_data_block(data)
        tap_name = 'game.tap'
        zip_fname = self._write_tap([block], zip_archive=True, tap_name=tap_name)
        z80file = self.write_bin_file(suffix='.z80')
        start = 16385
        output, error = self.run_tap2sna('--force --ram load=1,{} {} {}'.format(start, zip_fname, z80file))
        self.assertEqual(output, 'Extracting {}\nWriting {}\n'.format(tap_name, z80file))
        self.assertEqual(error, '')
        snapshot = get_snapshot(z80file)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_invalid_tzx_file(self):
        tzxfile = self.write_bin_file([1, 2, 3], suffix='.tzx')
        z80file = 'test.z80'
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('{} {}/{}'.format(tzxfile, self.make_directory(), z80file))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: Not a TZX file'.format(z80file))

    def test_tzx_block_type_0x10(self):
        data = [1, 2, 4]
        start = 16386
        block = create_tzx_data_block(data)
        snapshot = self._get_snapshot(start, blocks=[block], tzx=True)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_tzx_block_type_0x11(self):
        data = [2, 3, 5]
        block = [17] # Block ID
        block.extend([0] * 15)
        data_block = create_data_block(data)
        length = len(data_block)
        block.extend((length % 256, length // 256, 0))
        block.extend(data_block)
        start = 16387
        snapshot = self._get_snapshot(start, blocks=[block], tzx=True)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_tzx_block_type_0x14(self):
        data = [7, 11, 13]
        block = [20] # Block ID
        block.extend([0] * 7)
        data_block = create_data_block(data)
        length = len(data_block)
        block.extend((length % 256, length // 256, 0))
        block.extend(data_block)
        start = 16388
        snapshot = self._get_snapshot(start, blocks=[block], tzx=True)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_load_first_byte_of_block(self):
        data = [1, 2, 3, 4, 5]
        block = [20] # Block ID
        block.extend([0] * 7)
        length = len(data)
        block.extend((length % 256, length // 256, 0))
        block.extend(data)
        start = 16389
        load_options = '--ram load=+1,{}'.format(start)
        snapshot = self._get_snapshot(load_options=load_options, blocks=[block], tzx=True)
        exp_data = data[:-1]
        self.assertEqual(exp_data, snapshot[start:start + len(exp_data)])

    def test_load_last_byte_of_block(self):
        data = [1, 2, 3, 4, 5]
        block = [20] # Block ID
        block.extend([0] * 7)
        length = len(data)
        block.extend((length % 256, length // 256, 0))
        block.extend(data)
        start = 16390
        load_options = '--ram load=1+,{}'.format(start)
        snapshot = self._get_snapshot(load_options=load_options, blocks=[block], tzx=True)
        exp_data = data[1:]
        self.assertEqual(exp_data, snapshot[start:start + len(exp_data)])

    def test_load_first_and_last_bytes_of_block(self):
        data = [1, 2, 3, 4, 5]
        block = [20] # Block ID
        block.extend([0] * 7)
        length = len(data)
        block.extend((length % 256, length // 256, 0))
        block.extend(data)
        start = 16391
        load_options = '--ram load=+1+,{}'.format(start)
        snapshot = self._get_snapshot(load_options=load_options, blocks=[block], tzx=True)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_tzx_with_unsupported_blocks(self):
        blocks = []
        blocks.append((18, 0, 0, 0, 0)) # 0x12 Pure Tone
        blocks.append((19, 2, 0, 0, 0, 0)) # 0x13 Pulse sequence
        blocks.append([21] + [0] * 5 + [1, 0, 0, 0]) # 0x15 Direct Recording
        blocks.append([24, 11] + [0] * 14) # 0x18 CSW Recording
        blocks.append([25, 20] + [0] * 23) # 0x19 Generalized Data Block
        blocks.append((32, 0, 0)) # 0x20 Pause (silence) or 'Stop the Tape' command
        blocks.append((33, 1, 32)) # 0x21 Group start
        blocks.append((34,)) # 0x22 - Group end
        blocks.append((35, 0, 0)) # 0x23 Jump to block
        blocks.append((36, 2, 0)) # 0x24 Loop start
        blocks.append((37,)) # 0x25 Loop end
        blocks.append((38, 1, 0, 0, 0)) # 0x26 Call sequence
        blocks.append((39,)) # 0x27 Return from sequence
        blocks.append((40, 5, 0, 1, 0, 0, 1, 32)) # 0x28 Select block
        blocks.append((42, 0, 0, 0, 0)) # 0x2A Stop the tape if in 48K mode
        blocks.append((43, 1, 0, 0, 0, 1)) # 0x2B Set signal level
        blocks.append((48, 1, 65)) # 0x30 Text description
        blocks.append((49, 0, 1, 66)) # 0x31 Message block
        blocks.append((50, 4, 0, 1, 0, 1, 33)) # 0x32 Archive info
        blocks.append((51, 1, 0, 0, 0)) # 0x33 Hardware type
        blocks.append([53] + [32] * 16 + [1] + [0] * 4) # 0x35 Custom info block
        blocks.append([90] + [0] * 9) # 0x5A "Glue" block
        data = [2, 4, 6]
        blocks.append(create_tzx_data_block(data))
        start = 16388
        load_options = '--ram load={},{}'.format(len(blocks), start)
        snapshot = self._get_snapshot(load_options=load_options, blocks=blocks, tzx=True)
        self.assertEqual(data, snapshot[start:start + len(data)])

    def test_tzx_with_unknown_block(self):
        block_id = 22
        block = [block_id, 0]
        tzxfile = self._write_tzx([block])
        z80file = 'test.z80'
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna('{} {}/{}'.format(tzxfile, self.make_directory(), z80file))
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot {}: Unknown TZX block ID: 0x{:X}'.format(z80file, block_id))

    def test_default_register_values(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        exp_reg_values = {
            'a': 0, 'f': 0, 'bc': 0, 'de': 0, 'hl': 0, 'i': 63, 'r': 0,
            '^bc': 0, '^de': 0, '^hl': 0, 'ix': 0, 'iy': 23610, 'sp': 0, 'pc': 0
        }

        output, error = self.run_tap2sna('--force --ram load=1,16384 {} {}'.format(tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(34)
        for reg, exp_value in exp_reg_values.items():
            offset = Z80_REGISTERS[reg]
            size = len(reg) - 1 if reg.startswith('^') else len(reg)
            if size == 1:
                value = z80_header[offset]
            else:
                value = z80_header[offset] + 256 * z80_header[offset + 1]
            self.assertEqual(value, exp_value)

    def test_reg(self):
        block = create_tap_data_block([1])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        reg_dicts = (
            {'^a': 1, '^b': 2, '^c': 3, '^d': 4, '^e': 5, '^f': 6, '^h': 7, '^l': 8},
            {'a': 9, 'b': 10, 'c': 11, 'd': 12, 'e': 13, 'f': 14, 'h': 15, 'l': 16, 'r': 129},
            {'^bc': 258, '^de': 515, '^hl': 65534, 'bc': 259, 'de': 516, 'hl': 65533},
            {'i': 13, 'ix': 1027, 'iy': 1284, 'pc': 1541, 'r': 23, 'sp': 32769}
        )
        for reg_dict in reg_dicts:
            reg_options = ' '.join(['--reg {}={}'.format(r, v) for r, v in reg_dict.items()])
            output, error = self.run_tap2sna('--force --ram load=1,16384 {} {} {}'.format(reg_options, tapfile, z80file))
            self.assertEqual(error, '')
            with open(z80file, 'rb') as f:
                z80_header = f.read(34)
            for reg, exp_value in reg_dict.items():
                offset = Z80_REGISTERS[reg]
                size = len(reg) - 1 if reg.startswith('^') else len(reg)
                if size == 1:
                    value = z80_header[offset]
                else:
                    value = z80_header[offset] + 256 * z80_header[offset + 1]
                self.assertEqual(value, exp_value)
                if reg == 'r' and exp_value & 128:
                    self.assertEqual(z80_header[12] & 1, 1)

    def test_reg_hex_value(self):
        odir = self.make_directory()
        tapfile = self._write_tap([create_tap_data_block([1])])
        z80fname = 'test.z80'
        reg_value = 35487
        output, error = self.run_tap2sna('--ram load=1,16384 --reg bc=${:x} -d {} {} {}'.format(reg_value, odir, tapfile, z80fname))
        self.assertEqual(error, '')
        with open(os.path.join(odir, z80fname), 'rb') as f:
            z80_header = f.read(4)
        self.assertEqual(z80_header[2] + 256 * z80_header[3], reg_value)

    def test_reg_0x_hex_value(self):
        odir = self.make_directory()
        tapfile = self._write_tap([create_tap_data_block([1])])
        z80fname = 'test.z80'
        reg_value = 54873
        output, error = self.run_tap2sna('--ram load=1,16384 --reg hl=0x{:x} -d {} {} {}'.format(reg_value, odir, tapfile, z80fname))
        self.assertEqual(error, '')
        with open(os.path.join(odir, z80fname), 'rb') as f:
            z80_header = f.read(6)
        self.assertEqual(z80_header[4] + 256 * z80_header[5], reg_value)

    def test_reg_bad_value(self):
        self._test_bad_spec('--reg bc=A2', 'Cannot parse register value: bc=A2')

    def test_ram_invalid_register(self):
        self._test_bad_spec('--reg iz=1', 'Invalid register: iz=1')

    def test_reg_help(self):
        output, error = self.run_tap2sna('--reg help')
        self.assertTrue(output.startswith('Usage: --reg name=value\n'))
        self.assertEqual(error, '')

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load(self):
        code_start = 32768
        code = [4, 5]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_initial_code_block(self):
        code_start = 65360 # Overwrite return address on stack with...
        code = [128, 128]  # ...32896
        blocks = [
            create_tap_header_block("\xafblock", code_start, len(code)),
            create_tap_data_block(code)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Bytes: CODE block    ',
            'Fast loading data block: 65360,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32896',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65362', 'IX=65362', 'IY=23610', 'PC=32896'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_given_start_address(self):
        code_start = 32768
        start = 32769
        code = [175, 201]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load --start {start} {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC at start address): PC=32769',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32769'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_character_array(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            25, 0,            # Line length
            239, 34, 34, 228, # LOAD "" DATA
            97, 36, 40, 41,   # a$()
            58,               # :
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        ca_name = "characters"
        ca_data = [193, 5, 0, 1, 2, 0, 97, 98]
        code = [4, 5]
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block(ca_name, length=len(ca_data), data_type=2),
            create_tap_data_block(ca_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,29',
            'Character array: characters',
            'Fast loading data block: 23787,8',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(ca_data, snapshot[23787:23787 + len(ca_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_number_array(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            24, 0,            # Line length
            239, 34, 34, 228, # LOAD "" DATA
            97, 40, 41,       # a()
            58,               # :
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        na_name = "numbers"
        na_data = [129, 13, 0, 1, 2, 0, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0]
        code = [4, 5]
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block(na_name, length=len(na_data), data_type=1),
            create_tap_data_block(na_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,28',
            'Number array: numbers   ',
            'Fast loading data block: 23786,16',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(na_data, snapshot[23786:23786 + len(na_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_headerless_block(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            16, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        code = [
            221, 33, 0, 192,  # LD IX,49152
            17, 2, 0,         # LD DE,2
            55,               # SCF
            159,              # SBC A,A
            221, 229,         # PUSH IX
            195, 86, 5        # JP 1366
        ]
        code2 = [128, 129]
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code),
            create_tap_data_block(code2)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,14',
            'Fast loading data block: 49152,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=49152',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        self.assertEqual(code2, snapshot[49152:49152 + len(code2)])
        exp_reg = set(('SP=65344', 'IX=49154', 'IY=23610', 'PC=49152'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_overlong_blocks(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            16, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        code = [4, 5]
        basic_header = create_tap_header_block("simloadbas", 10, len(basic_data), 0)
        basic_header[0] += 1
        basic_header.append(1)
        basic_data_block = create_tap_data_block(basic_data)
        basic_data_block[0] += 1
        basic_data_block.append(2)
        code_header = create_tap_header_block("simloadbyt", code_start, len(code))
        code_header[0] += 1
        code_header.append(3)
        code_data_block = create_tap_data_block(code)
        code_data_block[0] += 1
        code_data_block.append(4)
        blocks = [
            basic_header,
            basic_data_block,
            code_header,
            code_data_block
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data + [128], snapshot[23755:23755 + len(basic_data) + 1])
        self.assertEqual(code + [0], snapshot[code_start:code_start + len(code) + 1])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_undersize_block(self):
        code2 = [201]
        code2_start = 49152
        code2_end = code2_start + len(code2)
        code = [
            221, 33, 0, 192,  # LD IX,49152
            221, 229,         # PUSH IX
            17, 5, 0,         # LD DE,5
            55,               # SCF
            159,              # SBC A,A
            195, 86, 5,       # JP 1366
        ]
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            16, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        code2_data_block = create_tap_data_block(code2)
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code),
            code2_data_block
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')

        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        self.assertEqual(code2, snapshot[code2_start:code2_end])
        self.assertEqual(snapshot[code2_end], code2_data_block[-1])
        exp_reg = set(('SP=65344', f'IX={code2_end+1}', 'E=3', 'D=0', 'IY=23610', 'PC=49152', 'F=0'))
        self.assertLessEqual(exp_reg, set(options.reg))

        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,14',
            'Fast loading data block: 49152,5',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=49152'
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_skips_blocks_with_wrong_flag_byte(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            16, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        code = [
            221, 33, 0, 0,    # 32768 LD IX,0
            17, 2, 0,         # 32772 LD DE,2
            55,               # 32775 SCF
            159,              # 32776 SBC A,A
            205, 86, 5,       # 32777 CALL 1366
            221, 33, 0, 192,  # 32780 LD IX,49152
            48, 245,          # 32784 JR NC,32775
        ]
        code2 = [128, 129]
        blocks = [
            create_tap_data_block(code), # Skipped
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code),
            create_tap_header_block("IGNORE ME", 49152, len(code2)), # Skipped
            create_tap_data_block(code2)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Data block (18 bytes) [skipped]',
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,18',
            'Bytes: IGNORE ME  [skipped]',
            'Fast loading data block: 49152,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32780',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        self.assertEqual(code2, snapshot[49152:49152 + len(code2)])
        exp_reg = set(('SP=65344', 'IX=49154', 'IY=23610', 'PC=32780', 'F=1'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_ignores_extra_byte_at_end_of_tape(self):
        code_start = 32768
        code = [4, 5]
        blocks, basic_data = self._write_basic_loader(code_start, code, False)
        tapfile = self._write_tap(blocks + [[0]])
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual(code, snapshot[code_start:code_start + len(code)])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_preserves_border_colour(self):
        code_start = 32768
        code_start_str = [ord(c) for c in str(code_start)]
        basic_data = [
            0, 10,            # Line 10
            22, 0,            # Line length
            239, 34, 34, 175, # LOAD ""CODE
            58,               # :
            231, 176,         # BORDER VAL
            34, 51, 34,       # "3"
            58,               # :
            249, 192, 176,    # RANDOMIZE USR VAL
            34,               # "
            *code_start_str,  # start address
            34,               # "
            13                # ENTER
        ]
        code = [201]
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
            create_tap_header_block("simloadbyt", code_start, len(code)),
            create_tap_data_block(code)
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,26',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,1',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertIn('border=3', options.state)

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_preserves_interrupt_mode_and_flip_flop(self):
        code_start = 32768
        code = [
            243,              # 32768 DI
            237, 94,          # 32769 IM 2
            201,              # 32771 RET
        ]
        start = 32771
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        z80file = '{}/out.z80'.format(self.make_directory())
        output, error = self.run_tap2sna(f'--sim-load --start {start} {tapfile} {z80file}')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,4',
            'Tape finished',
            'Simulation stopped (PC at start address): PC=32771',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertIn('im=2', options.state)
        self.assertIn('iff=0', options.state)

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_ram_call(self):
        ram_module = """
            def fix(snapshot):
                snapshot[32768:32772] = [1, 2, 3, 4]
        """
        module_dir = self.make_directory()
        module_name = 'simloadram'
        module_path = os.path.join(module_dir, f'{module_name}.py')
        module = self.write_text_file(textwrap.dedent(ram_module).strip(), path=module_path)
        code_start = 32768
        code = [4, 5]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        output, error = self.run_tap2sna(f'--sim-load --ram call={module_dir}:{module_name}.fix {tapfile} out.z80')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual([1, 2, 3, 4], snapshot[32768:32772])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_ram_move(self):
        code_start = 32768
        code = [4, 5]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        output, error = self.run_tap2sna(f'--sim-load --ram move=32768,2,32770 {tapfile} out.z80')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual([4, 5, 4, 5], snapshot[32768:32772])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_ram_poke(self):
        code_start = 32768
        code = [4, 5]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        output, error = self.run_tap2sna(f'--sim-load --ram poke=32768-32770-2,1 {tapfile} out.z80')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual([1, 5, 1], snapshot[32768:32771])
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_ram_sysvars(self):
        code_start = 32768
        code = [4, 5]
        tapfile, basic_data = self._write_basic_loader(code_start, code)
        output, error = self.run_tap2sna(f'--sim-load --ram sysvars {tapfile} out.z80')
        out_lines = output.strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,20',
            'Bytes: simloadbyt',
            'Fast loading data block: 32768,2',
            'Tape finished',
            'Simulation stopped (PC in RAM): PC=32768',
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(error, '')
        self.assertEqual(basic_data, snapshot[23755:23755 + len(basic_data)])
        self.assertEqual([203, 92], snapshot[23627:23629]) # VARS=23755
        self.assertEqual([204, 92], snapshot[23641:23643]) # E-LINE=23756
        self.assertEqual([206, 92], snapshot[23649:23651]) # WORKSP=23758
        self.assertEqual([206, 92], snapshot[23651:23653]) # STKBOT=23758
        self.assertEqual([206, 92], snapshot[23653:23655]) # STKEND=23758
        exp_reg = set(('SP=65344', 'IX=32770', 'IY=23610', 'PC=32768'))
        self.assertLessEqual(exp_reg, set(options.reg))

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_unexpected_end_of_tape(self):
        basic_data = [
            0, 10,       # Line 10
            4, 0,        # Line length
            239, 34, 34, # LOAD ""
            13           # ENTER
        ]
        blocks = [
            create_tap_header_block("simloadbas", 10, len(basic_data), 0),
            create_tap_data_block(basic_data),
        ]
        tapfile = self._write_tap(blocks)
        z80file = '{}/out.z80'.format(self.make_directory())
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna(f'--sim-load {tapfile} {z80file}')
        out_lines = self.out.getvalue().strip().split('\n')
        exp_out_lines = [
            'Program: simloadbas',
            'Fast loading data block: 23755,8',
            'Tape finished'
        ]
        self.assertEqual(exp_out_lines, out_lines)
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot out.z80: Failed to fast load block: unexpected end of tape')
        self.assertEqual(self.err.getvalue(), '')

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_tzx_block_type_0x15(self):
        block = [
            21,          # Block ID
            79, 0,       # T-states per sample
            0, 0,        # Pause
            8,           # Used bits in last byte
            3, 0, 0,     # Data length
            1, 2, 3,     # Data
        ]
        tzxfile = self._write_tzx([block])
        z80file = '{}/out.z80'.format(self.make_directory())
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna(f'--sim-load {tzxfile} {z80file}')
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot out.z80: TZX Direct Recording (0x15) not supported')
        self.assertEqual(self.out.getvalue(), '')
        self.assertEqual(self.err.getvalue(), '')

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_tzx_block_type_0x18(self):
        block = [
            24,          # Block ID
            11, 0, 0, 0, # Block length
            0, 0,        # Pause
            68, 172,     # Sampling rate
            1,           # Compression type
            1, 0, 0, 0,  # Number of stored pulses
            1,           # CSW Data
        ]
        tzxfile = self._write_tzx([block])
        z80file = '{}/out.z80'.format(self.make_directory())
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna(f'--sim-load {tzxfile} {z80file}')
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot out.z80: TZX CSW Recording (0x18) not supported')
        self.assertEqual(self.out.getvalue(), '')
        self.assertEqual(self.err.getvalue(), '')

    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_sim_load_with_tzx_block_type_0x19(self):
        block = [
            25,          # Block ID
            14, 0, 0, 0, # Block length
            0, 0,        # Pause
            0, 0, 0, 0,  # Number of symbols in pilot/sync block
            1,           # Maximum number of pulses per pilot/sync symbol
            1,           # Number of pilot/sync symbols in alphabet table
            0, 0, 0, 0,  # Number of symbols in data stream
            1,           # Maximum number of pulses per data symbol
            1,           # Number of data symbols in alphabet table
        ]
        tzxfile = self._write_tzx([block])
        z80file = '{}/out.z80'.format(self.make_directory())
        with self.assertRaises(SkoolKitError) as cm:
            self.run_tap2sna(f'--sim-load {tzxfile} {z80file}')
        self.assertEqual(cm.exception.args[0], 'Error while getting snapshot out.z80: TZX Generalized Data Block (0x19) not supported')
        self.assertEqual(self.out.getvalue(), '')
        self.assertEqual(self.err.getvalue(), '')

    def test_default_state(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--force --ram load=1,16384 {} {}'.format(tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(30)
        self.assertEqual(z80_header[12] & 14, 0) # border=0
        self.assertEqual(z80_header[27], 1) # iff1=1
        self.assertEqual(z80_header[28], 1) # iff2=1
        self.assertEqual(z80_header[29] & 3, 1) # im=1

    def test_state_iff(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        iff_value = 0
        output, error = self.run_tap2sna('--force --ram load=1,16384 --state iff={} {} {}'.format(iff_value, tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(29)
        self.assertEqual(z80_header[27], iff_value)
        self.assertEqual(z80_header[28], iff_value)

    def test_state_iff_bad_value(self):
        self._test_bad_spec('--state iff=fa', 'Cannot parse integer: iff=fa')

    def test_state_im(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        im_value = 2
        output, error = self.run_tap2sna('--force --ram load=1,16384 --state im={} {} {}'.format(im_value, tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(30)
        self.assertEqual(z80_header[29] & 3, im_value)

    def test_state_im_bad_value(self):
        self._test_bad_spec('--state im=Q', 'Cannot parse integer: im=Q')

    def test_state_border(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        border = 4
        output, error = self.run_tap2sna('--force --ram load=1,16384 --state border={} {} {}'.format(border, tapfile, z80file))
        self.assertEqual(error, '')
        with open(z80file, 'rb') as f:
            z80_header = f.read(13)
        self.assertEqual((z80_header[12] // 2) & 7, border)

    def test_state_border_bad_value(self):
        self._test_bad_spec('--state border=x!', 'Cannot parse integer: border=x!')

    def test_state_invalid_parameter(self):
        self._test_bad_spec('--state baz=2', 'Invalid parameter: baz=2')

    def test_state_help(self):
        output, error = self.run_tap2sna('--state help')
        self.assertTrue(output.startswith('Usage: --state name=value\n'))
        self.assertEqual(error, '')

    def test_args_from_file(self):
        data = [1, 2, 3, 4]
        start = 49152
        args = """
            ; Comment
            # Another comment
            --force ; Overwrite
            --ram load=1,{} # Load first block
        """.format(start)
        args_file = self.write_text_file(textwrap.dedent(args).strip(), suffix='.t2s')
        snapshot = self._get_snapshot(start, data, '@{}'.format(args_file))
        self.assertEqual(data, snapshot[start:start + len(data)])

    @patch.object(tap2sna, 'urlopen', Mock(return_value=BytesIO(bytearray(create_tap_data_block([2, 3])))))
    @patch.object(tap2sna, '_write_z80', mock_write_z80)
    def test_remote_download(self):
        data = [2, 3]
        start = 17000
        url = 'http://example.com/test.tap'
        output, error = self.run_tap2sna('--ram load=1,{} {} {}/test.z80'.format(start, url, self.make_directory()))
        self.assertTrue(output.startswith('Downloading {}\n'.format(url)))
        self.assertEqual(error, '')
        self.assertEqual(data, snapshot[start:start + len(data)])

    @patch.object(tap2sna, 'urlopen', Mock(side_effect=urllib.error.HTTPError('', 403, 'Forbidden', None, None)))
    def test_http_error_on_remote_download(self):
        with self.assertRaisesRegex(SkoolKitError, '^Error while getting snapshot test.z80: HTTP Error 403: Forbidden$'):
            self.run_tap2sna('http://example.com/test.zip {}/test.z80'.format(self.make_directory()))

    def test_no_clobber(self):
        block = create_tap_data_block([0])
        tapfile = self._write_tap([block])
        z80file = self.write_bin_file(suffix='.z80')
        output, error = self.run_tap2sna('--ram load=1,16384 {} {}'.format(tapfile, z80file))
        self.assertTrue(output.startswith('{}: file already exists; use -f to overwrite\n'.format(z80file)))
        self.assertEqual(error, '')
