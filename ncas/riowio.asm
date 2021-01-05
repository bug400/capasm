*
*   RIOWIO LEX file for HP 75
*   Recreated with HP 85
*   Martin Hepperle, 2016
*
*   ncas assembler version
*   Joachim Siebold, 2021
* 

LEXFILE_ID     EQU  4013H       ; lex file id
LEXFILE_NAME   EQU  "RIOWIO  "  ; always 8 characters filled with blanks
       INCLUDE  'lexheader.inc'
*
* LEX file header
*
       ORG   0                  ; force relative addr to zero (=ROMPTR)
RMBASE
LXSTART
       DEF  LEXFILE_ID          ; lex file id
       DEF (RUNTAB)-(RMBASE)-2  ; runtime table address
       DEF (KEYWRD)-(RMBASE)    ; keyword table address
       DEF (PARTAB)-(RMBASE)-2  ; parse table address
       DEF (ERRMSG)-(RMBASE)    ; error table address
       DEF (INTCPT)-(RMBASE)    ; intercept code address
*
* runtime table
*
RUNTAB
       DEF (WIORUN)-(RMBASE)    ; 1st keyword code addr
       DEF (RIORUN)-(RMBASE)    ; 2nd keyword code addr
*
* parse table
*
PARTAB
       DEF (WIOPAR)-(RMBASE)    ; addr of parse-time code
       DEF RELMAR               ; relocation marker
*
* keyword table
*
KEYWRD
       DATA `WIO`           ; keyword  WIO PILREG,VAL
       DATA `RIO`           ; function RIO(PILREG)
ERRMSG VAL  0FFH            ; end of keyword table
*
* error messages
*
       VAL  0FFH            ; empty error table

       DATA 'A'             ; rev. number "A" (optional)
*
* code attributes
*
       DATA 27              ; 27 = 10111B
                            ; code attribute bits
                            ; 0 RAMable
                            ; 1 ROMable
                            ; 2 position independent
                            ; 4 LEX# independent
*
* intercept code
*
INTCPT RTN                  ; no handling
*
* WIO command implementation
*
       DATA 241             ; attribute: statement
WIORUN BIN                  ; R12 has: byte, PIL-reg
       LDMD R20 , =ROMPTR   ; for relative addressing
       JSB =ONEB            ; get VAL to R46 and ...
       STM R46 , R26        ; ... save in R26
       JSB X20,SUB3         ; get register [0...7] to R46
       STBD R26,X46,IOSTAT  ; store R26 to [IOSTAT+R46]
       RTN 
*
* parse implementation
*
WIOPAR LDM R2,R41           ; load LEX-ID to R2-R3 and ..
       PUMD R2,+R6          ; .. push LEX# to R6 stack
       JSB =SYSJSB          ; call system function to ..
       DEF GET2N            ; .. get 2 numbers to R12 stack
       LDB R54,=264         ; store "LEX" token in R54
       POMD R2,-R6          ; recover LEX# to R2-R3 and ..
       STM R2,R55           ; .. store LEX# in R55-R56
       POBD R57,-R12        ; insert WIO token into R57
       PUMD R54,+R12        ; push 4 bytes R54-R57
       RTN 
*
* RIO command implementation
*
       DATA 20,55           ; attribute: function
RIORUN BIN 
       LDMD R20,=ROMPTR     ; relative
       JSB X20,SUB3         ; PIL register [0...7] to R46
       CLM R36
       LDBD R36,X46,IOSTAT  ; load R36 from [IOSTAT+R46]
       JSB =PUINTG          ; push INT to R12 stack
       RTN 

SUB3   JSB =ONEB            ; get PIL register #
       JNG ERR              ; err if R<0
       CMM R46,=10,00       ; set carry if R>=8
       RNC                  ; O.K. R in [0...7] jump to RTN
ERR    JSB =ERROR+          ; show system error 131o=89d
       DATA 131             ; 89 = "BAD PARAMETER"
LXEND  END
