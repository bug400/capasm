*
* LIF file header
*
       DATA LEXFILE_NAME        ; lex file name 8 characters length for HP-75
       DATA "  "                ; padded 2 blank characters
       DEF  89E0H               ; file type LEX75
       BSS  4                   ; start sector, always zeros
       DATA 0                   ; file length in sectors, computed from source
       DATA 0
       VAL (((LXEND)-(RMBASE)+18D+255D)/65536D)&0FFH
       VAL (((LXEND)-(RMBASE)+18D+255D)/256D)&0FFH
       VAL BCD_YEAR             ; date YY MM DD as BCD numbers
       VAL BCD_MONTH
       VAL BCD_DAY
       VAL BCD_HOUR             ; time HH MM SS as BCD numbers
       VAL BCD_MIN
       VAL BCD_SEC
       DEF 8001H                ; implementing bytes for HP-75 LEX files
       DATA "    "              ; password (blank)
*
* HP-75 RAM file header
*
RAMHDR
       DEF 0                    ; location of file (zero)
       DEF (LXEND)-(RMBASE)+18D ; size of file, computed from source
       VAL (TYRAM?)|(TYPUR?)|(TYCOP?)|(TYTOK?) ; Access bits
       DATA TYNLEX              ; name of type
       DATA (SECONDS1900).4     ; date and time
       DATA LEXFILE_NAME        ; file name (8 characters)
