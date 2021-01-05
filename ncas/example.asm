       abs
       org  6000H      ; Used only for ROM
******************************************************
*
*       A S S E N B L Y   I N F O R M A T I O N
*
* Note the careful use of upper and lower case here. I
* use uppercase to denote external  and global symbols
* and declared entry points.
*
******************************************************

tylex  equ 00001101B ; ROM, Purge, Copy, Token

******************************************************
*
*    File Directory (Used only for ROM LEX files)
*
******************************************************

       def RMHEAD                ; Yes, there is a ROM
       def lxstrt                ; Beginning of lefxile
       def (lxend)-(lxstrt)      ; Size of file
       val tylex
       val TYNLEX                ; LEX file in RAM
       data 90H,0B3H,0F3H,9AH    ; Date in sec since 1900
       data 'LEXEXAM '           ; File name
       def  0                    ; end of directory

*****************************************************
*
*       LEXEXAM Address Tables
* 
*****************************************************

lexid  equ 0100d             ; The id of this LEX fil
errnum equ 0150d             ; Starting error number

*****************************************************
*
*       L E X  F I L E  H E A D E R
* 
*****************************************************
base                         ; base 
rmbase  equ 0                ; remove 'equ 0' for ram
lxstrt
        def lexid               ; Number of this LEX fil
        def (runtab)-(rmbase)-2 ; Runtime table addr
        def (keywrd)-(rmbase)   ; Keyword table addr
        def (partab)-(rmbase)-2 ; Parse table addr
        def (errmsg)-(rmbase)   ; Error table addr
        def (intcpt)-(rmbase)   ; Intercept code addr

* Note that the addresses of the Runtime and Parse
* tables are offset by two. This is because the syste
* will ignore the first table entry in these tables

*****************************************************
*
*       R U N T I M E  T A B L E
* 
*****************************************************
runtab
        def (speak.)-(rmbase)   ; 1st keyword code addr
        def (error.)-(rmbase)   ; 

*****************************************************
*
*       P A R S E  T A B L E
* 
*****************************************************
partab
       def (speak#)-(rmbase)  ; Addr of parse-time co
       def (error#)-(rmbase)  ; 
       def RELMAR             ; Relocation marker

*   All items above RELMAR must be addresses only

*****************************************************
*
*       K E Y W O R D  T A B L E
* 
*****************************************************

keywrd
       data `SPEAK`            ; Invoking keyword #1
       data `ERROR`            ; Invoking keyword #2
       val  0ffh               ; End of keyword table

*****************************************************
*
*       E R R O R  M E S S A G E S
* 
*****************************************************

errmsg 
       val  errnum             ; 1st error msg nubmer
       data `sorry charlie!`   ; Error msg errnum 1
       data `malfunction malfunction!` ;

* Note that above is the largest displayable errmsg
       val  0ffH               ; End of error msgs

*****************************************************
*
*       C O D E  A T T R I B U T E S
* 
*****************************************************

       data 00011111B ; Ramable, ROMable, Pos idependent
                    ; Mergable, LEX ID idependent

*****************************************************
*
*        I N T E R C E P T  R O U T I N E
* 
*****************************************************

intcpt
       drp  !0
       cmb  r0,=V.WARM
       rne
       ldmd r36,=ROMPTR
       jsb  x36,(mesout)-(base)
       data 'Kangaroo at your service!'
       def   crlf!
       jsb  =UNSEE
       rtn

*****************************************************
*
*        P A R S E  R O U T I N E
* 
*****************************************************

speak#
       ldmd  r2,=ROMPTR
       jsb   x2,(prslex)-(base)
       jsb   =SFSCAN
       jmp   pushme            
*****************************************************
*
* Parse one keyword with one numeric parameter
*
*****************************************************
error#
       ldmd  r2,=ROMPTR
       jsb   x2,(prslex)-(base)
       jsb   =SYSJSB
       data   NUMVA+
pushme
       pomd  r54,-r6
       pumd  r54,+r12
       rtn

*****************************************************
*
* Pushes the LEX tokens onto R6 on entry
*
*****************************************************
prslex
       drp  !2
       pomd r2,-r6
       ldb  r55,=EROMTK
       ldm  r56,r41
       pumd r55,+r6
       pubd r14,+r6
       pumd r2,+r6
       rtn

*****************************************************
*
* 100 SPEAK  <cr>
*
* Output a silly message to all display devices
*
*****************************************************

        data  241
speak.  
        bin
        drp  !20
        ldmd r20,=ROMPTR
        jsb  x20,(mesout)-(base)
        data 'Arf! Arf!'
        def  crlf!
        jsb  =UNSEE
        rtn

******************************************************
*
* 100 ERROR <error number> <cr>
*
* Report the error specified after the keyword
*
******************************************************

       data 241
error.
       jsb  =ONEB
       ldb  r20,r76     
       jsb  =ERROR
       rtn

*****************************************************
*
* Output a message to display devices
*
*****************************************************

crlf!  equ  08a0dh   ; CRLF with terminator

mesout 
       pumd  r0,+r6
       pumd  r2,+r6
       pumd r30,+r6
       ldmd r30,x6,-8d
       pubd r32,+r6
       loop
         drp  !32
         pobd r32,+r30
         sad
         llb  r32
         lrb  r32
         jsb  =OUTCHR
         pad
       whps
       pobd r32,-r6
       stmd r30,x6,-8d
       pomd r30,-r6
       pomd r2,-r6
       pomd r0,-r6
       rtn
lxend
       end
