10        LST 
20 ! -------------------------
30 ! HP 75 LEX File
40 ! ASTORE "PHYCONS75S"
50 ! ASSEMBLE "PHYCONS75B",1
60 ! -------------------------
70        BYT 62,2              ! HP 75 specific (LEX #instead of NAM)
80 ! -------------------------
90        DEF RUNTIM            ! tables
100        DEF ASCIIS
110        DEF PARSE 
120        DEF ERRMSG
130        DEF INTCPT           ! HP 75 specific (intercept function)
140 ! -------------------------
150 PARSE  BYT 0,0
160 RUNTIM BYT 0,0              ! RUNTIM table
170        DEF UNIT$ 
180        DEF VLITE 
190        DEF CHARGE
200        DEF PLANCK
210        DEF ELMASS
220        DEF AVGDRO
230        DEF MOLRGC
240        DEF BOLTK 
250        DEF GRAVK 
260        DEF MOLVOL
270        DEF FARADK
280        DEF RYDBRK
290        DEF FINSTK
300        DEF ELRAD 
310        DEF BOHRAD
320        DEF MAGFLX
330        DEF ATMASS
340        DEF PRMASS
350        DEF NTMASS
360        DEF ELGK  
370        DEF BOHRMG
380        DEF NUCLMG
390        DEF ELMAG 
400        DEF PRMAG 
410        DEF PRGYMR
420        DEF GRACCL
430        BYT 377,377
440 ! -------------------------
450 ASCIIS ASP "UNIT$"
460        ASP "VLITE"
470        ASP "CHARGE"
480        ASP "PLANCK"
490        ASP "ELMASS"
500        ASP "AVGDRO"
510        ASP "MOLRGC"
520        ASP "BOLTK"
530        ASP "GRAVK"
540        ASP "MOLVOL"
550        ASP "FARADK"
560        ASP "RYDBRK"
570        ASP "FINSTK"
580        ASP "ELRAD"
590        ASP "BOHRAD"
600        ASP "MAGFLX"
610        ASP "ATMASS"
620        ASP "PRMASS"
630        ASP "NTMASS"
640        ASP "ELGK"
650        ASP "BOHRMG"
660        ASP "NUCLMG"
670        ASP "ELMAG"
680        ASP "PRMAG"
690        ASP "PRGYMR"
700        ASP "GRACCL"
710        BYT 377              ! end of table
720 ! -------------------------
730 ERRMSG BYT 377
740 ! -------------------------
750        BYT 15               ! HP 75 specific (LEX attribute)
760 INTCPT RTN 
770 ! -------------------------
780 ! runtime functions start here
790 ! -------------------------
800        BYT 0,56             ! function, return a string
810 UNIT$  LDM R56,=2,0
820        JSB =RSMEM-
830        PUMD R56,+R12        ! length
840        PUMD R26,+R12        ! address
850        LDM R20,=123,111     ! 123,111 = 83 73 = "SI"
860        PUMD R20,+R26        ! store
870        RTN 
880 !
890 ! table with up to 256 constants
900 ! 8 bytes float format
910 !
920 TABLE  BYT 10,0,0,200,105,222,227,51 ! 0 VLITE
930        BYT 201,220,0,0,222,30,2,26 ! 1 CHARGE
940        BYT 146,220,0,0,140,27,46,146 ! 2 PLANCK
950        BYT 151,220,0,0,100,123,11,221 ! 3 ELMASS
960        BYT 43,0,0,0,120,4,42,0 ! 4 AVGDRO
970        BYT 0,0,0,0,0,101,24,203 ! 5 MOLRGC
980        BYT 167,220,0,0,40,146,200,23 ! 6 BOLTK
990        BYT 211,220,0,0,0,0,162,146 ! 7 GRAVK
1000        BYT 230,220,0,0,30,70,101,42 ! 10 MOLVOL
1010        BYT 4,0,0,0,140,105,110,226 ! 11 FARADK
1020        BYT 7,0,0,167,61,67,227,20 ! 12 RYDBRK
1030        BYT 2,0,0,0,4,66,160,23 ! 13 FINSTK
1040        BYT 205,220,0,0,200,223,27,50 ! 14 ELRAD
1050        BYT 211,220,0,0,6,167,221,122 ! 15 BOHRAD
1060        BYT 205,220,0,0,6,205,147,40 ! 16 MAGFLX
1070        BYT 163,220,0,0,125,126,140,26 ! 17 ATMASS
1080        BYT 163,220,0,0,205,144,162,26 ! 20 PRMASS
1090        BYT 163,220,0,0,103,225,164,26 ! 21 NTMASS
1100        BYT 0,0,160,126,226,25,1,20 ! 22 ELGK
1110        BYT 166,220,0,0,200,7,164,222 ! 23 BOHRMG
1120        BYT 163,220,0,0,100,202,120,120 ! 24 NUCLMG
1130        BYT 166,220,0,0,40,203,204,222 ! 25 ELMAG
1140        BYT 164,220,0,0,161,141,20,24 ! 26 PRMAG
1150        BYT 10,0,0,0,207,31,165,46 ! 27 PRGYMR
1160        BYT 0,0,0,0,0,65C,06C,98C ! 30 GRACCL 9.81 m/s^2
1170 ! R36 = index 0,1,...,255
1180 LOOKUP BIN 
1190 !      BYT 336             ! DEBUG BREAKPOINT
1200 ! HP 75 specific (ROMPTR instead of BINTAB)
1210        LDMD R30,=ROMPTR    ! get load address to make...
1220        ADM R30,=TABLE      ! ... abs. address of TABLE
1230        CLB R37             ! zero out for R36-R37 shift
1240        ELM R36             ! * 2 (ELM shifts CY into R37)
1250        ELM R36             ! * 4 (LLM would drop CY)
1260        ELM R36             ! * 8
1270        ADM R30,R36         ! address of constant
1280        LDMD R40,R30        ! get and ...
1290        PUMD R40,+R12       ! push on R12 stack
1300        RTN 
1310 ! each constant takes
1320 ! length of its name
1330 ! + 7 bytes here
1340 ! + 8 bytes in table
1350 ! VLITE = 299792458 m/s
1360        BYT 0,55            ! function, return a float
1370 VLITE  LDB R36,=0
1380        JMP LOOKUP
1390 ! CHARGE = 1.6021892E-19 coulombs (charge)
1400        BYT 0,55
1410 CHARGE LDB R36,=1
1420        JMP LOOKUP
1430 ! PLANCK = 6.626176E-34
1440        BYT 0,55
1450 PLANCK LDB R36,=2
1460        JMP LOOKUP
1470 ! ELMASS = 9.109534E-31 kg (electron mass)
1480        BYT 0,55
1490 ELMASS LDB R36,=3
1500        JMP LOOKUP
1510 ! AVGDRO = 6.022045E23
1520        BYT 0,55
1530 AVGDRO LDB R36,=4
1540        JMP LOOKUP
1550 ! MOLRGC = 8.31441
1560        BYT 0,55
1570 MOLRGC LDB R36,=5
1580        JMP LOOKUP
1590 ! BOLTK = 1.380662E-23
1600        BYT 0,55
1610 BOLTK  LDB R36,=6
1620        JMP LOOKUP
1630 ! GRAVK = 6.672E-11 m^3/s^2/kg (universal gravity constant)
1640        BYT 0,55
1650 GRAVK  LDB R36,=7
1660        JMP LOOKUP
1670 ! MOLVOL = 0.022413818
1680        BYT 0,55
1690 MOLVOL LDB R36,=10
1700        JMP LOOKUP
1710 ! FARADK = 96484.56
1720        BYT 0,55
1730 FARADK LDB R36,=11
1740        JMP LOOKUP
1750 ! RYDBRK = 10973731.77
1760        BYT 0,55
1770 RYDBRK LDB R36,=12
1780        JMP LOOKUP
1790 ! FINSTK = 137.03604
1800        BYT 0,55
1810 FINSTK LDB R36,=13
1820        JMP LOOKUP
1830 ! ELRAD = 2.817938E-15
1840        BYT 0,55
1850 ELRAD  LDB R36,=14
1860        JMP LOOKUP
1870 ! BOHRAD = 5.2917706E-11
1880        BYT 0,55
1890 BOHRAD LDB R36,=15
1900 LOOK_1 JMP LOOKUP          ! trampoline
1910 ! MAGFLX = 2.0678506E-15
1920        BYT 0,55
1930 MAGFLX LDB R36,=16
1940        JMP LOOK_1
1950 ! ATMASS = 1.6605655E-27
1960        BYT 0,55
1970 ATMASS LDB R36,=17
1980        JMP LOOK_1
1990 ! PRMASS = 1.6726485E-27
2000        BYT 0,55
2010 PRMASS LDB R36,=20
2020        JMP LOOK_1
2030 ! NTMASS = 1.6749543E-27
2040        BYT 0,55
2050 NTMASS LDB R36,=21
2060        JMP LOOK_1
2070 ! ELGK = 1.0011596567
2080        BYT 0,55
2090 ELGK   LDB R36,=22
2100        JMP LOOK_1
2110 ! BOHRMG = 9.274078E-24
2120        BYT 0,55
2130 BOHRMG LDB R36,=23
2140        JMP LOOK_1
2150 ! NUCLMG = 5.050824E-27
2160        BYT 0,55
2170 NUCLMG LDB R36,=24
2180        JMP LOOK_1
2190 ! ELMAG = 9.284832E-24
2200        BYT 0,55
2210 ELMAG  LDB R36,=25
2220        JMP LOOK_1
2230 ! PRMAG = 1.4106171E-26
2240        BYT 0,55
2250 PRMAG  LDB R36,=26
2260        JMP LOOK_1
2270 ! PRGYMR = 267519870
2280        BYT 0,55
2290 PRGYMR LDB R36,=27
2300        JMP LOOK_1
2310 ! gravity acceleration GRACCEL = 9.80665 m/s^2
2320        BYT 0,55
2330 GRACCL LDB R36,=30
2340        JMP LOOK_1
2350 ! HP 75 specific (global addresses)
2360 RSMEM- DAD 22037
2370 ROMPTR DAD 101243
2380        FIN 
