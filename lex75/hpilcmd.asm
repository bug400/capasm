10 ! -------------------------
20 !
30 ! This creates a functional clone of the
40 ! HPILCMD LEX file for the HP 75.
50 ! It contains a fix for the "DA: not sent" bug.
60 !
70 ! This source can be assembled with the HP 85
80 ! assembler ROM.
90 ! Comments have been added with the help
100 ! of the I/O ROM source code.
110 !
120 ! Do not LOADBIN on HP 85, therefore:
130 !    ASSEMBLE "HPILCMDB",1
140 ! then
150 !    CHAIN "CVTLEX85"
160 ! to create a LEX file for the HP 75.
170 !
180 ! Martin Hepperle, December 2016
190 ! -------------------------
200        BYT 31,100           ! LEX-ID = 0x1940 = 6464d
210 ! -------------------------
220        DEF RUNTIM           ! address table
230        DEF ASCIIS           ! keywords
240        DEF PARSE            ! parse routines
250        DEF ERRMSG           ! error messages
260        DEF INTCPT           !
270 ! -------------------------
280 RUNTIM BYT 0,0              ! first addr is skipped
290        DEF SNDIO.           ! ... we could spare 2 bytes here
300        DEF ENTIO.           !     but we don't for didactic
310        DEF SEND?.           !     reasons.
320 ! -------------------------
330 PARSE  BYT 0,0              ! first addr is skipped
340        DEF PARSND           ! ... we could spare another 2 bytes
350        BYT 377,377          ! end of relocatable addresses
360 ! -------------------------
370 ASCIIS ASP "SENDIO"         ! keywords
380        ASP "ENTIO$"
390        ASP "SEND?"
400        BYT 377              ! end of table
410 ! -------------------------
420 ERRMSG BYT 226              ! first error message
430        ASP "device sent NRD"
440        BYT 377              ! end of table
450 ! -------------------------
460 ! a number conversion routine for binary or hex numbers
470 ! base is in R24 (e.g. 2 or 16)
480 ! converts alpha digit in R36 to binary
490 ! result is in R36 (0...15)
500 BINDGT JSB =ALFA#           ! uppercase character
510        SBB R36,=60          ! subtract '0'
520        JNG BADDGT           ! negative: character below '0'
530        CMB R36,=12          ! 10 = '9'
540        JNC DIGIT            ! it was a digit R36=0...9
550        CMB R36,=21          ! 17 = 'A'
560        JNC BADDGT           ! below 'A'
570        SBB R36,=7           ! subtract 7 so that 'A' becomes 10
580 DIGIT  CMB R#,R24           ! greater than base?
590        JCY BADDGT
600        CLE 
610        RTN 
620 !
630 BADDGT JSB =ERR1+ 
640        BYT 130              ! this is "bad statement"
650 !
660 ! a buffer allocation routine
670 ALLOC  LDM R56,=0,1         ! 000o,0010 = 400o = 256d
680        JSB =RSMEM-          ! allocate buffer of 256 bytes
690        RTN 
700 ! -------------------------
710 REV#   ASC "A"              ! revision number (optional)
720 ! -------------------------
730        BYT 27               ! attribute: 27o = 00010111b
740 !                                0 RAMable
750 !                                1 ROMable
760 !                                2 position independent
770 !                                4 LEX ID independent
780 INTCPT RTN                  ! no action
790 ! -------------------------
800 ! ENTIO$ runtime function
810        BYT 52,56            ! 52o = 0010.10.10: 2 pars (10=str, 10=str)
820 !                              ! 56o: string function
830 ! HP 75: on entry: ARP=DRP=20, R20=address of SNDIO.
840 ENTIO. BIN 
850 ! the original used SBM and STM to set R14 to the base ddress
860 !         SBM  R#,=ENTIO.       ! R# at entry is R20
870 !         STM  R#,R14           ! store base address in R14
880        LDMD R14,=ROMPTR     ! another way to load R14
890        CLB R20              ! and clear byte (R20 := 0)
900        JSB X14,ALLOC        ! allocate 256 byte buffer
910        JEN INTCPT           ! error: out
920        JSB X14,STSTND       ! STSTND standby on
930        PUMD R26,+R6         ! save R26
940        LDB R75,=100         ! default command  for ENTIO$ TAD
950        JSB X14,STRTIO       ! STRTIO send all commands in list
960        POMD R26,-R6         ! restore R26
970        JEN NULENT           ! error in commands
980        CLM R24              ! clear char count
990        ANM R56,=340,377     ! 340,377 returned frame
1000        LDMD R2,=TRKT+3     ! get frame from 0x8467
1010        CMM R2,=240,144     ! 240,144 send range? 0x64A0
1020        JCY NULENT          ! no  JNC
1030        CMM R2,=240,102     ! 240,102 send range? 0x42A0
1040        JNC NULENT          ! no
1050        CMM R2,R56          ! frame same as sent?
1060        JNZ HEXAND          ! no, enter string
1070        JMP NULENT
1080 NOTOK  JSB =ERROR          ! bad transmission
1090        BYT 71
1100 NULENT CLM R54
1110        PUMD R54,+R12
1120        RTN 
1130 ! -------------------------
1140 HEXAND STB R56,R3          ! save frame for END check
1150        CMM R56,=240,100    ! 240,100   ETO?
1160        JZR OKEND 
1170        CMM R56,=240,101    ! 240,101   ETE?
1180        JZR NOTOK 
1190        DRP R57             ! (inserted for binary compatibility)
1200        JSB X14,TOOBIG      ! check overflow and save char
1210        ANM R3,=100         ! isolate END bit
1220        CMB R3,=100         ! END bit set?
1230        JNZ T.002 
1240        LDBD R3,=SUBPNT
1250        JZR T.002 
1260        LDB R3,=15          ! get a CR
1270        JSB X14,TOOBIG      ! send it
1280        LDB R3,=12          ! get a LF
1290        JSB X14,TOOBIG      ! send it
1300 T.002  LDBD R77,=DNAME 
1310        JZR T.003 
1320        CMB R77,R57
1330        JNZ T.003 
1340        JSB X14,TOOBIG
1350        JMP T.004 
1360 T.003  JSB X14,DTASND      ! uses R26 stack?
1370        JMP HEXAND
1380 ! -------------------------
1390 TOOBIG SAD 
1400        ICM R24             ! R24-R25
1410        CMM R24,=0,1        !
1420        JCY CONTI           ! go on
1430        PAD 
1440        PUBD R#,+R26        ! push to R26 stack
1450        RTN 
1460 ! -------------------------
1470 CONTI  PAD 
1480        POMD R2,-R6
1490        PUBD R57,+R26       ! push to R26 stack
1500 T.004  PUMD R56,+R6        ! save R56
1510        LDM R56,=240,102    ! 240=101.00000 = RDY, 102=NRD
1520        JSB =RDYSND         ! send RDY frame (R56=3 ctrl bits, R57=8 bits)
1530        POMD R56,-R6        ! restore R56
1540        JSB X14,DTASND
1550        CMM R56,=240,100    ! 240,100
1560        JNZ NOTOK 
1570 OKEND  PUMD R24,+R12
1580        SBM R26,R24
1590        PUMD R26,+R12
1600        RTN 
1610 ! -------------------------
1620 DTASND JSB =MELJSB
1630        DEF DATSD-
1640        RTN 
1650 ! -------------------------
1660 ! set standby on  (see pg. 30(53) IO-ROM)
1670 STSTND CLM R2              ! clear for store
1680        STMD R2,=TRKT+5     ! clear TL+ and CL+
1690        STBD R2,=DNAME      ! clear IR: flag
1700        POMD R2,-R6         ! get RTN address
1710        LDM R0,=CLSTND      ! =CLSTND
1720        ADM R0,R14          ! make absolute address
1730        PUMD R0,+R6         ! put CLSTND as RTN on stack
1740        PUMD R2,+R6         ! put RTN back
1750        LDBD R2,=STAND?     ! get current standby
1760        STBD R2,=SUBP+1     ! save it
1770        LDB R3,=377         ! standby=ON ...
1780        JSB =STAND+         ! ... and turn on chip
1790 T.006  RTN 
1800 ! -------------------------
1810 CLSTND LDBD R2,=STAND?     ! get current standby status
1820        LDBD R3,=SUBP+1     ! get saved standby ...
1830        JSB =STAND+         ! ... and tell chip about it
1840        LDBD R2,=TRKT+5     ! TL+ CL+
1850        JZR T.005           ! no, TL+ was signified
1860        LDBD R3,=PLSTAT     ! get PLSTAT
1870        ANM R3,=24          ! 10100 any DISP or PRINTER devices active?
1880        JZR T.006           ! no: return w/o UNT, UNL
1890        JSB =UNTREP         ! else: untalk the talker
1900        RTN 
1910 ! -------------------------
1920 T.005  JSB =MELJSB         ! tell everybody
1930        DEF VFBYE           ! to shut up
1940 T.009  RTN 
1950 ! -------------------------
1960 T.008  LDB R24,=12         ! get base 10d
1970        TSM R36
1980        JZR T.011           ! zero
1990        POBD R36,+R34       ! pop character with a number
2000        JSB X14,BINDGT      ! call of BINDGT '0' -> 0
2010        JEN T.009           ! return
2020        LLB R36             ! * 2   ... multiply by 10
2030        STB R36,R37         ! save
2040        LLB R36             ! * 4
2050        LLB R36             ! * 8
2060        ADB R36,R37         ! *10  ... done
2070        STB R36,R37
2080 T.011  POBD R#,+R34
2090        JSB X14,BINDGT      ! call of BINDGT
2100        JEN T.009           ! return
2110        ADB R36,R37         ! add to accum
2120        CMB R36,=40         ! space char.
2130        JNC T.009           ! return
2140        JSB =ERR1+          ! raise error 131o
2150        BYT 131             ! bad parameter
2160 ! -------------------------
2170 ! All tables are composed of 3-character key words
2180 ! followed by byte which contains data or control bits,
2190 ! depending on table type.
2200 ! The end of each table is indicated by four null bytes.
2210 !
2220 ! first table: various CMD
2230 CMDTBL ASC "DCL"           ! device clear
2240        BYT 24              ! 20d
2250        ASC "EDN"           ! enble device not ready for data
2260        BYT 17              ! 15d
2270        ASC "IFC"           ! interface clear
2280        BYT 220             ! 144d
2290        ASC "NOP"           ! non-operable commsnd
2300        BYT 20              ! 16d
2310        ASC "REN"           ! remote enable
2320        BYT 222             ! 146d
2330        ASC "SDC"           ! selected device clear
2340        BYT 4               ! 4
2350        ASC "UNL"           ! unlisten
2360        BYT 77              ! 63d
2370        ASC "UNT"           ! untalk
2380        BYT 137             ! 95d
2390        ASC "GET"           ! group execute trigger
2400        BYT 10              ! 8d
2410        ASC "GTL"           ! goto local
2420        BYT 1               ! 1d
2430        ASC "LLO"           ! local lockout
2440        BYT 21              ! 17d
2450        ASC "LPD"           ! loop power down
2460        BYT 233             ! 155d
2470        ASC "AAU"           ! auto address unconfigure
2480        BYT 232             ! 154d
2490        ASC "NRE"           ! not remote enable
2500        BYT 223             ! 147d
2510        ASC "PPD"           ! parallel poll disable
2520        BYT 5               ! 5d
2530        ASC "PPU"           ! parallel poll unconfigure
2540        BYT 25              ! 21d
2550        BYT 0,0,0,0         ! end*of*table
2560 !
2570 ! second table:
2580        ASC "DDL"           ! device dependent listen command
2590        BYT 240             ! 160d DDL 0 ... DDL 30
2600        ASC "DDT"           ! device dependent talk command
2610        BYT 300             ! 192d DDT 0 ... DDT 30
2620        ASC "PPE"           ! parallel poll enable
2630        BYT 200             ! 128d PPE 0 ... PPE 30
2640        ASC "SAD"           ! secondary address
2650        BYT 140             ! 96d SAD 0 ... SAD 30
2660        BYT 0,0,0,0         ! end*of*table
2670 !
2680 ! third table: CMD
2690        ASC "LAD"           ! listener address
2700        BYT 40              ! 32d LAD 0 ... LAD 30
2710        ASC "TAD"           ! talker address
2720        BYT 100             ! 64d TAD 0 ... TAD 30
2730        BYT 0,0,0,0         ! end*of*table
2740 !
2750 ! fourth table: RDY frames
2760        ASC "NRD"           ! not ready for data
2770        BYT 102             ! 66d
2780        ASC "SDA"           ! send data
2790        BYT 140             ! 96d
2800        ASC "SST"           ! send status
2810        BYT 141             ! 97d
2820        ASC "SDI"           ! send device id
2830        BYT 142             ! 98d
2840        ASC "SAI"           ! send accessory id
2850        BYT 143             ! 99d
2860        ASC "TCT"           ! take control
2870        BYT 144             ! 100d
2880        ASC "IEP"           ! illegal ext primary
2890        BYT 277             ! 191d
2900        ASC "IES"           ! illegal ext secondary
2910        BYT 337             ! 223d
2920        ASC "IAA"           ! illegal auto address
2930        BYT 237             ! 159d
2940        ASC "IMP"           ! illegal multiple primary
2950        BYT 377             ! 255d
2960        ASC "ZES"           ! zero extended secondary
2970        BYT 300             ! 193d
2980        BYT 0,0,0,0         ! end*of*table
2990 !
3000 ! fifth table: control bit masks
3010        ASC "RD:"           ! ready class control bits
3020        BYT 240             ! RDY  101.00000
3030        ASC "CD:"           ! command class control bits
3040        BYT 200             ! CMD  100.00000
3050        ASC "ID:"           ! identify class control bits
3060        BYT 300             ! IDY  110.00000
3070        ASC "DA:"           ! data class control bits
3080 !         BYT  0               ! DATA 000.00000 (Bug:"0" is same as TR:)
3090        BYT 20              ! DATA 000.10000 (Fix by MH: "20" replace "0"
3100 !                            ! bits 1-4 will be ignored by PIL reg 1)
3110        ASC "EN:"           ! data END control bits
3120        BYT 100             !      010.00000
3130        ASC "IS:"           ! identify SRQ bits
3140        BYT 340             !      111.00000
3150        ASC "DS:"           ! data SRQ control bits
3160        BYT 40              !      001.00000
3170        ASC "ES:"           ! data END SRQ control bits
3180        BYT 140             !      011.00000
3190        ASC "TR:"           ! terminator
3200        BYT 0
3210        BYT 0,0,0,0         ! end*of*table
3220 !
3230 ! sixth table:
3240        ASC "TL+"
3250        BYT 1
3260        ASC "CL+"
3270        BYT 2
3280        BYT 0,0,0,0         ! end*of*table
3290 !
3300 ! seventh table: RDY messages, upper
3310        ASC "AAD"           ! auto address
3320        BYT 200             ! 128d AAD 0 ... AAD 30
3330        ASC "AEP"           ! auto ext primary
3340        BYT 240             ! 160d AEP 0 ... AEP 30
3350        ASC "AES"           ! auto ext secondary
3360        BYT 300             ! 192d AES 0 ... AES 30
3370        ASC "AMP"           ! auto multiple primary
3380        BYT 340             ! 224d AMP 0 ... AMP 30
3390        BYT 0,0,0,0         ! end*of*table
3400 ! -------------------------
3410 ! RUNTIME routine
3420        BYT 241
3430 ! -------------------------
3440 ! HP 75: on entry: ARP=DRP=20, R20=address of SNDIO.
3450 SNDIO. BIN                 ! leave BCD
3460 !         SBM  R#,=SNDIO.       ! R#=R20
3470 !         STM  R#,R14           ! store base address in R14
3480        LDMD R14,=ROMPTR    ! preferred way to set R14
3490        JSB X14,STSTND      ! set standby on
3500        LDB R20,=1          ! flags
3510        LDB R75,=40         ! default command is LAD
3520        JSB X14,STRTIO      ! STRTIO send commands in list
3530        CLM R34             ! clear for flags
3540        STMD R34,=BSEADR    ! clear # of bytes sent count
3550        POMD R34,-R6        ! get data location
3560        STM R34,R36         ! save pointer
3570        POMD R32,-R6        ! get DATA length
3580        JEN DONE            ! error: give up
3590        JZR DONE            ! loop done?
3600 ! loop
3610 SNDLOP POBD R57,+R34       ! get a data frame
3620        JSB =DATREP         ! send it DATREP
3630        JEZ T.012           ! error: give up
3640        DCE 
3650        JEN DONE  
3660        ANM R56,=340,377    ! 340,377 isolate control bits
3670        CMM R56,=240,102    ! 240,102 0x42A0
3680        JNZ DONE  
3690        JSB =RDYSND         ! send RDY frame (R56-R57)
3700        JEN DONE  
3710        ANM R56,=CMPSB 
3720        CLM R2
3730        POBD R2,-R34
3740        CMM R2,R56
3750        JNZ DONE  
3760        SBM R34,R36
3770        ICM R34             ! increment byte count
3780        STMD R34,=BSEADR    ! update # of bytes for SEND?
3790        JSB =CLRERR         ! clear any errors
3800        JSB =WARN           ! WARN eats its following byte
3810        BYT 226             ! warning 226: "device sent NRD"
3820        JMP APROP+
3830 T.012  DCM R32
3840        JNZ SNDLOP          ! send loop
3850 !
3860 APROP+ LDM R56,=240,100    ! 101.00000, 01000000
3870        JSB =RDYSND         ! send RDY frame (R56-R57)
3880 DONE   RTN 
3890 ! -------------------------
3900 ! send all commands in list
3910 STRTIO POMD R76,-R6
3920        STMD R75,=TRKTBL
3930 T.015  JSB =GETADR
3940        POMD R32,-R12
3950        LDM R44,R32
3960        PUMD R44,+R6
3970        DCB R20
3980        JPS T.015 
3990        CLE 
4000        POMD R20,-R12
4010        POMD R20,-R12
4020        JZR T.016 
4030        ADM R12,=4,0
4040        JSB =MELJSB
4050        DEF FLSTAK
4060        JEN T.051 
4070        LDM R32,=2,0
4080        CMB R66,=40         ! space?
4090        JZR T.017 
4100        ICM R32
4110        CMB R67,=40         ! space?
4120        JZR T.018 
4130        ICM R32
4140 T.018  LDM R34,=TMPMM2
4150        STMD R64,R34
4160        JMP T.019 
4170 T.017  LDM R#,R64
4180 T.019  PUMD R14,+R6        ! save base address
4190        JSB =GETPAD
4200        POMD R14,-R6        ! restore base address
4210        JEZ T.016 
4220 T.051  JSB =ERR1  
4230        BYT 77              ! invalid filespec
4240 T.016  POMD R26,-R6
4250        POMD R22,-R6
4260        JEN T.020 
4270        JNZ T.021 
4280        LDBD R57,=TRKTBL
4290        TSM R20
4300        JNZ T.022 
4310        CMB R57,=40         ! space?
4320        JZR T.023 
4330        JSB =ERR1  
4340        BYT 77              ! invalid filespec
4350 T.023  JMP T.024 
4360 T.022  LDB R36,R20
4370        JSB X14,SNDTDA
4380        JEN T.020 
4390        LDBD R57,=TRKTBL
4400        CMB R57,=100        ! 100.0000b
4410        JNZ T.024 
4420        LDB R57,=140        ! 110.0000b
4430        JSB X14,SNDRDY
4440 T.024  JMP T.020 
4450 T.021  PUBD R20,+R#
4460 T.052  POMD R45,+R26       ! UPRC* uses 377-375+1 = 3 bytes
4470        LDM R0,=045,375     ! setup for UPRC*: R45, 3 bytes
4480        JSB =UPRC*          ! convert R45-R47 to upper case
4490        JSB X14,CMDSCH      ! call CMDSCH
4500        JEN T.025 
4510        SBM R22,=3,0        ! 003,000
4520        JZR T.025 
4530        POBD R20,+R26
4540        CMB R20,=54
4550        JNZ T.026 
4560        DCM R22
4570        JZR T.026 
4580        JPS T.052 
4590 T.026  JSB =ERR1  
4600        BYT 131             ! bad parameter
4610 T.025  POBD R20,-R6
4620        JSB =PILREP
4630 T.020  LDMD R2,=TRKT+1     ! 0x8465
4640        PUMD R2,+R6
4650 T.RTN  RTN 
4660 ! -------------------------
4670 ! search through one PIL command table
4680 ! R45-R47 has the 3 character command to look up
4690 SEARCH CLE 
4700 SLOOP  POMD R54,+R30       ! 4 bytes: R54-R56: cmd name, R57: frame data
4710        JZR T.RTN           ! at end of table?
4720        CMM R45,R54         ! compare 3 bytes
4730        JNZ SLOOP 
4740        ICE                 ! found, R57 has frame bits
4750 T.036  RTN 
4760 ! -------------------------
4770 ! CMDSCH: search for 3-byte command string in R45-R47
4780 CMDSCH LDM R30,=CMDTBL     ! load address of table
4790        ADM R30,R14         ! make absolute (add base address)
4800        JSB X14,SEARCH      ! table 1
4810        JEN SNDCMD          ! found: do it
4820        JSB X14,SEARCH      ! table 2
4830        JEN GETNUM          ! found: get number
4840        JSB X14,SEARCH      ! table 3
4850        JEN SNDTAD          ! found: do it LAD/TAD
4860        JSB X14,SEARCH      ! table 4
4870        JEN SNDRDY          ! found: do it
4880        JSB X14,SEARCH      ! table 5
4890        JEN GENPIL          ! found: do it
4900        JSB X14,SEARCH      ! table 6
4910        JEN TL+             ! found: do it
4920        JSB X14,SEARCH      ! table 7
4930        JEZ INVPCM          ! found: do it
4940        JSB X14,NUMBER
4950        JEN T.036 
4960        ADB R57,R36
4970        JSB X14,SNDRDY
4980        DCE                 ! was FRNS set?
4990        JEZ T.036           ! FRNS was set, so return, okay
5000        ICE                 ! error: recover E
5010        RTN 
5020 ! -------------------------
5030 SNDRDY LDB R56,=240        ! set up 3 ctl bits for RDY frame
5040        STMD R56,=TRKT+3    ! save the frame
5050        JSB =RDYSND         ! send RDY frame (R56-R57)
5060        RTN 
5070 ! -------------------------
5080 TL+    STB R57,R56         ! save the value
5090        CLB R57             ! clear for add
5100        ADM R56,=150,204    ! 150,204 if 1 (CL+): store in TMPMM3+5
5110 !                                if 2 (CL+): store in TMPMM3+6
5120        STBD R56,R56        ! store approp.
5130 BACK.3 CLE                 ! clear errors
5140        LDMD R56,=TRKT+3    ! get last valid frame
5150 T.050  RTN 
5160 ! -------------------------
5170 SNDTAD POBD R20,+R26       ! get next char from R26 ptr
5180        CMB R20,=43         ! compare with '#', is this LAD# or TAD#?
5190        JNZ LTAD.N          ! NO, must be LADn or TADn
5200 !
5210 ! LAD# or TAD#                 convert # to HP-IL address
5220        DCM R22             ! dec string count
5230        POMD R20,-R6        ! get rtn addr
5240        POBD R36,-R6        ! get target device number
5250        PUBD R36,+R6        ! put target device number back
5260        PUMD R20,+R6        ! put rtn addr back
5270        TSB R36             ! test for no device
5280        JNZ LTAD.#          ! O.K., number in R36
5290        JSB =ERR1+          ! TAD# or LAD# w/o device number
5300        BYT 77              ! invalid filespec
5310 !
5320 LTAD.# JMP SNDTDA          ! send it
5330 ! -------------------------
5340 LTAD.N DCM R26             ! no '#': set R26 ptr back to the number
5350 GETNUM JSB X14,NUMBER      ! convert NUMBER to R36
5360        JEN T.050           ! oops, no number, return
5370 !
5380 SNDTDA ADB R57,R36         ! add target address to frame data
5390 SNDCMD LDB R56,=200        ! this is a CMD frame
5400        STMD R56,=TRKT+3    ! save frame
5410        JSB =CMDREP         ! finally: send CMD frame
5420 T.040  RTN 
5430 ! -------------------------
5440 INVPCM JSB =ERR1+ 
5450        BYT 130             ! bad statement
5460 ! -------------------------
5470 GENPIL POMD R20,+R26       ! get HEX value for frame
5480        DCM R22             ! decrement command count by 2
5490        DCM R22
5500        JNG INVPCM          ! neg: bad PIL command error
5510        JSB X14,HEXBIN      ! convert ASCII HEX to binary
5520        JEN T.040           ! error: return
5530        STB R57,R56         ! save byte value in R56
5540        JNZ NOTRM           ! jump if this is no TR: terminator
5550 !  Bug: also ended up here if DA: was found. This also had "0" in table.
5560 !       This is fixed now.
5570        STBD R20,=DNAME     ! temporarily store terminator byte
5580        JMP BACK.3          ! jump out
5590 !
5600 ! Note: V2 of HPILCMD seems to replace the line:
5610 ! 003 242       STB R#,R03    - note DRP is R#, i.e. left
5620 ! with                        - as it currently is
5630 ! 003 120 242   STB R20,R03   - here R20 is explicitely set
5640 ! which inserts the byte 120 between 003 and 242
5650 ! This adds a DRP R20, equivalent to replacing R# with R20.
5660 ! The previous version might have a wrong DRP when
5670 ! jumping from above to NOTRM. But this does not happen.
5680 !
5690 NOTRM  STB R#,R3           ! save flag in R57 (R#) to R3
5700        LDB R#,R20          ! load value into R57 (R#)
5710        ANM R3,=300         ! AND out any garbage 1100.0000
5720        CMB R3,=200         ! compare to CMD frame
5730        JNZ SET.TA          ! I am the Talker
5740        LDB R55,=120        ! set LA bit in PIL R0 ...
5750        JMP SETDON          ! ... and skip
5760 SET.TA LDB R55,=140        ! set TA bit in PIL R0
5770 SETDON STMD R56,=TRKT+3    ! save frame (R56-R57) for SNDFRM
5780 !
5790        CMM R56,=200,030    ! 200,030 trap EAR: commented out in I/O ROM?
5800        JZR T.040           ! trap EAR: commented out in I/O ROM?
5810 !
5820        JSB =SNDFRM         ! set PILR0=R55, send frame (R56-R57)
5830        RTN 
5840 ! -------------------------
5850 ! R26 points to a string with a number
5860 ! R20:     digit
5870 ! R22: command count
5880 ! R26-R27: pointer to string
5890 NUMBER CLM R36
5900        LDM R34,R26         ! save pointer in R34-R35
5910        POBD R20,+R26       ! get first digit (we hope)
5920        JSB =DIGIT          ! has R20 it a digit?
5930        JEZ INVPCM          ! error
5940        DCM R22             ! decrement command count
5950        JNG INVPCM          ! error
5960        POBD R20,+R26       ! get second digit (we hope)
5970        JSB =DIGIT          ! has R20 a digit?
5980        JEN T.045 
5990        DCM R26             ! decrement string ptr
6000        JMP T.046 
6010 T.045  DCM R22             ! decrement command count
6020        JNG INVPCM          ! error
6030        ICM R36             ! R36=1
6040 T.046  JSB X14,T.008       ! get number in binary to R36
6050 T.047  RTN 
6060 ! -------------------------
6070 ! convert a two digit ASCII HEX number to binary
6080 ! input is in R20-21
6090 ! result is returned in R20
6100 HEXBIN LDB R24,=20         ! BINDGT wants the base in R24.
6110 !                              ! We use 16d for HEX to binary
6120        LDB R36,R20         ! get first (left) digit from
6130        JSB X14,BINDGT      ! convert to binary 0...15 => R36
6140        JEN T.047           ! oops?
6150        LLB R36             ! *  2 MSB: multiply by 16
6160        LLB R36             ! *  4
6170        LLB R36             ! *  8
6180        LLB R36             ! * 16
6190        STB R36,R20         ! save in R20
6200        LDB R36,R21         ! get second (right) digit
6210        JSB X14,BINDGT      ! convert to binary and ...
6220        ADB R20,R36         ! ... add to result
6230        RTN 
6240 ! parse routine for SENDIO    R14 has input token # for "SENDIO"
6250 PARSND LDB R2,=264         ! external ROM token
6260        PUBD R2,+R6         ! (264 == EROMTK) to R6 stack         (1 byte)
6270        LDM R2,R41          ! R41-R42 = LEX ID
6280        PUMD R2,+R6         ! LEX ID to R6 stack                  (2 bytes)
6290        PUBD R14,+R6        ! current token# (SENDIO) to R6 stack (1 byte)
6300        JSB =SYSJSB         ! R6 stack: 4 bytes:
6310 !                          ! [EROMTK,LEXID0,LEXID1,TOKEN#]
6320        DEF GETSTP          ! get 3rd string + comma, save input tok in R36
6330        JZR T.048 
6340 T.049  POMD R44,-R6        ! drop R44-R47: clean up R6 stack
6350        JSB =ERR1+ 
6360        BYT 121             ! comma expected
6370 !
6380 T.048  LDB R14,R36         ! restore input token from R36
6390        JSB =SYSJSB
6400        DEF GETSTP          ! get 2nd string + comma, save input tok in R36
6410        JNZ T.049           ! error: no comma
6420        LDB R14,R36         ! restore input token from R36
6430        JSB =SYSJSB         ! get 1st string
6440        DEF GET1$           ! leaves 1 byte (string token) on R12 stack
6450        POBD R54,-R12       ! drop string token, we don't need it
6460        BYT 154             ! DRP 54 (not needed but in original)
6470        POMD R#,-R6         ! pop the 4 bytes of tokens to R54-R57
6480        PUMD R#,+R12        ! and push them to R12 stack
6490        RTN 
6500 ! -------------------------
6510 ! SEND? runtime function
6520        BYT 0,55            ! 55: numeric, 0: no arguments
6530 SEND?. LDMD R36,=BSEADR    ! retrieve # of bytes sent by previous SENDIO
6540        JSB =PUINTG         ! convert binary to real
6550        RTN 
6560 ! -------------------------
6570 ALFA#  DAD 7003            ! SYSROM0
6580 GET1$  DAD 11216           ! SYSROM0
6590 GETSTP DAD 11226           ! SYSROM0
6600 UPRC*  DAD 15465           ! SYSROM0
6610 GETADR DAD 17421           ! SYSROM0
6620 RSMEM- DAD 22037           ! SYSROM1
6630 SYSJSB DAD 43155           ! SYSROM2
6640 MELJSB DAD 43141           ! SYSROM2
6650 CLRERR DAD 45702           ! SYSROM2
6660 WARN   DAD 45723           ! SYSROM2
6670 ERROR  DAD 46221           ! SYSROM2
6680 ERR1   DAD 46244           ! SYSROM2
6690 ERR1+  DAD 46254           ! SYSROM2
6700 GETPAD DAD 56560           ! SYSROM2
6710 PILREP DAD 42745           ! SYSROM2
6720 RDYSND DAD 165430          ! BASROM
6730 SNDFRM DAD 165433          ! BASROM
6740 UNTREP DAD 166012          ! BASROM
6750 CMDREP DAD 166037          ! BASROM
6760 DATREP DAD 166044          ! BASROM
6770 PUINTG DAD 176344          ! BASROM
6780 STAND+ DAD 165337          ! BASROM
6790 FLSTAK DAD 64072           ! MELROM, called by MELJSB
6800 VFBYE  DAD 66655           ! MELROM, called by MELJSB
6810 DATSD- DAD 70012           ! MELROM, called by MELJSB
6820 BSEADR DAD 101236          ! ROM file base address (used for SEND? data)
6830 ROMPTR DAD 101243          ! contains LEX file base addr.
6840 STAND? DAD 101663          ! S.ON HPIL info: 7=no timeout, 0=leave osc. on
6850 TRKTBL DAD 102144          ! track-load table #1
6860 TRKT+1 DAD 102145          ! track-load table #1 +1
6870 TRKT+3 DAD 102147          ! track-load table #1 +3
6880 TRKT+5 DAD 102151          ! track-load table #1 +5
6890 DNAME  DAD 102154          !
6900 TMPMM2 DAD 101015          ! dedicated temp memory (38 bytes)
6910 CMPSB  DAD 177600          ! comparator status byte
6920 PLSTAT DAD 101275          ! BIT: 7=HANDI, 6=PPC, 5=OFFIO,
6930 !                          ! BIT: 4=DI.., 3=Dx active, 2=PR
6940 SUBPNT DAD 102152          ! return-stack mark #1
6950 SUBP+1 DAD 102153          ! return-stack mark #1 +1
6960 ! -------------------------ren
6970        FIN 
6980 ! -------------------------
