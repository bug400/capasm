1 !****************************
2 !*      FTOC BINARY         *
3 !* (c) Hewlett-Packard Co.  *
4 !*          1980            *
5 !****************************
10        LST 
20 !      GLO GLOBAL 
30        NAM FTOC  
40 !***************************
50 !System Table:
60        DEF RUNTIM
70        DEF ASCIIS
80        DEF PARSE 
90        DEF ERMSG 
100        DEF INIT  
110 !***************************

120 !Parse Routine Table:
130 PARSE  BYT 0,0
140 !***************************

150 !Runtime Routine Table:
160 RUNTIM BYT 0,0
170        DEF FTOC. 
180        BYT 377,377
190 !**************************
200 !ASCII Table:
210 ASCIIS BSZ 0
220        ASP "FTOC"
230        BYT 377
240 !**************************
250 !Error Message Table:
260 ERMSG  BSZ 0
270        BYT 377
280 !**************************
290 !Initialization Routine:
300 INIT   BSZ 0
310        RTN 
320 !**************************
330 !Runtime Routines:
340        BYT 20,55
350 FTOC.  BSZ 0
360        BIN 
370        JSB =ONER  
380        LDM R50,R40
390        LDM R40,=1,0,0,0,0,0, 0,32C
400        JSB =SUB10 
410        POMD R70,-R12
420        LDM R50,=0,0,0,0,0,0, 0,50C
430        JSB =MPY10 
440        POMD R70,-R12
450        LDM R50,R40
460        LDM R40,=0,0,0,0,0,0, 0,90C
470        JSB =DIV10 
480        RTN 
490 ONER   DAD 56215
500 SUB10  DAD 52137
510 MPY10  DAD 52562
520 DIV10  DAD 51644
530        FIN 
