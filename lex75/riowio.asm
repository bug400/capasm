10 ! --------------------------
20 ! RIOWIO LEX file for HP 75
30 ! Recreated with HP 85
40 ! Martin Hepperle, 2016
50 ! --------------------------
60        LST                   ! create a listing
80 ! --------------------------
90        BYT 23, 100            ! 2 bytes LEX #
100 ! -------------------------
110        DEF RUNTIM           ! the 5 addresses
120        DEF ASCII 
130        DEF PARSE 
140        DEF ERRM
150        DEF INTCPT
160 ! -------------------------
170 RUNTIM BYT 0,0              ! first addr is skipped
180        DEF WIORUN
190        DEF RIORUN
200 ! -------------------------
210 PARSE  BYT 0,0              ! first addr is skipped
220        DEF WIOPAR
230        BYT 377,377          ! RELMAR
240 ! -------------------------
250 ASCII  ASP "WIO"            ! keyword  WIO PILREG,VAL
260        ASP "RIO"            ! function RIO(PILREG)
270 ! -------------------------
280 ERRM   BYT 377,377          ! first 377 ends KW table
290 !                            and is also first error #
300 !                            second 377 ends ERR table
310 ! -------------------------
320        BYT 101              ! rev. number "A" (optional)
330        BYT 27               ! 27 = 10111B
340                             ! code attribute bits
350 !                             0 RAMable
360 !                             1 ROMable
370 !                             2 position independent
380 !                            4 LEX# independent
390 INTCPT RTN                  ! no handling
400 ! -------------------------
410        BYT 241              ! attribute: statement
420 WIORUN BIN                  ! R12 has: byte, PIL-reg
430        LDMD R20 , =ROMPTR   ! for relative addressing
440        JSB =ONEB            ! get VAL to R46 and ...
450        STM R46 , R26        ! ... save in R26
460        JSB X20,SUB3         ! get register [0...7] to R46
470        STBD R26,X46,IOSTAT  ! store R26 to [IOSTAT+R46]
480        RTN 
490 ! -------------------------
500 WIOPAR LDM R2,R41           ! load LEX-ID to R2-R3 and ..
510        PUMD R2,+R6          ! .. push LEX# to R6 stack
520        JSB =SYSJSB          ! call system function to ..
530        DEF GET2N            ! .. get 2 numbers to R12 stack
540        LDB R54,=264         ! store "LEX" token in R54
550        POMD R2,-R6          ! recover LEX# to R2-R3 and ..
560        STM R2,R55           ! .. store LEX# in R55-R56
570        POBD R57,-R12        ! insert WIO token into R57
580        PUMD R54,+R12        ! push 4 bytes R54-R57
590        RTN 
600 ! -------------------------
610        BYT 20,55            ! attribute: function
620 RIORUN BIN 
630        LDMD R20,=ROMPTR     ! relative
640        JSB X20,SUB3         ! PIL register [0...7] to R46
650        CLM R36
660        LDBD R36,X46,IOSTAT  ! load R36 from [IOSTAT+R46]
670        JSB =PUINTG          ! push INT to R12 stack
680 EXIT   RTN 
690 ! -------------------------
700 SUB3   JSB =ONEB            ! get PIL register #
710        JNG ERR              ! err if R<0
720        CMM R46,=10,00       ! set carry if R>=8
730        JNC EXIT             ! O.K. R in [0...7] jump to RTN
740 ERR    JSB =ERROR+          ! show system error 131o=89d
750        BYT 131              ! 89 = "BAD PARAMETER"
760 ! -------------------------
770 ! ONEB   DAD 37213
780 ! PUINTG DAD 176344
790 ! IOSTAT DAD 177420
800 ! GET2N  DAD 11130
810 ! ERROR+ DAD 46231
820 ! SYSJSB DAD 43155
830 ! ROMPTR DAD 101243
840 ! -------------------------
850        FIN 
