CAPASM: an Assembler for the HP Capricorn CPU
=============================================


Index
-----

* [Description](#description)
* [Installation](#installation)
* [Assemble files](#assemble-files)
* [CAPASM Assembler command line parameters](#capasm-assembler-command-line-parameters)
* [NCAS Assembler command line parameters](#ncas-assembler-command-line-parameters)
* [Create LIF image files for Series 80 computers](#create-lif-image-files-for-series-80-computers)
* [Create LIF images for the HP-75](#create-lif-images-for-the-hp-75)
* [LIF image file creator command line parameters](#lif-image-file-creator-command-line-parameters)
* [Add LEX file headers to assembled LEX files](#add-lex-file-headers-to-assembled-lex-files)
* [Create ROM image files](#create-rom-image-files)
* [Create custom global symbol tables](#create-custom-global-symbol-tables)
* [Convert Series 80 Assembler files](#convert-series-80-assembler-files)
* [Known Issues](#known-issues)
* [Release Notes](#release-notes)
* [License](#license)
* [Acknowledgements](#acknowledgements)


Description
-----------
CAPASM is a software suite primary intended for programmers who would like to
assemble ROM or LEX files for the Series 80 desktop or the HP-75 handheld 
computers. 

Essential part of the software suite are the assemblers:
* *capasm* which is almost compatible to the assembler of the HP-83/85 Assembler 
  ROM and the HP-86/87 Assembler ROM. See the 
  [CAPASM Assembler language description](CAPASM.md) for details.
* *ncas* which implements language elements to facilitate the assembly of
  source code written for the *karma* assembler. The *karma* assembler
  was used by HP for the development of the HP-75 system ROMs. See the 
  [NCAS Assembler language description](NCAS.md) for details.

In addition, the CAPASM suite provides tools to post-process the assembled
object files to LEX, LIF image or ROM files in order to use the assembled
files in emulators or "real" hardware.

The CAPASM software is entirely written in Python3 and was successfully 
tested on LINUX, macOS and Windows 10.


Installation
------------

See the [Installation Instructions](https://github.com/bug400/capasm/blob/master/INSTALL.md) for details.


Assemble files
--------------

The *lex85* subdirectory of this repository contains the sample HP-85 LEX file ftoc.asm from the HP-83/85 Assembler ROM manual. To assemble this file type:

        capasm ftoc.asm

This assembles the file *ftoc.asm* and creates a binary object file *ftoc.bin*. Any error messages are printed to the terminal.

To get a list file type:

        capasm ftoc.asm -l ftoc.lst

This creates a list file *ftoc.lst* with the default symbol table. To get a symbol table with a cross-reference use the *-r 2* option:

        capasm ftoc.asm -l ftoc.lst -r 2

Note: The default base of addresses in the list file is octal.

If not specified, the name of the binar object file is the name of the source file with the extension *.bin*. You can specify a different binary object file name with the *-b* option:

        capasm ftoc.asm -l ftoc.lst -b result.bin -r 2

The *ncas* assembler is called in the same way. The default base for addresses in
*ncase* assembly list files is hexadecimal. The *lex75* subdirectory contains
sample assembler source files for *ncas*.


CAPASM Assembler command line parameters
----------------------------------------

You get a description of the command line parameters if you type:

        capasm -h

```
usage: capasm [-h] [-b BINFILE] [-l LISTFILE] [-g GLOBALSYMBOLFILE]
              [-r {0,1,2}] [-p PAGESIZE] [-w WIDTH] [-c] [-x]
              [-s {6,7,8,9,10,11,12}]
              sourcefile

An assembler for the Hewlett Packard Capricorn CPU (Series 80 and HP-75)

positional arguments:
  sourcefile            source code file (required)

optional arguments:
  -h, --help            show this help message and exit
  -b BINFILE, --binfile BINFILE
                        binary object code file (default: sourcefilename with
                        suffix .bin)
  -l LISTFILE, --listfile LISTFILE
                        list file (default: no list file)
  -g GLOBALSYMBOLFILE, --globalsymbolfile GLOBALSYMBOLFILE
                        global symbol file. Use either the built-in symbol
                        table names {"85","87","75","none"} or specify a file
                        name for a custom table (default: none)
  -r {0,1,2}, --reference {0,1,2}
                        symbol reference 0:none, 1:short, 2:full
  -p PAGESIZE, --pagesize PAGESIZE
                        lines per page (default:66)
  -w WIDTH, --width WIDTH
                        page width (default:80)
  -c, --check           activate additional checks
  -d DEFINE, --define DEFINE
                        define conditional flag with value True
  -x, --hex             use hex output
  -s {6,7,8,9,10,11,12}, --symnamelength {6,7,8,9,10}
                        maximum length of symbol names (default:6)

See https://github.com/bug400/capasm for details
```

*capasm* provides built-in global symbol tables for the HP-83/85, HP86/87 
or HP-75 computers. The required symbol table is selected with the *-g* 
option. The naming of these tables is:

- 85  : symbol table for the HP-83/85
- 87  : symbol table for the HP-86/87
- 75  : symbol table for the HP-75
- none: use no symbol table (this is the default)

Alternatively you can provide the file path of a global symbol table which must be created with the *capglo* utility (see below). The file must have
the extension ".py".

You can enable additional checks with the *-c* option. The assembler issues
a warning if:

* A symbol defined in the source file has an other value or type than a global
  symbol of the same name
* R# is used as data register operand in literal immediate mode and the value of
  the drp is unknown, e.g.: `LABELA   ADM R#,1,2,3,4`


NCAS Assembler command line parameters
--------------------------------------

You get a description of the command line parameters if you type:

        ncas -h

```
usage: ncas [-h] [-b BINFILE] [-l LISTFILE] [-g GLOBALSYMBOLFILE] [-r {0,1,2}]
            [-p PAGESIZE] [-w WIDTH] [-c] [-o]
            sourcefile

An assembler for the Hewlett Packard HP-75

positional arguments:
  sourcefile            source code file (required)

optional arguments:
  -h, --help            show this help message and exit
  -b BINFILE, --binfile BINFILE
                        binary object code file (default: sourcefilename with
                        suffix .bin
  -l LISTFILE, --listfile LISTFILE
                        list file (default: no list file)
  -g GLOBALSYMBOLFILE, --globalsymbolfile GLOBALSYMBOLFILE
                        global symbol file. Use either the built-in symbol table
                        names {"85","87","75","none"} or specify a file name for
                        a custom table (default: 75)
  -r {0,1,2}, --reference {0,1,2}
                        symbol reference 0:none, 1:short, 2:full (default:1)
  -p PAGESIZE, --pagesize PAGESIZE
                        lines per page (default: 66)
  -w WIDTH, --width WIDTH
                        page width (default:80)
  -c, --check           activate additional checks
  -d DEFINE, --define DEFINE
                        define conditional flag with value True
  -o, --oct             use octal output

See https://github.com/bug400/capasm for details.

```

*ncas* uses the built-in HP-75 global symbol table per default. You may override
this with the *-g* option to use not any or another symbol table. Custom symbol
tables must be created with the *capglo* command (see below). This file must
have the extension *.py*.

Regarding the extended checks option see the chapter above.


Create LIF image files for Series 80 computers
----------------------------------------------

To store the assembled LEX file *ftoc.bin* into an Upload LIF image file type:

        caplif ftoc.bin

This creates a LIF image file *ftoc.dat* that has a LIF file system where
the file *ftoc.bin* is stored with the default file name *WS_FILE* and the
file type 0xE008 (BPGM Binary Program). This Upload LIF image has a nonstandard 
volume header and is inteded for use with the
[HP-85/85B787 Emulator](http://www.kaser.com/hp85.html) of Everett Kaser.

*caplif* can not insert multiple input files into an upload LIF image file.

You can specify a different file name for the Upload LIF image file with the 
*-l* option:

        caplif ftoc.bin -l disk0.dat

You can define another name for the LIF directory entry than WS_FILE as well:

        caplif ftoc.bin -l disk0.dat -f ftoc

The file name specified with the *-f* parameter is converted to uppercase. 

For the LIF directory entries the following rules apply:

* The maximum length is 8 charaters
* The file name must begin with a character
* The remaining characters must be letters, digits or underscores - 
  underscores are allowed for the Series 80 only!


Create LIF images for the HP-75
-------------------------------

Upload LIF images for the HP-75 are created in almost the same manner as for the Series 80 computers. However, the command line parameter *-m 75* is required for *capasm* and *caplif*.

*caplif* adds an HP-75 RAM file header to the assembled LEX file and stores it 
in the file system of the Upload LIF image with the file type 0xE089 (HP75 LEX file). The default file name in the directory entry is the name of the binary object file without suffix. This Upload LIF image file has
a standard volume header and can be used with the [EMU-75 Emulator](http://www.jeffcalc.hp41.eu/emu71/index.html) of J-F Garnier.


LIF image file creator command line parameters
----------------------------------------------

You get a description of the command line parameters if you type:

        caplif -h

```
usage: caplif [-h] [-m {75,85,87}] [-l LIFIMAGEFILENAME] [-f FILENAME] binfile

Utility to put an assembled binary file into an import LIF image file

positional arguments:
  binfile               binary object code file (required)

optional arguments:
  -h, --help            show this help message and exit
  -m {75,85,87}, --machine {75,85,87}
                        Machine type (default=85)
  -l LIFIMAGEFILENAME, --lifimagefilename LIFIMAGEFILENAME
                        name of the Upload LIF image file (default: objectfile
                        name with suffix .dat)
  -f FILENAME, --filename FILENAME
                        name of the LIF directory entry (default: WS_FILE for
                        Series 80, deduced from object file name for HP-75)

See https://github.com/bug400/capasm for details.
```


Add LEX file headers to assembled LEX files
-------------------------------------------

The *caplex* utility adds a LEX file header to an assembled Series 80 LEX file.
If the *-m 75* parameter is specified, an HP-75 RAM file header and a
LEX file header is put in front of the assembled lex file.
The program operates the same way as the *caplif* utility.


Create ROM image files
----------------------

The *caprom* tool converts an assembled binary file to a ROM image. An appropriate ROM header must be present in the assembled binary file. The size of the ROM image file must be specified. *caprom* fills up the assembled binary file to the size of the ROM image and creates the appropriate checksum(s). This is supported for HP-83/85, HP-87 and HP-75 ROM image files. The ROM type is determined from the ROM header in the assembled binary file.

Use *caprom -h* for a description of parameters.


Create custom global symbol tables
----------------------------------

A custom global symbol table is a text file which only has DAD or EQU definitions. The *capglo* utility converts this file into a global symbol table which can be fed to the assembler with the *-g* option.

If you have a custom global symbol source file *myglobal.glo* then:

        capglo myglobal.glo

creates the global symbol table file *myglobal.py*. This file is a Python 
file, therefore:

* Do not change the suffix *.py* of that file
* Do not edit the content of the file.

To use this global symbol table to assemble the file *sample.asm* type:

        capasm sample.asm -g myglobal.glo


Convert Series 80 Assembler files
---------------------------------

The *capconv* utility can convert binary global symbol data files or 
tokenized Series 80 assembler source files to text files. See 
*capconv -h* for details how to invoke this tool. Note: Since the 
*capasm* software suite does not support the Series 80 character set, 
the result files must be revised if any characters exist in the file 
which are not in the code range (0x20-0x7A, 0x7C).


Known Issues
------------

The global symbol file for the HP-75 contains a couple of duplicate entries 
(see the file *duplicateSymbols.txt* in the *symbols* directory).
The last entry is used in each case.

The *ncas* assembler is still in beta phase. Processing faulty assembler 
files has not been tested sufficiently.


Release Notes
-------------

See the [Release Notes](https://github.com/bug400/capasm/blob/master/RELEASE.md) for details.


License
-------

CAPASM is published under the GNU General Public License v2.0 License 
(see LICENSE file).


Acknowledgements
----------------

A special acknowledgement goes to 
[Everett Kaser](https://www.kaser.com/hp85.html).
He formerly wrote the HP-83/85 Assembler ROM software which is a heroic deed
compared to writing an assembler in Python without any constraints concerning
memory or CPU speed.

On his website you can download his HP85/HP87 emulator and a powerful disassembler (CAPDIS) for the Capricorn CPU. His  documentation 
[Understanding how the HP85 Works from the Inside](https://groups.io/g/hpseries80/wiki/1884), the source files he disassembled from the ROM binaries 
and his warm support were essential for me to get this software done.
