CAPASM release notes
====================

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
