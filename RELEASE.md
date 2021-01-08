CAPASM release notes
====================

1.0.0 (Production)
-----------------
 * CAPASM: fix incorrect range checks of relative jumps
 * CAPASM: extended check marks redefinition of global symbols if there is a type or value mismatch
 * CAPASM: suppress superfluous code output of BSZ pseudo-ops
 * CAPASM: line numbers in list file
 * CAPASM: parsing of conditional assembly pseudo-ops fixed
 * CAPASM: various other small fixes
 * CAPASM: documentation updates
 * NCAS: new assembler with extended capabilities (beta!)

0.9.8 (Beta)
------------

 * added support for ASP/ASP statements with numeric length qualifiers
 * removed "'" as alternate string delimiter
 * removed -m option, added -g option and enhanced global symbols capabilities
 * allow more special characters in symbol names
 * OCT pseudo op added
 * added capconv tool


0.9.7 (Beta)
------------

* HP-75 rom support added to caprom
* support for hex and bin constants
* support for non octal register numbers
* support for empty literal data lists, e.g. LDM R40,=
* LOC and HED pseudo ops added
* literal data list error fixes


0.9.6 (Beta)
------------

* HP-87 compatible NAM statement
* conditional assembly pseudo ops (AIF, ELS, EIF, SET, CLR)
* the GTO pseudo op generates relative jumps in non absolute assembly files include and link file support (INC, LNK) new caprom tool, which generates the necessary primary and secondary checksums
* new option to output addresses and program code as hex numbers in the list file
* bug fixes


0.9.5 (Beta)
------------

First published release
