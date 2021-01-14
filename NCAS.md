NCAS: Assembler for the HP-75
=============================


Index
-----

* [Introduction](#introduction)
* [Conventions used in this document](#conventions-used-in-this-document)
* [Assembler Input Format](#assembler-input-format)
* [Constants](#constants)
* [Symbols](#constants)
* [Expressions](#expressions)
* [Data Lists](#data-lists)
* [Machine Instructions](#machine-instructions)
* [Specifying the ARP and DRP](#specifying-the-arp-and-drp)
* [Creation of Symbols](#creation-of-symbols)
* [Conditions](#conditions)
* [Conditional Returns](#conditional-returns)
* [ADDR pseudo-op](#addr-pseudo-op)
* [EQU pseudo-op](#equ-pseudo-op)
* [END pseudo-op](#end-pseudo-op)
* [INCLUDE pseudo-op](#include-pseudo-op)
* [ORG pseudo-op](#org-pseudo-op)
* [BSS pseudo-op](#bss-pseudo-op)
* [TITLE pseudo-op](#title-pseudo-op)
* [IF-ELSE-ENDIF pseudo-ops](#if-else-endif-pseudo-ops)
* [LOOP-WH pseudo-ops](#loop-wh-pseudo-ops)
* [EX pseudo-ops](#ex-pseudo-ops)
* [DATA pseudo-op](#data-pseudo-op)
* [Conditional assembly pseudo-ops](#conditional-assembly-pseudo-ops)
* [Other pseudo-ops](#other-pseudo-ops)
* [Examples](#examples)




Introduction
------------
The *ncas* assembler is a further development of the *capasm* assembler. The main
 goal of *ncas* is to assemble source files derived from source files of HP-75
system and application ROMS, which were developed with the HP *karma* assembler.

The *karma* assembler which was only used by HP internally and got lost after 
cancellation of the HP-75 project had numerous extensions to the HP-85 ROM 
assembler. The most important extensions were expressions support and language 
elements for structured programming. This causes a major effort to convert 
*karma* assembler files into a HP-85 ROM assembler source file format.

The *karma* assembler language has numerous features, bells and whistles which 
sometimes lack sound concepts. HP did a redesign of the assembler called *koda*
which was likely never realized. A language description still exists which 
shows some interesting and better designed features. See 
[this post](https://groups.io/g/hp75/topic/koda/5171903) for more
information.

For the *ncas* development the following features ware added based on *koda* 
concepts:

* Sized expressions
* Strucured programming language elements IFXX-ELSE-ENDIF and LOOP-WHXX
* *DATA* lists

This made many pseudo operations of the *capasm* assembler obsolete.

*ncas* is neither compatible to *karma* nor *koda*. This is not necessary because
neither *karma* nor *koda* assembler source files do exist anymore. Listings of
*karma* assembled files can be easily converted to the *ncas* format.


Conventions used in this document
---------------------------------

    A::=B             A is defined to be B
    C | D | E         choose one of C, D or E
    {F}               repeat F zero or more times
    [G]               G is optional
    < >               meta characters
    <open>            a real left parenthesis
    <close>           a real right parenthesis
    <bar>             a real bar



Assembler Input Format
----------------------

Input to *ncas* is either a comment or an assembler instruction.

Comment lines begin with a "\*" in the first or second column.

Assembler instructions have the format:

    [label]  opcode [operands] [;comment]

Example:

    center  ldmd r2,r10  ; get pointer to RADQ lines
                         ; by loading current offset
            tcm  r2      ; complement that
            bin
    store
            stmd r2,r10  ; now store it back
    gotit                ; we've got it now
            rtn


Blanks are mandatory:

* Between label and opcode
* Before the opcode if no label is present (two blanks are required)
* Between opcode and operands
* Between operands and the semicolon of a comment

Blanks are forbidden:

* Inside an opcode
* Inside symbol names
* Inside a numeric constant
* Before a label
* In expressions

Blanks are optional

* Between operands (though the comma is still required)

Assembler opcodes and registers are case-independent. All other input is
case sensitive!


Constants
---------
    
    <constant>  ::=  <bin con> | <bcd con> | <oct con> | <dec con>
                       <hex con> | <K con>  | <chr con>
    
    <bin con>   ::=  <bin digit> {<bin digit>} B 
    
    <bcd con>   ::=  <digit> {<digit>} C
    
    <oct con>   ::=  <oct digit> {<oct digit>} (O|Q)
    
    <dec con>   ::=  <digit> {<digit>}
    
    <hex con>   ::=  <digit> {<hex digit>} (H|#)
    
    <K con>     ::=  <digit> {<digit>} K
    
    <chr con>   ::=  "{<character>}"
                       '{<character>}'
                       `{<character>}`
                       ^{<character>}^
    
    <digit>     ::=  0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9
    
    <bin digit> ::=  0 | 1
    
    <oct digit> ::=  0 | 1 | 2 | 3 | 4 | 5 | 6 | 7
    
    <hex digit> ::=  <digit> | A | B | C | D | E | F
    
Notes:

* The default base of numbers is octal!
* A hex constant must always begin with a decimal number e.g. 0FAH
* Strings enclosed in "`" or "^" yield in a string with the top bit of the last
  character set 


Symbols
-------

    <letter>    ::=  A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z
    
    <other char>::=  _|$|+|-|.|#|/|?|(|!|&|)|=|:|<|>|||@|*|^
    
    <symbol>    ::=  <letter> {<letter>|<digit>|<other char>}

Notes:
* Symbol names must not exceed 32 characters
* The symbol "$" returns the address of the beginning of the source line
* Due to the implementation of expressions (see below) the characters "(", ")"
  "'", ""","`" and "^" are not allowed in symbol names. Unfortunately some
  global symbols of the HP-75 system ROMs use these characters. It is
  recommended to use "\_" as a replacement character. The HP-75 global symbol
  file for *ncas* considers that, e.g. X(K-1) was renamed to X\_K-1\_.

To support the generation of file headers the one bytes symbols *BCD_YEAR*, 
*BCD_MONTH*, *BCD_DAY*, *BCD_HOUR*, *BCD_MIN*, *BCD_SEC* and the four byte
symbol *SECONDS1900* represent the current system date.


Expressions
-----------

    <sized exp> ::= <open> <expression> <close> [.<size spec>]

    <size spec> ::= <constant>
  
    <expression>::= <term> { <monadic op> <term> }

    <term>      ::= <factor> { <mul op> <factor> }

    <factor>    ::= <bool> { <bool op> <bool> }

    <bool>      ::= [-] <base>

    <base>      ::= $
                    <constant>
                    <sized expression>
                    <symbol>

    <monadic op>::= + | - 

    <mul op>    ::= * | / | %

    <bool op>   ::=  <bar> | &

Notes:

* *ncas* regards the size of the result of a computation always as unknown. 
* With a few exceptions (see below) expressions are evaluated in the second
  pass of the assembly. In this case the use of forward references
  (symbols which are defined later in the source file) is allowed.


Data Lists
----------

    <data list> ::= <sized exp>, {, <sized exp>}

Many machine instructions and the *DATA* pseudo-op use \<data lists\>. 
This is a comma separated list of expressions which is generated into the
object code.

Example:

    blank  equ ' '
    start  addr  129CH
           ldm   R2,=blank,0          ; data list is 20 00 hex
           ldmd  R40,34Q              ; data list is 1C 00 hex
           stmd  R20,=START           ; data list is 9C 12 hex
           adm   1,(2+4).1,(8D).5,'X' ; data list is 01 06 08 00 00 00 00 58 hex

An additional .\<constant\> after an expression is a \<size spec\>. The
\<size spec\> forces the expression to take up that number of bytes.

If a data list is used as an operand then its required size is determined
according to the following rules:

* If the instruction intrinsically wants a two-byte operant (like LDMD), the
  required size is two bytes. Single byte values are sized to two bytes.
* If the instruction is a single byte instruction (like ADB), the required size
  is one byte.
* If the drp is known, then the required size of the data list is determined
  by the register boundary. If the length of the data list is less than the
  required length, a warning is issued (see below).
* If the drp is unknown, a warning is issued if extended checks of the assembler
  were enabled.

Exceeding the required length of a data list is an error.

If \<data list\> items are not sized explicitly, their size is determined in the
following way:

* Address symbols which are either local labels or symbols which were defined
  with the *ADDR* pseudo operation have always a size of two bytes
* The size of strings is their number of characters
* The size of integer constants is the smallest number of bytes to store that
  number

If an expressions has any operand, then the size of the result is *unknown*
because expressions are executed in the second pass of the assembler. 
Therefore, expressions with operands must always be explicitly. 

Note:
The monadic "-" is regarded as an operand. Therefore, negative constants must
always be sized in data lists. Sized negative constants are converted to a
2'S representation.


Example:

           LDMD  R45,=RTC           ; required size is 2 bytes
                                    ; RTC is generated as a two byte value,
                                    ; regardless of its size
           LDM   R45,=110B          ; required size 3 bytes 
                                    ; a warning is issued because the actual 
                                    ; size is less than 3 bytes
           LDM   R45,=(110B).3      ; the constant 6 is resized to 3 bytes
           CMBD  T73,=BUFFER        ; required size 2 bytes
           LDB   R62,TYNLEX         ; required size 1 byte
    LBL    ADM   R#,1,2,3           ; generates three bytes and a warning is 
                                    ; issued, because the register boundary
                                    ; is unknown
           LDM   R45,=1,(-1).2      ; -1 has to be sized explicitly and is
                                    ; generated as a 2 bytes 2'S representation
           
          

Machine Instructions
--------------------

The machine instructions for the *CAPRICORN* CPU are as far as possible documented in section 4 of the HP-83/85 Assembler ROM manual. The manual is available on the [www.series80.org](http://www.series80.org) web site.

*ncas* extends the machine instructions in the following way:

* Expressions can be used instead of labels as operands. The expressions are
  resized to two bytes. Expressions are not allowed as a destination of any
  relative jump or jump to subroutine instruction.
* Expressions can be used as elements of literal data lists. In this case, the
  expression must be sized!
* A *=* is needed before data literal data lists and labels
* Empty literal data lists are supported. Thus, the remaining data can be
  assembled into memory with ````DATA````. ````DEF```` or ````VAL````
  instructions. Incomplete literal data lists are always marked with a warning.
  You should only use this feature if you would like to save bytes:

              LDM  R40,=
      CALNAM  DATA "calcprog"


Specifying the ARP and DRP
--------------------------

Like *karma* there is an extension of the ````ARP```` and ````DRP```` instruction.

The instruction:

    ARP  !nn

or

    DRP  !nn

instructs the assembler that the current *ARP*/*DRP* is nn. This is a
replacement of the *R#* register specification and enables the assembler to
check *DRP* boundaries of subsequent machine instructions that use this register.

Example:

    ONES_EXE DRP !36       ; assures that data register is R36
             ERP R36       ; no DRP instruction is generated



Creation of Symbols
-------------------

Symbols can be created in several ways:

* As a statement label. Statement labels are always two bytes long
* An ````EQU```` statement. The symbol declared here has the same size as the 
  expression.
* An ````ADDR```` statement. This symbol is always two bytes long.

Note: ````ADDR```` and ````EQU```` allow expressions as operands. All symbols
must be resolved in the first pass of the assembly. Therefore, it is not allowed
to use forward references in these expressions.


Conditions
----------

The concept of a *condition* is used in the conditional branches machine
instructions and the pseudo operations for conditional returns, *IF-ELSE-ENDIFs*,
*LOOP-WHs*, and *EXs*.

The conditions which are implemented in machine instructions are documented in
the section *CONDITIONAL JUMP INSTRUCTION* of the HP83/85 ROM Assembler Manual.

Like *karma* the following condition aliases are supported

      EQ = ZR
      NE = NZ
      GE = PS
      LT = NG
      HS = CY
      LO = NC


Conditional Returns
-------------------

    R<condition>

There is no ROV pseudo operation. The assembler tries to generate a conditional
jump to a previous return statement. If no previous return statement exists
within an address range of -128 bytes a call to the next return statement is 
generated. If no next return statement exists within an address range of +127 
bytes an error is generated.

Example:

    LDM  R30,=INPBUF      ; decompile in INPBUF
    LDBD R67,=EDTYPE      ; how shall we decompile it
    JSB  =DECOPR          ; this will return with R17 tested for errors
    RNG                   ; abort if errors
    LDM  R26,=INPBUF      ; address of input buffer



Long Branch
-----------

The pseudo operation:

     GTO DEST

generates the same code as:

     LDM R4,=((DEST)-1).2

GTO can branch to any location. No expressions are allowed as operand.

Example:

    STBD R#,=(DIAG)+1     ; disable diagnostic slot
    STBD R#,=ROM3EN       ; enable the system rom
    GTO START?            ; now do warm or colstart stuff



ADDR pseudo-op
--------------

    <label>  ADDR  <expression>

Define \<label\> to have the value of the result of \<expression\>.  The size of 
\<label\> will be forced to two-bytes.  An error will be generated if the size 
of \<expression\> is greater than two bytes.

Note: Forward references are not allowed in \<expression\> because the result of
\<expression\> is resolved in the first pass of the assembly.

    <label> ADDR <expression>

is exactly equivalent to

    <label> EQU (<expression>).2

Example:

    BUFFER   ADDR 0EF0H
    BUFEND   ADDR (BUFEND)+96D

EQU pseudo-op
-------------

    <label> EQU <expression>

Define \<label\> to have the value of the result of \<expression\>.
The length of the value for \<label\> will be taken from the length of the 
result of the expression.

Note: Forward references are not allowed in \<expression\> because the result of
\<expression\> is resolved in the first pass of the assembly.

See also the ADDR pseudo-op.

Examples:

    WORKFILENAME   EQU 'WORKFILE'
    DEVICEFI1ENAME EQU 'DEVFILE '
    TRANS          EQU 'A'-'A'
    LCDSIZ         EQU 32D
    LCDSIZ         EQU (LCDMAX)-(LCDMIN)
    FILLER         EQU 0102030405060708#


END pseudo-op
-------------

The *END* pseudo operation indicates the logical end of the assembly. *END* is 
required.


INCLUDE pseudo-op
-----------------

    INCLUDE 'quoted string'

Include the given file into the program.  The *INCLUDE* instruction is printed in 
the program listing. Included files can be nested up to a level of 3.


ORG pseudo-op
-------------

    ORG <expression>

Sets the location counter to the address specified by \<expression>. Forward
references are not allowed in the expression. 

The result of the expression must be in the range of 0 to 0FFFFH.


ABS pseudo-op
-------------

    ABS

Indicates that the program shall be assembled as an absoulte program. This
pseudo-op must precede any other instruction that generates code including
the *ORG* pseudo-op.


BSS pseudo-op
-------------

     BSS <expression>

This pseudo operation generates a number of zero bytes determined by the result
of \<expression\>. Forward references are not allowed in \<expression\>.

To fill the remaining bytes of a ROM image do:

    ROMEND  EQU 07FFFH
            ...
            BSS (ROMEND)-($)+1
            END


TITLE pseudo-op
---------------

    TITLE 'quoted string'

The quoted string is printed in the header of each page in the list file.


IF-ELSE-ENDIF pseudo-ops
------------------------

    IF<condition>
    *
    * True case
    *
    ELSE
    * 
    * False case
    *
    ENDIF

or

    IF<condition>
    *
    * True case
    *
    ENDIF

The *IF-ELSE-ENDIF* pseudo-ops provide a structured means for conditional flow.

For example:

          CMBD R32,=STATUS ; test condition flag
          IFEQ             ; if equal status:
            DCE            ; decrement counter
          ELSE             ; otherwise
            ICE            ; increment counter
          ENDIF
      
Produces the same code as:

          CMBD R32,=STATUS ; test condition flag
          JNE  UNEQ        ; jump to unequal status
          DCE              ; decrement counter
          JMP  OUT         ; escape to common code
    UNEQ  ICE              ; increment counter
    OUT

The *ELSE* clause is optional. For example:

          TSB  R17         ; check error flag
          IFNZ             ; if we have an error
            CALL ABORT     ; destroy current pipe
          ENDIF

Produces the same code as:

          TSB  R17         ; check error flag
          JZR  OVER        ; skip if no error
          CALL ABORT       ; destroy current pipe
    OVER


      
LOOP-WH pseudo-ops
------------------

    LOOP
    *
    * body of loop
    *
    WH<condition>

The *LOOP-WH* pseudo-ops provide a structured means for expression looping
constructs. For example:

    * Wait for a key
            LOOP
              CALL KEY      ; do we have a key?
            WHEZ            : loop until E=1 from KEY

Produces the same code as:

    * Wait for a key
     LUPE   CALL KEY        ; do we have a key?
            JEZ LUPE        ; loop until E=1 from KEY


EX pseudo-ops
-------------

    IF<condition>

      EX<condition>

    ENDIF

or

    LOOP
     
      EX<condition>

    WH<condition>

The *EX* pseudo-ops allow the user to jump out of a surrounding *IF* or *LOOP* construct. For example:

    *
    * Loop until timeout, or a key is struck
    *
            LDM   R40,=COUNT     ; get timeout count
            LOOP
              JSB  KEY           ; interrupted yet?
              EXEZ               ; exit if e zero
              DCM  FR40          ; count down
            WHNZ                 ; continue if still counting

The *EXEZ* generates a *JEZ* past the end of the loop.

*EX* can also be used to escape from an *IF-ELSE-ENDIF* construct.


DATA pseudo-op
--------------

    DATA <data list>

*DATA* assembles data into memory. The \<data list\> is a comma separated list of any constants, equates, symbols and expressions containing them.

Note: an expression must always be sized if it contains an operand 
([see Data Lists](#data-lists)).


Conditional assembly pseudo-ops
-------------------------------

This set of pseudo-ops permits the user to control assembly by means of 
conditions. A conditional assembly flag has the same constraints as the
other symbols, but they do not share the same symbol table.

    .IFSET <symbol>

Tests the specified conditional assembly flag and, if true, continues
to assemble the following code. If the flag tests false, the
source code after the flag is treated as if it were a series of comments
until an *ELSE* or *ENDIF* instruction is found. Multiple conditional
assemblies can be nested.

If \<symbol\> does not exist, an error is thrown.

    .ELSE

The source code following this instruction is treated in the opposite way as
the corresponding *.IFSET* or *.IFDEF* conditional.

    .ENDIF

Terminates the conditional assembly in progress. 

    .IFDEF <symbol>

Tests if the specified conditional assembly flag does exist, e.g. was either
defined by a *.SET*, or *.CLR* pseudo-op or was set with the *-d* command line
option.
    
    .SET <symbol>

Sets the specified conditional assembly flag to the true state.

    .CLR <symbol>

Sets the specified conditional assembly flag to the false state.

The *IFNDEF* is the opposite of the *IFDEF* and the *IFNSET* is the opposite of 
the *IFSET* pseudo-op.


Other pseudo-ops
----------------

The following pseudo operations were implemented because they were frequently used
in program code written for the *karma* assembler:

       STE

This pseudo instruction generates a *CLE, ICE* machine instruction sequence. 

       NOP

This pseudo instruction generates a *TSB* machine instruction. If you would 
like to use the *real* NOP machine instruction (0o336) use *NOP1* instead.

       DEF <expression>

Generate the result of expression into the program code. The value is resized to two bytes. This is equivalent to:

       DATA (<expression>).2


       VAL <expression>

Generate the result of expression into the program code. The value is resized to one byte. This is equivalent to:

       DATA (<expression>).1


Examples
--------

The *ncas* subdirectory contains the file [example.asm](https://github.com/bug400/capasm/blob/master/ncas/example.asm) which is the example
ROM-based LEX file from *Appendix A* of the HP-75C *Description and Entry Points* Document. 

The [riowio.asm](https://github.com/bug400/capasm/blob/master/ncas/riowio.asm) 
which exists in the same directory shows how to create a lex file including 
the HP-75 RAM-header and the LIF-header without additional post-processing. This 
file includes the file [lexheader.inc](https://github.com/bug400/capasm/blob/master/ncas/lexheader.inc)
which provides a generic component to create lex files.
