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

import textx
import json

ld_grammar = """
File: stanzas*=Stanza;

Stanza: Comment
      | Memory
      | Sections
      | Entry
      | Assignment
      | OutputFormat
      | OutputArch
      ;

Memory: 'MEMORY' '{' memory_spec+=MemorySpec '}';
Sections: 'SECTIONS' '{' sections*=Section '}';
Entry: 'ENTRY' '(' entry=ID ')';
OutputArch: 'OUTPUT_ARCH' '(' ID ')';

OutputFormat: 'OUTPUT_FORMAT' '(' StringList ')';

StringList: STRING ',' StringList
          | STRING
          ;

Section: Provide
       | name=Id (addr=Address)? ':' (alignment=Alignment)? '{' Definition+ '}' ('>' location=Location)?
       | Assignment
       ;

Address: '(' Address ')'
        | Arithmetic
        | ID
        | Hex
        | INT
        ;

Arithmetic: ID '-' ID;        

Alignment: 'ALIGN' '(' alignment=HexOrNum ')';

Provide: 'PROVIDE' '(' /[^)]+/ ')' ';';

Assignment: ID '=' /[^;]+/ ';' ;

Comment: /\/\*(\*(?!\/)|[^*])*\*\//;

MemorySpec: name=ID attributes=Attributes? ':' 'ORIGIN' '=' origin=Hex ','? 'LENGTH' '=' length=Size;

Attributes: '(' attributes+=Attribute ')';
Attribute: '!' Attribute | /[RWXAILrwxail]/;

Hex: '0' ('x' | 'X') /[a-fA-F\d]+/;

HexOrNum: Hex
        | /\d+/
        ;

Size: amount=HexOrNum (scale=Scale)?;
Scale: 'M' | 'K';

Location: used=ID 'AT' '>' stored=ID
        | stored = ID
        ;

Id: /[.\w\d_-]+/;
Definition: !'}' /[^};]*/ ';'?;
"""

mm = textx.metamodel_from_str(ld_grammar)

def cname(o):
    return o.__class__.__name__

def scale_to_multiplier(scale):
    match scale:
        case 'K': return 1024
        case 'M': return 1024 * 1024
        case   _: return 1

def process(path):
    model = mm.model_from_file(path)
    memory_spaces={}

    for stanza in model.stanzas:
        match cname(stanza):
            case 'Memory':
                for spec in stanza.memory_spec:
                    memory_spaces[spec.name] = {
                        'size': int(spec.length.amount, 0) * scale_to_multiplier(spec.length.scale),
                        'sections': []
                    }
            case 'Sections':
                for section in stanza.sections:
                    if section.location:
                        memory_spaces[section.location.stored]['sections'] += [section.name]
                        if section.location.used:
                            memory_spaces[section.location.used]['sections'] += [section.name]
                        #print("{} < {}".format(section.name, section.location.stored))

    return memory_spaces
  


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
      prog='prettysize_map_generator',
      description='generate memory mapping JSON from a linkerscript',
      epilog='Written by Katherine Whitlock, MIT License'
    )
    parser.add_argument("file", help='the source file to process')
    args = parser.parse_args()
    output = process(args.file)
    print(json.dumps(output, indent=4))