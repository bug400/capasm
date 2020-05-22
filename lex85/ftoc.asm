        LST
!****************************
!*     FTOC BINARY          *
!* (c) Hewlett-Packard Co.  *
!*        1980              *
!****************************
!       GLO GLOBAL    this is not supported on CAPASM
        NAM FTOC
!****************************
!System Tables:
        DEF RUNTIM
        DEF ASCIIS
        DEF PARSE
        DEF ERMSG
        DEF INIT
!****************************
!Parse Routine Table
PARSE   BYT 0,0
!****************************
!Runtime Routine
RUNTIM  BYT 0,0
        DEF FTOC.
        BYT 377,377
!****************************
!ASCII Table
ASCIIS  BSZ  0
        ASP "FTOC"
        BYT 377
!****************************
!Error Message Table
ERMSG   BSZ 0
        BYT 377
!****************************
!Initialization Routine:
INIT    BSZ 0
        RTN
!****************************
!Runtime Routines:
        BYT 20,55            !Attributes for FTOC.
FTOC.   BSZ 0                !Begin runtime routine.
        BIN                  !Sets BIN mode for ONER routine.
        JSB =ONER            !Load F into R40.
        LDM R50,R40          !Move F into R50.
        LDM R40,=1,0,0,0,0,0,0,32C !Load 32 into R40.
        JSB =SUB10           !Perform subtraction.
        POMD R70,-R12        !Throw away copy on stack.
        LDM R50,=0,0,0,0,0,0,0,50C !Load 50 into R50
        JSB =MPY10           !Perform multiplication.
        POMD R70,-R12        !Throw away copy on stack.
        LDM R50,R40          !Move intermediate result to R50
        LDM R40,=0,0,0,0,0,0,0,90C !Load 90 into R40.
        JSB =DIV10           !Perform division
        RTN                  !Answer is on stack, so return
        FIN
