CAPASM Assembler Language Description
=====================================

Index
-----

* [Introduction](#introduction)
* [Restrictions to the HP-83/85 Assembler ROM language](#restrictions-to-the-hp83/85-assembler-rom-language)
* [Extensions to the HP-83/85 Assembler ROM language](#extensions-to-the-hp83/85-assembler-rom-language)
* [Additional pseudo-ops](#additional-pseudo-ops)
* [Additions to conditional assembly pseudo-ops](#additions-to-conditional-assembly-pseudo-ops)


Introduction
------------

The machine instructions for the *CAPRICORN* CPU are as far as possible documented in section 4 of the HP-83/85 Assembler ROM manual. The manual is available on the [www.series80.org](http://www.series80.org) website.


Restrictions to the HP-83/85 Assembler ROM language
---------------------------------------------------

* The ````LST, UNL```` and ```` GLO pseudo```` opcodes are ignored. 
* The ````ABS 16```` and ````ABS 32```` pseudo ops of the HP-83/85 ROM 
  Assembler are not supported. Use ````ABS nnnnn```` to specify the address 
  of an absolute binary program.
* The *capasm* software suite does not support the HP Series 80 character
  set. Therefore, all characters must be in the character code range
  (0x20-0x7A, 0x7C).


Extensions to the HP-83/85 Assembler ROM language
-------------------------------------------------

* The assembler provides built in symbol tables for the HP-85, HP-87 and
  HP-75. The *-g* option specifies which table to use. This makes an
  ORG pseudo op redundant. The default is to use no symbol table. Combined with
  the *capglo* tool you can use custom symbol tables as well.
* If a program number is supplied in a ````NAM```` pseudo operation *capasm* 
  generates an HP-87 program header.
* A symbol cross-reference listing which is activated with the *-r 2* option.
* The maximum length of symbol names can be adjusted within the range from 
  6 to 12 characters.
* Line numbers in the assembler source file are optional.
* The *-x* option outputs addresses and code as hex numbers
* Non-octal numbers are supported as register numbers
* Binary (1001B or 1001b) and hexadecimal (01CH, 01Ch or 01C#) numbers are 
  supported. Note: hexadecimal numbers must always begin with a number!
* Support for empty literal data lists, e.g:

               LDM  R40,=
       CALNAM  ASC "calcprog"


Additional pseudo-ops
---------------------

    OCT Octal Number {, Octal Number }
This is equivalent to the ````BYT```` pseudo opcode but only accepts a list of 

octal numbers as operands.

    HED 'Quoted String'

This pseudo opcode forces a form feed. The quoted string is printed in the header of the page except for the first page.

    LOC  numeric constant

This statement is only supported in absolute programs. It forces the program counter (PC) to the numeric constant by generating an appropriate number of zero bytes. Does nothing, if PC is already the numeric constant. Generates an error, if the PC is greater.

    INC 'quoted string'

Include the given file into the program.  The *INC* instruction is printed in
the program listing. Included files can be nested up to a level of 3.


Additions to conditional assembly pseudo-ops
--------------------------------------------

The conditional assembly pseudo-ops were extended with the following instructions:

    ELS

The source code following this instruction is treated in the opposite way as
the corresponding *AID* or *DIF* conditional.


    DIF <symbol>

Tests if the specified conditional assembly flag does exist, e.g. was either
defined by a *SET*, or *CLR* pseudo-op or was set with the *-d* command line
option.

Conditional assembly *AIF/DIF-EIF* or *AIF/DIF-ELS-EIF* pseudo-op sequences can
be nested.

