# prettysize
 a pretty formatter for seeing embedded target memory and flash usage using

## Output
```
FLASH:     [=====     ]  48.0% (used 61.5KiB of 128KiB)
DTCMRAM:   [          ]   0.0% (used 0B of 128KiB)
SRAM:      [=         ]  11.3% (used 58.1KiB of 512KiB)
RAM_D2:    [=         ]   5.8% (used 16.6KiB of 288KiB)
SDRAM:     [          ]   0.2% (used 128KiB of 64MiB)
QSPIFLASH: [          ]   0.0% (used 0B of 8MiB)
```

## Usage
```
usage: prettysize [-h] (-c CONFIG | -l LINKER) [-s SIZE] [-v] [-a] [-N] [-w WIDTH] file

format the output of size in a friendly usable way

positional arguments:
  file                  the source file to process

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        path to the JSON memory layout map config (for pre-generated configs using prettysize_config_generator)
  -l LINKER, --linker LINKER
                        path to the linkerscript to use for calculations
  -g, --gen-config      generate a config using the provided linkerscript                        
  -s SIZE, --size SIZE  the path to the 'size' command
  -v, --verbose         prints the output of size as well
  -a, --show-all        show all memory sections (including unused)
  -N, --no-abbrev       do not abbreviate byte counts into human-readable format
  -w WIDTH, --width WIDTH
                        the width of the bargraph, in characters (defaults to 10)
```

