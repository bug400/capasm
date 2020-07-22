CAPASM: an Assembler for the HP Capricorn CPU
=============================================


Index
-----

* [Description](#description)
* [Assembler instructions](#assembler-instructions)
* [Installation](#installation)
* [Basic use of the assembler](#basic-use-of-the-assembler)
* [Assembler command line parameters](#assembler-command-line-parameters)
* [Basic use of the LIF image file creator](#basic-use-of-the-lif-image-file-creator)
* [LIF image file creator command line parameters](#lif-image-file-creator-command-line-parameters)
* [Create Upload LIF images for the HP-75](#create-upload-lif-images-for-the-hp-75)
* [Add a LEX file header to assembled LEX files](#add-a-lex-file-header-to-assembled-lex-files)
* [Create ROM image files](#create-rom-image-files)
* [Known Issues](#known-issues)
* [License](#license)
* [Acknowledgements](#acknowledgements)


Description
-----------
CAPASM is a software suite primary intended for programmers who would like to
assemble ROM or LEX files for the Series 80 desktop or the HP-75 handheld 
computers. 

Essential part of the software suite is the assembler *capasm* which is 
almost compatible to the assembler of the HP-83/85 Assembler ROM and the HP-86/87 Assembler ROM. 

In addition the CAPASM suite provides tools to post-process the assembled
object files to LEX-, LIF image or ROM files in order to use the assembled
files in emulators or "real" hardware.

The CAPASM software is entirely written in Python3 and was successfully 
tested on LINUX, mac OS and Windows 10.


Assembler Instructions
----------------------

The *capasm* assembler instructions are as far as possible documented in section 4 of the HP-83/85 Assembler ROM manual. The manual is available on the [www.series80.org](http://www.series80.org) web site.

Restrictions to the HP-83/85 Assembler ROM language:

* The use of special characters in symbol names is restricted to "$+-.#/?(!&)=:<>\|@\*%^"
* The GLO pseudo opcode is not supported, use the *-m* option instead (see below).
* The ABS 16 and ABS 32 pseudo ops of the HP-83/85 ROM Assemblerare not
  supported. Use *ABS nnnnn* to specify the address of an absoulte binary 
  program.
* ASC and ASP only support quoted strings as arguments. Use either " or '
  to quote a string. 
* The pseudo opcodes LST and UNL are silently ignored.

Extensions to the HP-83/85 Assembler ROM language:

* The assembler provides built in symbol tables for the HP-85, HP-87 and
  HP-75. The *-m* option specifies which table to use. This makes an
  ORG pseudo op redundant. Default is to use the global symbol table for the 
  HP-85.
* If a program number is supplied in a NAM pseudo operation *capasm* generates a HP-87 program header.
* A symbol cross reference listing which is activated with the *-r 2* option.
* The maximum length of symbol names can be adjusted within the range from 
  6 to 12 characters.
* The pseudo instructions for conditional assembly were extended by an
  ELS statement and may be nested
* In addition to the LNK pseudo instruction an INC statement allows 
  including assembler source files.
* Line numbers in the assembler source file are optional.
* The *-x* option outputs addresses and code as hex numbers
* Non octal numbers are supported as register numbers
* Binary (1001B or 1001b) and hexadecimal (01CH, 01Ch or 01C#) are supported. Note: hexadecimal numbers must always begin with a number!
* Support for the HED and the LOC statement.
* Support for empty literal data lists, e.g. LDM R40,=

HED 'Quoted String'<br />
This pseudo opcode forces a form feed. The quoted string is printed in the header of the page except for the first page.

LOC  numeric constant<br />
This statement is only supported in absolute programs. It forces the program counter (PC) to the numeric constant by generating an appropriate number of zero bytes. Does nothing, if PC is already the numeric constant. Generates an error, if the PC is greater.


Installation
------------

See the [Installation Instructions](https://github.com/bug400/capasm/blob/master/INSTALL.md) for details.


Basic use of the assembler
--------------------------

The *lex85* subdirectory of this repository contains the sample HP-85 LEX file ftoc.asm from the HP-83/85 Assembler ROM manual. To assemble this file type:

        capasm ftoc.asm

This assembles the file *ftoc.asm* and creates a binary object file *ftoc.bin*. Any error messages are printed to the terminal.

To get a list file type:

        capasm ftoc.asm -l ftoc.lst

This creates a list file *ftoc.lst* with the default symbol table. To get a symbol table with a cross reference use the *-r 2* option:

        capasm ftoc.asm -l ftoc.lst -r 2

If not specified, the name of the binar object file is the name of the source file with the extension *.bin*. You can specify a different binary object file name with the *-b* option:

        capasm ftoc.asm -l ftoc.lst -b result.bin -r 2


Assembler command line parameters
---------------------------------

You get a description of the command line parameters if you type:

        capasm -h

```
Usage: capasm [-h] [-b BINFILE] [-l LISTFILE] [-r {0,1,2}] [-p PAGESIZE]
              [-w WIDTH] [-m {75,85,87}] [-c] [-x] [-s {6,7,8,9,10,11,12}]
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
  -r {0,1,2}, --reference {0,1,2}
                        symbol reference 0:none, 1:short, 2:full
  -p PAGESIZE, --pagesize PAGESIZE
                        lines per page (default:66)
  -w WIDTH, --width WIDTH
                        page width (default:80)
  -m {75,85,87}, --machine {75,85,87}
                        Machine type (default:85)
  -c, --check           activate additional checks
  -x, --hex             use hex output
  -s {6,7,8,9,10,11,12}, --symnamelength {6,7,8,9,10}
                        maximum length of symbol names (default:6)

See https://github.com/bug400/capasm for details
```

*capasm* provides built in repositories of the global symbols for the HP-83/85, HP86/87 or HP-75 computers. The required repository is selected with the *-m* parameter.

You can enable additional checks with the *-c* option to let the assembler recognize the following issues as an error:

* redefine global symbols as local labels or constants
* use R# as data register operand in literal immediate mode, if the value of
  the drp is unknown, e.g.: `LABELA   ADM R#,1,2,3,4`


Basic use of the LIF image file creator
---------------------------------------

To store the assembled LEX file *ftoc.bin* in an Upload LIF image file type:

        caplif ftoc.bin

This creates a LIF image file *ftoc.dat* that has a LIF file system where
the file *ftoc.bin* is stored with the default file name *WS_FILE* and the
file type 0xE008 (BPGM Binary Program). This Upload LIF image has a non
standard volume header and is inteded for use with the
[HP-85/85B787 Emulator](http://www.kaser.com/hp85.html) of Everett Kaser.

*caplif* can not insert multiple input files into an upload LIF image file.

You can specify a different file name for the Upload LIF image file with the 
*-l* option:

        caplif ftoc.bin -l disk0.dat

You can define an other name for te LIF directory entry than WS_FILE as well:

        caplif ftoc.bin -l disk0.dat -f ftoc

The file name specified with the *-f* parameter is converted to uppercase. 

For the LIF directory entries the following rules apply:

* the maximum length is 8 charaters
* the file name must begin with a character
* the remaining characters must be letters, digits or underscores - underscores
   are allowed for the Series 80 only!


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


Create Upload LIF images for the HP-75
--------------------------------------

Upload LIF images for the HP-75 are created in the same manner as for the Series 80 computers. However, the command line parameter *-m 75* is required for *capasm* and *caplif*.

*caplif* adds a HP-75 RAM file header to the assembled LEX file and stores it 
in the filesystem of the Upload LIF image with the file type 0xE089 (HP75 LEX file). The default file name in the directory entry is the name of the binary object file without suffix. This Upload LIF image file has
a standard volume header and can be used with the [EMU-75 Emulator](http://www.jeffcalc.hp41.eu/emu71/index.html) of J-F Garnier.


Add a LEX file header to assembled LEX files
--------------------------------------------

The *caplex* utility adds a LEX file header to an assembled Series 80 LEX file.
If the *-m 75* parameter is specified, a HP-75 RAM file header and a
LEX file header is put in front of the assembled lex file.
The program operates the same way as the *caplif* utility.

Create ROM image files
----------------------

The *caprom* tool converts an assembled binary file to a ROM image. An appropriate ROM header must be present in the assembled binary file. The size of the ROM image file must be specified. *caprom* fills up the assembled binary file to the size of the ROM image and creates the appropriate checksum(s). This is supported for HP-83/85, HP-87 and HP-75 ROM image files. The ROM type is autodetected from the ROM header in the assembled binary file.

Use *caprom -h* for a description of parameters.


Known Issues
------------

The global symbol file for the HP-75 contains a couple of duplicate entries 
(see the file *duplicateSymbols.txt* in the *symbols* directory).
The *capasm* assembler only uses the *last* entry.


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
