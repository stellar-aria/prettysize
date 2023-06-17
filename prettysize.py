#!/usr/bin/env python

# MIT License

# Copyright (c) 2023 Katherine Whitlock

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import argparse
from decimal import ROUND_UP, Decimal
import subprocess
import re
from dataclasses import dataclass
import json
import sys

class Berkeley:
    def __init__(self, output):
        pattern = r'^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[\d\w]+\s+(.+)'
        regex = re.compile(pattern)

        for line in output.splitlines():
            line = line.strip()
            match = regex.match(line)
            if match:
                self.text_size = int(match.group(1))
                self.data_size = int(match.group(2))
                self.bss_size = int(match.group(3))
                self.total_size = int(match.group(4))
                self.filename = match.group(5)

class SysV:
    def __init__(self, output:str):
        file_pattern = r'^(/[\w\d\-_.]+)+\s+:'
        section_pattern = r'([.\w]+)\s+(\d+)\s+(\d+)'
        total_pattern = r'Total\s+(\d+)'
        
        regex_file = re.compile(file_pattern)
        regex_section = re.compile(section_pattern)
        regex_total = re.compile(total_pattern)

        self.entries = {}

        for line in output.splitlines():
            line.strip()
            match_file = regex_file.match(line)
            match_section = regex_section.match(line)
            match_total = regex_total.match(line)
            if match_section:
                section = match_section.group(1)
                size = int(match_section.group(2))
                #addr = int(match_section.group(3))

                self.entries[section] = size
            elif match_total:
                continue
            elif match_file:
                self.filename = match_file.group(1)

# parses objdump -h output 
class ObjDump:
    @dataclass
    class Entry:
        idx : int
        name : str
        size : int 
        vma : int 
        lma : int 
        offset : int 
        alignment : int 
        tags : list

    def __init__(self, output):
        section_pattern = r'\s*(\d+)\s+([\.\w]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+2\*\*([0-9]+)'
        regex_section = re.compile(section_pattern)

        self.sections = {}
        prev_section = ''

        for line in output.splitlines():
            match_section = regex_section.match(line)
            if match_section:
                idx = int(match_section.group(1))
                name = match_section.group(2)
                size = int(match_section.group(3), 16)
                vma = int(match_section.group(4), 16)
                lma = int(match_section.group(5), 16)
                file_off = int(match_section.group(6), 16)
                alignment = int(match_section.group(7))

                self.sections[name] = ObjDump.Entry(
                    idx = idx,
                    name = name,
                    size = size,
                    vma = vma,
                    lma = lma,
                    offset = file_off,
                    alignment = alignment,
                    tags = []
                )
                prev_section = name
            else:
                if prev_section == '':
                    continue
                tags = line.strip().split(', ')
                self.sections[prev_section].tags = tags
        
    def __str__(self):
        string = ""
        for name, data in self.sections.items():
            if data.vma != 0:
                tag_string = ', '.join(data.tags)
                string += "[{}] \t {:<25}{:<10} {:<}\n".format(data.idx, data.name, data.size, tag_string)
        return string

@dataclass
class Usage:
    name: str
    total: int
    max: int

# Execute a command as subprocess and return the output
def get_output(cmd) -> (str | None):
    cmd += args.file.split()
    result = subprocess.run(cmd, stdout=subprocess.PIPE)
    if result.returncode != 0:
        return None
    return result.stdout.decode().strip()

# Turn a number into a human-readable format
def sizeof_fmt(num:int, suffix="B") -> str:
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            dec = Decimal(num).quantize(Decimal('.1'), rounding=ROUND_UP).normalize()
            return f"{dec}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


# Turn a number and total bytes into a cute bargraph
def format_available_bytes(value:int, total:int, abbreviated=False, progress_bar_width=10) -> str:
    percent_raw = float(value) / float(total)
    used_blocks = min(int(round(progress_bar_width * percent_raw)), progress_bar_width)
    if abbreviated:
        val_fmt = sizeof_fmt(value)
        total_fmt = sizeof_fmt(total)
    else:
        val_fmt = f"{value} bytes"
        total_fmt = f"{total} bytes"        

    return "[{:{}}] {: 6.1%} (used {} of {})".format("=" * used_blocks, progress_bar_width, percent_raw, val_fmt, total_fmt)

# Format multiple memory sections
def format_sections(sections:list[Usage], show_all:bool, abbreviated:bool) -> str:
    max_columns = 0
    for section in sections:
        columns = len(section.name)
        if columns > max_columns:
            max_columns = len(section.name)

    # generate a format string with the required padding
    format_string = "{:<" + str(max_columns + 1) + "} {}"

    output = []

    for section in sections:
        if show_all or section.total != 0:
           bytes_formatted = format_available_bytes(section.total, section.max, abbreviated, args.width)
           output.append(format_string.format(section.name + ":", bytes_formatted))

    return "\n".join(output);


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='prettysize',
        description='format the output of size in a friendly usable way',
        epilog='Written by Katherine Whitlock (2023)',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--config', help='path to the JSON memory layout map config (for pre-generated configs using prettysize -g)')
    group.add_argument('-l', '--linker', help='path to the linkerscript to use for calculations')
    group.add_argument('-g', '--gen-config', action='store_true', help='generate a config using a provided linkerscript')
    parser.add_argument('-s', '--size', default="size", type=str, help="the path to the 'size' command")
    parser.add_argument('-v', '--verbose', action='store_true', help='prints the output of size as well')
    parser.add_argument('-a', '--show-all', action='store_true', help='show all memory sections (including unused)')
    parser.add_argument('-N', '--no-abbrev', action='store_true', help='do not abbreviate byte counts into human-readable format')
    parser.add_argument('-w', '--width', default=10, type=int, help='the width of the bargraph, in characters (defaults to 10)')
    parser.add_argument("file", help='the source file to process')
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    if args.gen_config:
        import prettysize_config_generator
        if args.linker:
            config = prettysize_config_generator.process(args.linker)
        elif args.file:
            config = prettysize_config_generator.process(args.file)
            print(config)
            exit()
    elif args.config:
        config = json.load(open(args.map))
    elif args.linker:
        import prettysize_config_generator
        config = prettysize_config_generator.process(args.linker)
    
    output = get_output([args.size, "-A","-d"])

    if args.verbose:
        print(output)
        print('-' * len(max(output.splitlines())))

    sysv = SysV(output)

    sections = []

    for region, details in config.items():
        if details['sections']:
            total = 0
            for section in details['sections']:
                if section in sysv.entries:
                    total += sysv.entries[section]
            sections.append(Usage(name=region, total=total, max=details['size']))

    print(format_sections(sections, args.show_all, not args.no_abbrev))