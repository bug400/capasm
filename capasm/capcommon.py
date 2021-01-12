#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This module contains the common code for all programs
#
# (c) 2020 Joachim Siebold
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#--------------------------------------------------------------------------
#
# Changelog
#
# 02.01.2021 jsi
# - solved issue #2, incorrect range check of relative jumps
# 08.01.2021 jsi
# - extended check marks redefinition of global symbols if there is a type or 
#   value mismatch
# - suppress superfluous code output of BSZ pseudo-ops
# - line numbers in list file
# - parsing of conditional assembly pseudo-ops fixed
#
import re,os,sys,importlib,datetime
from pathlib import Path

#
# Program Constants -----------------------------------------------------
#
CAPASM_VERSION="Version 1.0.0"
CAPASM_VERSION_DATE="January 2021"

#
# CAPASM custom exception -----------------------------------------------
# The assembler raises this exception, if a fatal error occurred
#
class capasmError(Exception):
   def __init__(self,msg):
      super().__init__()
      self.msg= msg

#
# Class to generates Date/Time as BCD ---------------------------------------
#
class clsDateTime(object):

   def __init__(self):
      super().__init__()
      now=datetime.datetime.now()
      self.bcdYear= self.intToBcd(now.date().year-2000)
      self.bcdMonth= self.intToBcd(now.date().month)
      self.bcdDay= self.intToBcd(now.date().day)
      self.bcdHour= self.intToBcd(now.time().hour)
      self.bcdMin= self.intToBcd(now.time().minute)
      self.bcdSec= self.intToBcd(now.time().second)

   def intToBcd(self,value):
      return (((int(value/10)%10)<<4)+(value%10))
#
# Static class for the bytes to store check --------------------------------
#
# Returns the number of bytes that can be stored according to the
# data register and the design of the CPU register bank
#
class BYTESTOSTORE(object):

   __dictBytesToStore__= {
   0o0: 2,   # R(*) ptr
   0o1: 0,
   0o2: 2,   # X
   0o3: 1,   # X
   0o4: 2,   # PC
   0o5: 1,   # PC
   0o6: 2,   # begin of GP 2 byte sections
   0o7: 1,

   0o10: 2,
   0o11: 1,
   0o12: 2,
   0o13: 1,
   0o14: 2,
   0o15: 1,
   0o16: 2,
   0o17: 1,

   0o20: 2,
   0o21: 1,
   0o22: 2,
   0o23: 1,
   0o24: 2,
   0o25: 1,
   0o26: 2,
   0o27: 1,
  
   0o30: 2,
   0o31: 1,
   0o32: 2,
   0o33: 1,
   0o34: 2,
   0o35: 1,
   0o36: 2,
   0o37: 1,

   0o40: 8,   # begin of GP 8 byte sections
   0o41: 7,
   0o42: 6,
   0o43: 5,
   0o44: 4,
   0o45: 3,
   0o46: 2,
   0o47: 1,

   0o50: 8,
   0o51: 7,
   0o52: 6,
   0o53: 5,
   0o54: 4,
   0o55: 3,
   0o56: 2,
   0o57: 1,

   0o60: 8,
   0o61: 7,
   0o62: 6,
   0o63: 5,
   0o64: 4,
   0o65: 3,
   0o66: 2,
   0o67: 1,

   0o70: 8,
   0o71: 7,
   0o72: 6,
   0o73: 5,
   0o74: 4,
   0o75: 3,
   0o76: 2,
   0o77: 1
   }

   @classmethod 
   def numBytes(cls,reg):
      if reg<0:
         return None
      else:
         return BYTESTOSTORE.__dictBytesToStore__[reg]
#
# Static class for number and label parsing ----------------------------------
#
class parseFunc(object):

   DELIMITER=""
   LABELMATCHSTRING=""
   

#  Parse quoted string
#
   @staticmethod
   def parseQuotedString(string):
      if string[0] not in parseFunc.DELIMITER:
         return None
      if string[0]!=string[-1]:
         return None
      string=string[1:len(string)-1]

      return string
#
#  Parse quoted or unquoted string
#
   @staticmethod 
   def parseAnyString(string):
      if string[0] in parseFunc.DELIMITER:
         return parseFunc.parseQuotedString(string)
      else:
         return string
#
#  Parse label
#
   @staticmethod
   def parseLabel(string,length):
      match=re.fullmatch(parseFunc.LABELMATCHSTRING+ str(length)+"}",string)
      if match:
         return string
      else:
         return None
#
#  Parse decimal number (without D at the end, e.g. line numbers)
#
   @staticmethod
   def parseDecimal(string):
      try:
         val=int(string,10)
         return None if val <  0 else val
      except ValueError:
         return None
#
#  Parse hex number 
#
   @staticmethod
   def parseHex(string):
      try:
         val=int(string,16)
         return None if val < 0 else val
      except ValueError:
         return None

#
#  Parse binary number
#
   @staticmethod
   def parseBin(string):
      try:
         val=int(string,2)
         return None if val < 0 else val
      except ValueError:
         return None
#
#  Parse octal number
#
   @staticmethod
   def parseOctal(string):
      try:
         val=int(string,8)
         return None if val < 0 else val
      except ValueError:
         return None
#
#  Parse BCD number (with a C at the end)
#
   @staticmethod
   def parseBCD(string):
      retVal=0
      for c in string:
         if c in "0123456789":
            retVal=(retVal<<4) | ord(c)-ord("0")
         else:
            return None
      return retVal
#
#  Parse Kbyte number (with a K at the end)
#
   @staticmethod
   def parseKB(string):
      try:
         val=int(string,10)*1024
         return None if val <  0 else val
      except ValueError:
         return None

#
#  Parse number, guess the type from the type attribute character at the end
#  If the number has no attribute, then it is an ocal number
#  
   @staticmethod
   def parseNumber(string):
      retval=0
      if string[-1] in "Dd":
         return parseFunc.parseDecimal(string[:-1])
      elif string[-1] in "Cc":
         return parseFunc.parseBCD(string[:-1])
      elif string[-1] in "Hh#":
         return parseFunc.parseHex(string[:-1])
      elif string[-1] in "Bb":
         return parseFunc.parseBin(string[:-1])
      elif string[-1] in "OoQq":
         return parseFunc.parseOctal(string[:-1])
      elif string[-1] in "Kk":
         return parseFunc.parseKB(string[:-1])
      elif string[-1] in "0123456789":
         return parseFunc.parseOctal(string)
      else:
         return None

#
#  Basic Static class for the opcode dictionary ----------------------------------
#
class OPCODES(object):

   NUM_OPERANDS_ANY=-1
#
#    Each opcode is associated to a list with the items:
#    - parse method
#    - code generator method
#    - instruction or instruction template which must be completed later
#    - number of operand parameters min
#    - number of operand parameters max
#    for ARP/DRP optimization in IF-ELSE-ENDIF clauses:
#    - flag if opcode is an unconditional jump (GTO, RTN, JSBN) 
#    - flag if opcode does not executable code
#    for the processing of conditional assembly pseudo-ops
#    - flag if opcode is an IF/ELSE/ENDIF conditional pseudo op
#
   __opcodeDict__= {
   "ARP" : ["pArp","gdarp",0o0,1,1,False,False,False],
   "DRP" : ["pDrp","gdarp",0o100,1,1,False,False,False],
   "ELB" : ["p1reg","gdirect",0o200,1,1,False,False,False],
   "ELM" : ["p1reg","gdirect",0o201,1,1,False,False,False],
   "ERB" : ["p1reg","gdirect",0o202,1,1,False,False,False],
   "ERM" : ["p1reg","gdirect",0o203,1,1,False,False,False],
   "LLB" : ["p1reg","gdirect",0o204,1,1,False,False,False],
   "LLM" : ["p1reg","gdirect",0o205,1,1,False,False,False],
   "LRB" : ["p1reg","gdirect",0o206,1,1,False,False,False],
   "LRM" : ["p1reg","gdirect",0o207,1,1,False,False,False],
   "ICB" : ["p1reg","gdirect",0o210,1,1,False,False,False],
   "ICM" : ["p1reg","gdirect",0o211,1,1,False,False,False],
   "DCB" : ["p1reg","gdirect",0o212,1,1,False,False,False],
   "DCM" : ["p1reg","gdirect",0o213,1,1,False,False,False],
   "TCB" : ["p1reg","gdirect",0o214,1,1,False,False,False],
   "TCM" : ["p1reg","gdirect",0o215,1,1,False,False,False],
   "NCB" : ["p1reg","gdirect",0o216,1,1,False,False,False],
   "NCM" : ["p1reg","gdirect",0o217,1,1,False,False,False],
   "TSB" : ["p1reg","gdirect",0o220,1,1,False,False,False],
   "TSM" : ["p1reg","gdirect",0o221,1,1,False,False,False],
   "CLB" : ["p1reg","gdirect",0o222,1,1,False,False,False],
   "CLM" : ["p1reg","gdirect",0o223,1,1,False,False,False],
   "ORB" : ["pOrXr","gdirect",0o224,2,2,False,False,False],
   "ORM" : ["pOrXr","gdirect",0o225,2,2,False,False,False],
   "XRB" : ["pOrXr","gdirect",0o226,2,2,False,False,False],
   "XRM" : ["pOrXr","gdirect",0o227,2,2,False,False,False],
   "BIN" : ["pNoPer","gdirect",0o230,0,0,False,False,False],
   "BCD" : ["pNoPer","gdirect",0o231,0,0,False,False,False],
   "SAD" : ["pNoPer","gdirect",0o232,0,0,False,False,False],
   "DCE" : ["pNoPer","gdirect",0o233,0,0,False,False,False],
   "ICE" : ["pNoPer","gdirect",0o234,0,0,False,False,False],
   "CLE" : ["pNoPer","gdirect",0o235,0,0,False,False,False],
   "PAD" : ["pNoPer","gdirect",0o237,0,0,False,False,False],
   "LDB" : ["pLdSt","gLdSt",0o240,2,10,False,False,False],
   "LDBI" : ["pLdSt","gLdSt",0o240,2,NUM_OPERANDS_ANY,False,False,False],
   "LDBD" : ["pLdSt","gLdSt",0o240,2,NUM_OPERANDS_ANY,False,False,False],
   "LDM" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False,False],
   "LDMI" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False,False],
   "LDMD" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False,False],
   "STB" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False,False],
   "STBI" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False,False],
   "STBD" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False,False],
   "STM" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False,False],
   "STMI" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False,False],
   "STMD" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False,False],
   "CMB"  : ["pAri","gAri",0o300,2,NUM_OPERANDS_ANY,False,False,False],
   "CMM"  : ["pAri","gAri",0o301,2,NUM_OPERANDS_ANY,False,False,False],
   "CMBD"  : ["pAri","gAri",0o300,2,NUM_OPERANDS_ANY,False,False,False],
   "CMMD"  : ["pAri","gAri",0o301,2,NUM_OPERANDS_ANY,False,False,False],
   "ADB"  : ["pAri","gAri",0o302,2,NUM_OPERANDS_ANY,False,False,False],
   "ADM"  : ["pAri","gAri",0o303,2,NUM_OPERANDS_ANY,False,False,False],
   "ADBD"  : ["pAri","gAri",0o302,2,NUM_OPERANDS_ANY,False,False,False],
   "ADMD"  : ["pAri","gAri",0o303,2,NUM_OPERANDS_ANY,False,False,False],
   "SBB"  : ["pAri","gAri",0o304,2,NUM_OPERANDS_ANY,False,False,False],
   "SBM"  : ["pAri","gAri",0o305,2,NUM_OPERANDS_ANY,False,False,False],
   "SBBD"  : ["pAri","gAri",0o304,2,NUM_OPERANDS_ANY,False,False,False],
   "SBMD"  : ["pAri","gAri",0o305,2,NUM_OPERANDS_ANY,False,False,False],
   "ANM"  : ["pAri","gAri",0o307,2,NUM_OPERANDS_ANY,False,False,False],
   "ANMD"  : ["pAri","gAri",0o307,2,NUM_OPERANDS_ANY,False,False,False],
   "JSB"  : ["pJsb","gJsb",0o306,1,2,False,False,False],
   "POBD" : ["pStack","gStack",0o340,2,2,False,False,False],
   "POMD" : ["pStack","gStack",0o341,2,2,False,False,False],
   "PUBD" : ["pStack","gStack",0o344,2,2,False,False,False],
   "PUMD" : ["pStack","gStack",0o345,2,2,False,False,False],
   "POBI" : ["pStack","gStack",0o350,2,2,False,False,False],
   "POMI" : ["pStack","gStack",0o351,2,2,False,False,False],
   "PUBI" : ["pStack","gStack",0o354,2,2,False,False,False],
   "PUMI" : ["pStack","gStack",0o355,2,2,False,False,False],
#
#  Jump and conditional jump Instructions
#
   "JMP"  : ["pJrel","gJrel",0o360,1,1,True,False,False],
   "JNO"  : ["pJrel","gJrel",0o361,1,1,False,False,False],
   "JOD"  : ["pJrel","gJrel",0o362,1,1,False,False,False],
   "JEV"  : ["pJrel","gJrel",0o363,1,1,False,False,False],
   "JNG"  : ["pJrel","gJrel",0o364,1,1,False,False,False],
   "JPS"  : ["pJrel","gJrel",0o365,1,1,False,False,False],
   "JNZ"  : ["pJrel","gJrel",0o366,1,1,False,False,False],
   "JZR"  : ["pJrel","gJrel",0o367,1,1,False,False,False],
   "JEN"  : ["pJrel","gJrel",0o370,1,1,False,False,False],
   "JEZ"  : ["pJrel","gJrel",0o371,1,1,False,False,False],
   "JNC"  : ["pJrel","gJrel",0o372,1,1,False,False,False],
   "JCY"  : ["pJrel","gJrel",0o373,1,1,False,False,False],
   "JLZ"  : ["pJrel","gJrel",0o374,1,1,False,False,False],
   "JLN"  : ["pJrel","gJrel",0o375,1,1,False,False,False],
   "JRZ"  : ["pJrel","gJrel",0o376,1,1,False,False,False],
   "JRN"  : ["pJrel","gJrel",0o377,1,1,False,False,False],
   }
   __condAssemblyOpcodes__= []
#
#  extend the basic opcodes above with the assembler pseudo ops
#
   @classmethod
   def extendDict(cls,extendedOpcodes):
      OPCODES.__opcodeDict__.update(extendedOpcodes)
#
#  get opcode information
#
   @classmethod
   def get(cls,opcode):
      lookUp=opcode
      if lookUp in OPCODES.__opcodeDict__.keys():
         return OPCODES.__opcodeDict__[lookUp]
      else:
         return []




#
# Error Messages static class --------------------------------------------
#
class MESSAGE(object):
#
#  Errors
#
   E_ILL_OPCODE = 0
   E_ILL_REGISTER= 1
   E_ILL_LABEL = 2
   E_DUP_LABEL = 3
   E_ILL_NUMOPERANDS= 4
   E_REGISTERSIGN=5
   E_XREGEXPECTED=6
   E_ILLADDRESSMODE=7
   E_SYMNOTFOUND=8
   E_NUMBERTOOLARGE=9
   E_OPEXCEEDSSECTION=10
   E_SIGNEDREGISTER=11
   E_ILLNUMBER=12
   E_ILLSTRING=13
   E_ILL_LABELOP=14
   E_ILL_LINENUMBER=15
   E_NOTALLOWED_HERE=16
   E_ILL_PROGNAME=17
   E_RELJUMP_TOOLARGE=19
   E_ILL_LITOPERAND=20
   E_ILL_LITERALLENGTH=21
   E_MISSING_LABEL=23
   E_FLAGNOTDEFINED=25
   E_AIFEIFMISMATCH=26
   E_ILLFLAGNAME=27
   E_MISSING_FIN=28
   E_ROM_EXPECTED=29
   E_PCGREATERTHANADDRESS=30
   E_ILL_ADDRESS= 31
   E_MISSINGRPAREN=100
   E_DIVBYZERO=101
   E_ILLEXPRESSION=102
   E_INVALIDSIZESPEC=103
   E_VALTOOLARGE=104
   E_ILLQUOTSTRING=105
   E_UNSIZEDEXPRESSION=106
   E_ILLVALUE=107
   E_ILLSTRUCT=110
#
#  Warnings
#
   W_LITDATADOESNOTFILL=1001
   W_REDEF_DOES_NOT_MATCH=1002
   W_RHASH_LITERAL=1003


   messages= {
#
#     Error messages
#
      E_ILL_OPCODE : "Illegal opcode or pseudo opcode",
      E_ILL_REGISTER: "Illegal register",
      E_ILL_LABEL: "Illegal label in label field",
      E_DUP_LABEL: "Label in label field is already defined",
      E_ILL_NUMOPERANDS: "Illegal number of operands",
      E_REGISTERSIGN: "+/- not allowed in register definition",
      E_XREGEXPECTED: "X register expected as second operand",
      E_ILLADDRESSMODE: "Illegal address mode",
      E_SYMNOTFOUND: "Symbol not found",
      E_NUMBERTOOLARGE: "Number too large",
      E_OPEXCEEDSSECTION: "Literal or label data exceed section boundary",
      E_SIGNEDREGISTER: "+/- required for address register",
      E_ILLNUMBER: "Illegal number",
      E_ILLSTRING: "Illegal string",
      E_ILL_LABELOP: "Illegal label in operand field",
      E_ILL_LINENUMBER: "Illegal line number",
      E_NOTALLOWED_HERE: "Pseudo opcode not allowed here",
      E_ILL_PROGNAME: "Illegal program name",
      E_RELJUMP_TOOLARGE: "Relative jump too large",
      E_ILL_LITOPERAND: "Illegal literal operand",
      E_ILL_LITERALLENGTH: "Illegal byte length of literal operand",
      E_MISSING_LABEL: "Missing label in label field",
      E_FLAGNOTDEFINED: "Flag not defined",
      E_AIFEIFMISMATCH: "AIF/EIF mismatch",
      E_ILLFLAGNAME: "Illegal flag name",
      E_MISSING_FIN: "Missing FIN/END statement",
      E_ROM_EXPECTED: "ROM expected",
      E_ILL_ADDRESS: "Illegal Address",
      E_MISSINGRPAREN: "Missing ) in expression",
      E_DIVBYZERO: "Division by zero in expression",
      E_ILLEXPRESSION: "Illegal expression",
      E_INVALIDSIZESPEC: "Illegal size specified",
      E_VALTOOLARGE: "Value too large for size specified",
      E_ILLQUOTSTRING: "Illegal quoted string",
      E_UNSIZEDEXPRESSION: "Unsized expression(s)",
      E_ILLVALUE: "Illagal Value",
      E_ILLSTRUCT: "Illegal IF/ELSE/ENDIF or LOOP/EX/WHILE",
      E_PCGREATERTHANADDRESS: "PC greater than the specified address",
#
#     Warning messages
#
      W_LITDATADOESNOTFILL: "Literal data list does not fill register section",
      W_REDEF_DOES_NOT_MATCH: "Value/type mismatch of redefined global symbol",
      W_RHASH_LITERAL: "Dangerous R#, cannot check section boundary",

   }

#
#  Get message text for a message number
#
   def getMsg(msgno):
      if msgno < 1000:
         sv="ERROR"
      else:
         sv="WARNING"
      return sv,MESSAGE.messages[msgno]
#
# Fatal error handler (I/O errors etc.). Raise custom exception
#
   @staticmethod
   def fatalError(msg):
     raise capasmError(msg)

# 
# Symbol dictionary class -------------------------------------
#
class clsSymDict(object):
#
#  Symbol types
#
   SYM_DAD=0
   SYM_EQU=1
   SYM_LCL=2

   def __init__(self,extendedChecks,globalSymbolFile,dictSymTypes):
      super().__init__()
      
      self.__extendedChecks__=extendedChecks
      self.__symbols__= { }
      self.__dictSymbolTypes__= dictSymTypes
      self.__maxSymNameLength__=0
#
#  Load global symbols 
#
      if globalSymbolFile in ["85","87","75","none"]:
         globalModuleName=".globals"+globalSymbolFile
         try:
            self.__globalSyms__=importlib.import_module(globalModuleName, \
                              package='capasm')
         except :
            MESSAGE.fatalError("Invalid global symbol file")
      else:
         globalSymbolFilePath=Path(globalSymbolFile)
         suffix=globalSymbolFilePath.suffix.upper()
         if suffix != ".PY":
            MESSAGE.fatalError(\
               "global symbol file does not have a .py suffix")
         if not os.access(globalSymbolFile,os.R_OK):
            MESSAGE.fatalError(\
               "cannot open or read global symbol file")
         try:
            spec=importlib.util.spec_from_file_location(".globals",\
               globalSymbolFile)
            self.__globalSyms__=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.__globalSyms__)
         except :
            MESSAGE.fatalError("Invalid global symbol file")
      return
#
#  Enter new symbol, we have to check for duplicates in the global symbol
#  dictionary and this dictionary as well. Returns None if we have no
#  error or an error number otherwise
#
   def enter(self,name,typ,value,size,defLineInfo,refLineInfo= []):
#
#      Diagnosic
#
       msg=None
#
#      Check global dict, if global symbol was redefined
#
       ret=self.__globalSyms__.globalSymbols.get(name)
       if ret is not None and  self.__extendedChecks__:
#
#      Extended check, warn if redefined global symbol does not match
#      with local symbol definition
#
          if ret[1]!=value or \
             (ret[0]== 0 and (typ != 2 and typ !=0)) or \
             (ret[0]== 1 and typ != 1):
             msg=MESSAGE.W_REDEF_DOES_NOT_MATCH
#
#      Check our own dict, return error if duplicate entry
#
       if name in self.__symbols__.keys():
          msg= MESSAGE.E_DUP_LABEL
#
#      Enter symbol, determine maximum length of symbol name (for reference list)
#
       else:
          self.__symbols__[name]=[typ,value,size,defLineInfo,refLineInfo]
          l=len(name)
          if l > self.__maxSymNameLength__:
             self.__maxSymNameLength__=l
       return msg
#
#  Get a symbol. We look first in our own symbol dictionary. If the
#  symbol is not found, try the Globals dictionary. If a symbol was
#  found in the Globals dictionary the insert it into the local dict.
#
   def get(self,name,lineInfo=None,noGlobStore=False):
      try:
         ret=self.__symbols__[name]
         if lineInfo is not None:
            if not self.__symbols__[name][4]:
               self.__symbols__[name][4]=[lineInfo]
            else:
               self.__symbols__[name][4].append(lineInfo)
         return ret
      except KeyError:
         ret=self.__globalSyms__.globalSymbols.get(name)
         if ret:
            typ=ret[0]
            value=ret[1]
            size=2
            if typ==clsSymDict.SYM_EQU and value <= 0xFF:
               size=1
            if lineInfo is not None:
               refLineInfo=[lineInfo]
            else:
               refLineInfo=[]
            defLineInfo=None
            if not noGlobStore:
               self.enter(name,typ,value,size,defLineInfo,refLineInfo)
            return typ,value,size,defLineInfo,refLineInfo
#
#  Get a list of all symbols in the local dictionary
# 
   def getList(self):
      return list(self.__symbols__.keys())

#
#  Get string for a symbol type
#
   def getSymTypeString(self,st):
      return self.__dictSymbolTypes__[st]
#
#  Get max leght of symbol names 
#
   def getMaxSymNameLength(self):
      return self.__maxSymNameLength__
#
#  Extend the global symbol table
#
   def extendGlobalSymbols(self,key,value):
       self.__globalSyms__.globalSymbols.symbols[key]=value
     

#
# Conditional assembling class ---------------------------------------------
#
# Conditional assembly controls with IF <condition> ENDIF or
# IF <condition> ELSE ENDIF clauses whether a source file line is "active"
# == has to be executed or "not active" == "has to be treated as comment".
#
# The conditional assembly class maintains the following data:
# - flags               : Dictionary of flag names and their conditions
#                         The dictionary is populated by the set or the
#                         clr method
# - stack               : The current state of the parsed conditions are pushed
#                         on a stack, because conditions can be nested
# - activeConditionIndex: Index of the "current" active condition. 
#
class clsConditionalAssembly(object):

   def __init__(self,definedFlags):
    
      super().__init__()
      self.__stack__= []
      self.__flags__ = {}
      self.__activeConditionIndex__= -1
   
      for f in definedFlags:
         self.__flags__[f]=True
#
#  returns True, if the current condition is active 
#
   def isActive(self):
      return (len(self.__stack__)-1) == self.__activeConditionIndex__
#
#  returns True, if we are within a condition
#
   def isOpen(self):
      return len(self.__stack__) > 0
#
#  return True, if lines are inactive and must be handeled as comment
#
   def isSuppressed(self):
      if not self.isOpen():
         return False
      return self.__stack__[self.__activeConditionIndex__]
#
#  endif, pop condition from stack
#
   def endif(self):
      if self.isActive():
         self.__activeConditionIndex__-=1
      self.__stack__.pop()
#
#  set flag
#
   def set(self,name):
      self.__flags__[name]= True
#
#  clear flag
#
   def clr(self,name):
      self.__flags__[name]= False
#
#  ifdef, push new condition on stack
#
   def ifdef(self,name):
      if not self.isSuppressed():
         self.__activeConditionIndex__+=1
      if name in self.__flags__:
         self.__stack__.append(False)
      else:
         self.__stack__.append(True)
      
#
#  ifndef, push new condition on stack
#
   def ifndef(self,name):
      if not self.isSuppressed():
         self.__activeConditionIndex__+=1
      if name in self.__flags__:
         self.__stack__.append(True)
      else:
         self.__stack__.append(False)
#
#  ifset, push new condition on stack
#
   def ifset(self,name):
      if not self.isSuppressed():
         self.__activeConditionIndex__+=1
      try:
         self.__stack__.append(self.__flags__[name]==False)
      except KeyError:
         self.__stack__.append(False)
         if not self.isSuppressed():
            return False
      return True
#
#  ifnset, push new condition on stack
#
   def ifnset(self,name):
      if not self.isSuppressed():
         self.__activeConditionIndex__+=1
      try:
         self.__stack__.append(self.__flags__[name]!=False)
      except KeyError:
         self.__stack__.append(False)
         if not self.isSuppressed():
            return False
      return True
#
#  else reverts the status of the topmost condition
#
   def els(self):
      self.__stack__[-1]= not self.__stack__[-1]

#
# GlobVar data class, global variables of the assembler --------------------
#
class clsGlobVar(object):

   def __init__(self):

      super().__init__()
      self.progName=""               # program name
      self.arpReg=-1                 # current content of the ARP
      self.drpReg=-1                 # current content of the DRP
      self.lastStmtWasPAD= False     # PAD sets this to True
      self.lastStmtWasJSB= False     # JSB sets this to True
      self.ORG=0                     # ORG value set by ORG
      self.PC=0                      # Program counter
      self.codeLen=0                 # length of generated code
      self.allowHashRLiteral=True    # allow LD R#,=Literal
      self.hasAbs=False              # if ABS was used
      self.hasNam=False              # if NAM was used
      self.hasIncludes=False         # if any include files were processed
      self.symNamLen=6               # symbol name length parameter
      self.isRegressionTest=False    # true to run assembler in regtest mode
      self.isFin=False               # FIN Statement encountered
      self.useHex=False              # output hex instead of oct
      self.symDict=None              # Symbol dictionary
      self.errorCount=0              # Error counter
      self.warningCount=0            # Warning counter
      self.sourceFileDirectory=""    # directory of source file if specified
      self.condAssembly= None        # conditional assembly object
      self.symDict= None             # global symbol dictionary object
      self.title=""                  # title of print page
      self.doPageBreak=False         # do a page break
      self.lastRtnAddr=-255          # address of last return
      self.lastOpcodeWasJmp=False    # flag, if last opcode was JMP or RTN
#      
# Token data class, result of lexical scanner -----------------------------
#
class clsToken(object):

   def __init__(self, string= "", position= 0, termChar=""):
      self.string=string          # this is the scanned token as string
      self.position=position      # the position of the scanned token in the
                                  # source line
      self.termChar=termChar      # the char after the token that terminated
                                  # scanning

   def __repr__(self):  # pragma: no cover
      return ("clsToken object '{:s}' {:d} '{:s}'".format(self.string, self.position,self.termChar))

#
# Lexical Scanner class -------------------------------------------------
#
# The scanLine() method of the scanner takes a source line as input and
# returns a list of clsToken objects:
# [lineNumber,label,opcode,[scannedOperands]]
#
class clsLineScanner(object):

#
#  init scanner:
# commentLineChar: character(s) that indicate a line with a comment
# commentTrailerChar: character(s) that idicate trailing comment
# stringDelimiters: string delimiters
#

   def __init__(self,commentLineChar,commentTrailerChar,stringDelimiters):
      super().__init__()
      self.__commentLineChar__= commentLineChar
      self.__commentTrailerChar__= commentTrailerChar
      self.__stringDelimiters__= stringDelimiters
#
#  Get one character, returns a tripel of [character, position, next character]
#
   def scanChar(self):
      oldposition= self.__position__
      oldch= self.__gch__
      oldnxtch= self.__nxtChar__
      if self.__gch__ != "":
         self.__position__+=1  
         self.__gch__=self.__nxtChar__
         if (self.__position__) >= len(self.__line__)-1:
            self.__nxtChar__= ""
         else:
            self.__nxtChar__=self.__line__[self.__position__+1]
    
      return [oldch, oldposition,oldnxtch]
#
#  Get Token, returns a token object
#
      
   def scanTok(self,termSyms=None):
#
#     Skip blanks
#
      while True:
         char, pos, nxtChar=self.scanChar()
         if char!=" ":
            break
      token=""
      position= -1
      termchar= ""
      termString=" "
      inString=False
      if termSyms is not None:
         termString+=termSyms
         if char in termSyms:
            return clsToken(char, pos, nxtChar)
#
#     Loop until end of line, blank or termchar encountered
#
      while char!="":
         if not inString and char in termString:
               termchar= char
               break
#
#     String handling
#
         if char in self.__stringDelimiters__:
            if not inString:
               quote=char
               inString=True
            else:
#
#              In string mode and we have a " or '
#
               if char==quote:
                  inString=False
#
#        Accumulate token
#
         if len(token)==0:
            position= pos
         token+=char
         char, pos, nxtChar=self.scanChar()
      return clsToken(token, position, termchar)
#
#  Scan input line and return scanned line number, label, opcode and a list
#  of operands. Missing items are None
#
   def scanLine(self,line):

      scannedLineNumber=None
      scannedLabel=None
      scannedOpcode=None
      scannedOperand=[]

      self.__line__= line
      self.__position__= -1
      self.__gch__= ""
      self.__nxtChar__= ""
      if self.__line__!="":
         self.__gch__=self.__line__[0]
         self.__position__= 0
      if len(line) > 1:
         self.__nxtChar__= self.__line__[1]
#
#     We have an empty line that contains nothing, return line count as token
#
      tok=self.scanTok()
      if tok.string=="":
         return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
#
#     Is the first token a line number?
#
      lineBegin=0
      if tok.string[0] in "0123456789":
         scannedLineNumber=tok
         lineBegin=len(scannedLineNumber.string)+tok.position
         tok=self.scanTok()
#
#     No next token, leave ...
#
      if tok.string=="":
         return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
#
#     Is the token a label? 
#
      if tok.position <= lineBegin+2:
         if tok.string[0] not in self.__commentLineChar__:
            scannedLabel= tok
            tok= self.scanTok()
#
#     No next token, leave ...
#
      if tok.string=="":
         return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
#
#     Do we have a comment?
#
      if tok.string[0] in self.__commentLineChar__ \
         or tok.string[0] in self.__commentTrailerChar__:
         return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
#
#      Opcode, convert it to upper case
#
      scannedOpcode= tok
      scannedOpcode.string=scannedOpcode.string.upper()
#
#     Operand, if any, scan it as a comma separated list
#
      tok= self.scanTok(",")
      while True:
#
#        End of line
#
         if tok.string=="":
            break
#
#        Comment 
#
         if tok.string[0] in self.__commentTrailerChar__:
            break
#
#        Comma, continue loop
#
         if tok.string!=",":
            scannedOperand.append(tok)
         tok= self.scanTok(",")
      return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]

#
#  object code writer class --------------------------------------------
# 
#  This object writer dumps the generated code to the binary output file
#
class clsObjWriter(object):
#
#  Initialize, open binary output file
#
   def __init__(self,objectfilename):
      super().__init__()
      self.__codeLen__=0
      self.__objectfile__= None
      try:
         self.__objectfile__=open(objectfilename,"wb")
      except OSError:
         MESSAGE.fatalError("Error opening object file")
      return
#
#  Dump code to file
#
   def writeCode(self,codeInfo,parsedLine):
      if codeInfo.code == []:
         return
      for c in codeInfo.code:
         try:
            self.__objectfile__.write(c.to_bytes(1,byteorder="big"))
            self.__codeLen__+=1
         except OSError:
            MESSAGE.fatalError("Error writing object file")
         except OverflowError:
            MESSAGE.fatalError("Internal error: code overflow")
      return
#
#  Destructor, flush and close file
#
   def __del__(self):
      if self.__objectfile__ is not None:
#        fill= 256 - (self.__codeLen__ % 256)
#        c=0xFF
#        for i in range(0,fill):
#           self.__objectfile__.write(c.to_bytes(1,byteorder="big"))
         self.__objectfile__.flush()
         self.__objectfile__.close()
      return
#
# List file writer class -----------------------------------------------
#
# The list file writer creates the list file
#
class clsListWriter(object):

#
#  Initialize and open list file
#
   def __init__(self,globVar,listFileName,maxLines,lineWidth):
      super().__init__()
      self.__globVar__=globVar
      self.__maxLines__=maxLines
      self.__lineWidth__= lineWidth
      self.__lineCount__=maxLines
      self.__listFile__= None
      self.__totalLines__=0
      self.__totalBytesOfCode__=0
      self.__pageCount__=1
      self.__noList__=False
      self.__sourceFileDict__={ }
      self.__sourceFileCount__=0
      try:
         if listFileName=="":
            self.__listFile__=sys.stdout
            self.__noList__=True
         else:
            self.__listFile__=open(listFileName,"w")
      except OSError:
         MESSAGE.fatalError("Error opening list file")
      self.writeHeader()
      return
#
#  Format program code byte (either 3 digit octal or 2 digit hex)
#
   def formatCode(self,b):
      if self.__globVar__.useHex:
         if b is None:
            return "  "
         else:
            return "{:02X}".format(b)
      else:
         if b is None:
            return "   "
         else:
            return "{:03o}".format(b)
#
#  Format address (either 6 digit ocal number of 4 digit hex number)
#
   def formatAddress(self,b):
      if self.__globVar__.useHex:
         if b is None:
            return "    "
         else:
            return "{:04X}".format(b)
      else:
         if b is None:
            return "      "
         else:
            return "{:06o}".format(b)
#
# Format symbol line reference
#
   def formatLineReference(self,lineInfo):
      fileName,lineNumber= lineInfo
      if not fileName in self.__sourceFileDict__:
         self.__sourceFileCount__+=1
         self.__sourceFileDict__[fileName]=self.__sourceFileCount__
      return " {:5d};{:d}".format(lineNumber, \
             self.__sourceFileDict__[fileName])

#
#  Write full header. This information is always printed to standard output
#  and the beginning of the first page of the list file
#
   def writeHeader(self):
      if self.__globVar__.isRegressionTest:
         headerString=""+self.__globVar__.progName+"\n(c) Joachim Siebold\n\n"
      else:
         s1=self.__globVar__.progName+"  "+CAPASM_VERSION+"       "+\
             CAPASM_VERSION_DATE
         s2=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
         offset=self.__lineWidth__-len(s1)-len(s2)
         headerString=""+s1+" "*offset+s2+"\n(c) Joachim Siebold 2020\n\n"
#
#     Print header to terminal regardless if we have a list file or not
#
      print(headerString)
      if not self.__noList__:
         self.__listFile__.write(headerString)
      self.__lineCount__=3
      self.__pageCount__=1
#
#  Do a page break, write small header with page numbers
#
   def pageBreak(self):
      if self.__noList__:
         return
      self.__listFile__.write("")
      self.__listFile__.write("Page {:4d} {:^60s}\n".format(\
          self.__pageCount__,self.__globVar__.title))
      self.__listFile__.write(self.__globVar__.progName+"\n")
      self.__listFile__.write("\n")
      self.__lineCount__=3
      self.__pageCount__+=1
#
#  Output one line to list file, do page break if necessary
#
   def wrL(self,string):
      self.__lineCount__+=1
      try:
         if self.__lineCount__> self.__maxLines__:
            self.pageBreak()
         self.__listFile__.write(string+"\n")
      except OSError:
         MESSAGE.fatalError("Error writing list file")
#
#  Write list file information for a source line including code, sourceline
#  and diagnostics. If no list file is specified, this information is
#  printed to standard output only if any diagnostics exist
#
   def writeLine(self,parsedLine,codeInfo):
      lineNumber="{:5d} ".format(parsedLine.lineInfo[1])
#
#     check if we have a page break
#
      if self.__totalLines__ > 0 and self.__globVar__.doPageBreak:
         self.__lineCount__= self.__maxLines__
      self.__globVar__.doPageBreak= False       
      self.__totalLines__+=1
      codeLen=len(codeInfo.code)
      self.__totalBytesOfCode__+= codeLen
#
#     Do not output statement, if we output to terminal
#
      if self.__noList__ and parsedLine.messages== [ ] \
         and codeInfo.messages== [ ]:
         return
      pc=parsedLine.PC
      line=parsedLine.line
#
#     PC 
#
      s=lineNumber+self.formatAddress(pc)+" "
#
#     Bytes of code (max 3 octal or 4 hex)
#
      if self.__globVar__.useHex:
         numCode=4
      else:
         numCode=3
      for i in range(0,numCode):
         if i>= codeLen:
            s+=self.formatCode(None)+" "
         else:
            s+=self.formatCode(codeInfo.code[i])+" "
#
#     Source code line
#
      s+=line
      self.wrL(s)
#
#     Continuation line(s) for code, if we have more than numCode bytes 
#     of code. i is the index of the current byte. If the shortList
#     flag is set in the codeInfo object, then continuation lines are skipped
#
      j=0
      i=numCode
      skippedCode=False
      while i < codeLen:
         if j==0:
            pc+=numCode
            s="      "+self.formatAddress(pc)+" "
         s+=self.formatCode(codeInfo.code[i])+" "
         j+=1
         if j==numCode:
            if(not codeInfo.shortList):
               self.wrL(s)
            else:
               skippedCode=True
            j=0
         i+=1
      if (skippedCode):
         self.wrL("      ...")
      if j>0:
         self.wrL(s)
#
#     Error messages of parser and code generator, if any
#
      for e in parsedLine.messages:
         sv,msg=MESSAGE.getMsg(e)
         s="*{:s}(P) at {:s}({:d}): {:s}".format(sv,parsedLine.lineInfo[0], \
            parsedLine.lineInfo[1],msg)
         self.wrL(s)
      for e in codeInfo.messages:
         sv,msg=MESSAGE.getMsg(e)
         s="*{:s}(C) at {:s}({:d}): {:s}".format(sv,parsedLine.lineInfo[0], \
            parsedLine.lineInfo[1],msg)
         self.wrL(s)
      return
#
#  Write symbol table
#
   def writeSymbols(self,reference):
      SymDict=self.__globVar__.symDict
#
#     No table, if either no list file is speficied or the reference table
#     option is zero
#
      if reference==0 or self.__noList__:
         return
      symlist=SymDict.getList()
      self.wrL(" ")
      self.wrL("{:d} Symbols used:".format(len(symlist)))
#
#     Sort symbol names and begin loop to output information
#
      symlist.sort()
      maxLen=SymDict.getMaxSymNameLength()
      formatString="{:"+str(maxLen)+"s} {:s} {:s}"
      for sn in symlist:
#
#        do not output symbols beginning with a number (generated symbols)
#
         if sn[0].isdigit():
            continue
#
#        Output dictionary entry
#
         typ,value,size,defLineInfo,refLineInfo=SymDict.get(sn)
         symAddr=self.formatAddress(value)
         s=formatString.format(sn,\
             SymDict.getSymTypeString(typ),\
             symAddr)
         nSkip=len(s)
#
#        Output symbol dictionary
#        first print the line number where the symbol was defined
#        this value is None for global symbols
#
         if defLineInfo is None:
            s+="  GLOBAL"
         else:
            s+=self.formatLineReference(defLineInfo)
         j=0
#
#        Now output line references, output a warning if we have none
#
         if reference==2:
            if len(refLineInfo)==0:
               s+=" ** Not referenced!"
               j+=1
            else:
               for ln in refLineInfo:
                  if ln[1] == clsParserInfo.ILL_NUMBER:
                     continue                         # dead code ??
                  j+=1
                  s+=self.formatLineReference(ln)
#
#                 We need a continuation line
#
                  if len(s)+8>= self.__lineWidth__:
                     self.wrL(s)
                     s=" "*nSkip
                     j=0
            if j!=0:
               self.wrL(s)
         else:
            self.wrL(s)
#
#     output source file dictionary
#
      self.wrL("")
      self.wrL("Index of source files in symbol cross reference:")
      for filename in self.__sourceFileDict__:
          self.wrL("{:d}: {:s}".format(self.__sourceFileDict__[filename],\
              filename))
      return
#
#  Write statistics: source code lines, generated code, number of errors
#  This information is always printed to standard output
#  and the end of the list file
#
   def writeStatistics(self):
      numberOfErrors=self.__globVar__.errorCount
      numberOfWarnings=self.__globVar__.warningCount
      s1="Assembly completed"
      s2=" {:d} lines processed, {:d} error(s) {:d} warning(s)".format(self.__totalLines__, numberOfErrors,numberOfWarnings)
      if numberOfErrors == 0:
         s3=" {:d} bytes of code written to object file".format(self.__totalBytesOfCode__)
      else:
         s3=" object file deleted"
#
#     Output statistics to terminal regardless if we have a list file
#
      print(s1)
      print(s2)
      print(s3)
      if not self.__noList__:
         self.wrL(s1)
         self.wrL(s2)
         self.wrL(s3)
      return 
#
#  Destructor, flush and close file
#
   def __del__(self):
      if self.__listFile__ is not None:
         self.__listFile__.flush()
         if self.__listFile__ != sys.stdout:
            self.__listFile__.close()
      return
#
# Source file reader class ----------------------------------------------
#
class clsSourceReader(object):
#
#  Initialize and open first source file
#
   def __init__(self,inputFileName):
      super().__init__()
      self.__inputFiles__= []
      self.__lineInfos__= []
      try:
        self.__inputFiles__.append(open(inputFileName,"r"))
        self.__lineInfos__.append([Path(inputFileName).name,0])
      except OSError:
        MESSAGE.fatalError("Error opening source file")
#
# build name of include or link file. 
# If the source assembly file name has a path and
# the include file name has no path
# then put the directory of the source assembly file name in front of
# the include file name
#
   def buildFileName(self,inputFileName,sourceFileDirectory):
      ifPath=Path(inputFileName)
      if str(ifPath.parent)!=".":
         return inputFileName
      if sourceFileDirectory==".":
         return inputFileName
      return str(Path(sourceFileDirectory) / ifPath)
#
#  open include file
#
   def openInclude(self,inputFileName,sourceFileDirectory):
      if len(self.__inputFiles__)> 3:
         MESSAGE.fatalError("Maximum include depth exceeded")
      fileName=self.buildFileName(inputFileName,sourceFileDirectory)
      try:
        self.__inputFiles__.append(open(fileName,"r"))
        self.__lineInfos__.append([Path(inputFileName).name,0])
      except OSError:
        MESSAGE.fatalError("Error opening include or link file "+\
              inputFileName+" ")
#
#  open linked file
#
   def openLink(self,inputFileName,sourceFileDirectory):
      self.__inputFiles__[-1].close()
      self.__inputFiles__.pop()
      self.__lineInfos__.pop()
      self.openInclude(inputFileName,sourceFileDirectory)
   
#
#  Read a line
#
   def read(self):
      while self.__inputFiles__:
         try:
            line=self.__inputFiles__[-1].readline()
         except OSError:
            MESSAGE.fatalError("Error reading source or include file")
         if line:
            self.__lineInfos__[-1][1]+=1    
            return line.strip("\r\n")
#
#        EOF, fall back to previous file, if none return None
#
         self.__inputFiles__[-1].close()
         self.__inputFiles__.pop()
         self.__lineInfos__.pop()
      return None
#
# Get current filename and line count
#
   def getLineInfo(self):
      return [self.__lineInfos__[-1][0],self.__lineInfos__[-1][1]]
         
#
#  Destructor, close any open files
#
   def __del__(self):
      for f in self.__inputFiles__:
         f.close()
      return
#
# Parser Info data class ----------------------------------------------
#
# An object of this class is returned by the parser
#
class clsParserInfo(object):
#
#  Address Modes
#
   AM_REGISTER_IMMEDIATE=0
   AM_REGISTER_DIRECT=1
   AM_REGISTER_INDIRECT=2
   AM_LITERAL_IMMEDIATE=3
   AM_LITERAL_DIRECT=4
   AM_LITERAL_INDIRECT=5
   AM_INDEX_DIRECT=6
   AM_INDEX_INDIRECT=7
#
#  Single, Multibyte Modes
#
   BM_UNKNOWN=0
   BM_SINGLEBYTE=1
   BM_MULTIBYTE=2

#
#  Gosub Modes
#
   JS_LITERAL_DIRECT=0
   JS_INDEXED=1
#
#  Stack operands mode
#
   STACK_INCREMENT=0
   STACK_DECREMENT=1
#
#  Illegal Number
#
   ILL_NUMBER=-1

   def __init__(self,PC,lineInfo,messages,line,opcode="",opcodeLen=0,parsedOperand= [],needsArp=-1,needsDrp=-1,addressMode=AM_REGISTER_IMMEDIATE):
      self.PC=PC                          # program counter
      self.lineInfo= lineInfo             # input file name and line number
      self.messages=messages              # list of error messages, an empty
                                          # list means: no errors
      self.line=line                      # the original source code line
      self.opcode=opcode                  # the opcode string
      self.opcodeLen=opcodeLen            # length of opcode, this enables
                                          # the main program to compute the
                                          # PC of the next statement
      self.parsedOperand=parsedOperand    # list of parsed Operand objects,
                                          # the list may be empty
      self.needsArp=needsArp              # if > 0, generate a DRP instruction
      self.needsDrp=needsDrp              # if > 0, generate an ARP instruction
      self.addressMode=addressMode        # address mode

   def __repr__(self): # pragma: no cover
      return("clsParserInfo object:")
#
# Parsed Operand Data Class --------------------------------------------
#
# Note: the base class is used to indicate illegal operand items
#
class clsParsedOperand(object):
#
#  Parsed Operand Types
#
   OP_INVALID=0
   OP_REGISTER=1
   OP_LABEL=2
   OP_NUMBER=3
   OP_STRING=4
   OP_EXPRESSION=5

   def __init__(self,typ=OP_INVALID):
      self.typ=typ
      self.size=None

   def __repr__(self): # pragma: no cover
      return("clsParsedOperand (generic)")

   def isInvalid(self):
      return self.typ==clsParsedOperand.OP_INVALID
#
#  Invalid operand, operand that had issues during parsing
#
class clsInvalidOperand(clsParsedOperand):
   
   def __init__(self):
      super().__init__(clsParsedOperand.OP_INVALID)

   def __repr__(self): # pragma: no cover
      return("clsParsedOperand (invalid)")
#
#  Parsed expression
#
class clsParsedExpression(clsParsedOperand): 

   def __init__(self,bytecode,size):
      super().__init__(clsParsedOperand.OP_EXPRESSION)
      self.byteCode=bytecode
      self.size=size

   def __repr__(self): # pragma: no cover
      s="clsParsedExpression\n"
      for item in self.byteCode:
         s+=str(item)+" "
      s+=str(self.size)
      return(s)
#
#  Valid number operand (syntax checked)
#
class clsParsedNumber(clsParsedOperand):
   
   def __init__(self,number,size=None):
      super().__init__(clsParsedOperand.OP_NUMBER)
      self.number=number
      self.size=size

   def __repr__(self): # pragma: no cover
      return ("clsParsedNumber number= {:o}".format(self.number))
#
# Valid string operand (syntax checked)
#
class clsParsedString(clsParsedOperand):
   
   def __init__(self,string):
      super().__init__(clsParsedOperand.OP_STRING)
      self.string=string

   def __repr__(self): # pragma: no cover
      return ("clsParsedString string= {:s}".format(self.string))

#
#  Valid label operand (syntax checked) with optional size constraint
#  for symbols in literal data lists
#
class clsParsedLabel(clsParsedOperand):

   def __init__(self,label,size=None):
      super().__init__(clsParsedOperand.OP_LABEL)
      self.label=label
      self.size=size

   def __repr__(self): # pragma: no cover
      return ("clsParsedLabel label= "+self.label+" "+str(self.size))
#
# Valid register operand (syntax checked)
#
class clsParsedRegister(clsParsedOperand):

   R_HASH=-1
   R_ILLEGAL=-2

   def __init__(self,registerSign="", registerTyp="", registerNumber=R_ILLEGAL):
      super().__init__(clsParsedOperand.OP_REGISTER)
      self.registerSign=registerSign      # sign of the register "+", "-" or ""
      self.registerTyp=registerTyp        # register typ "R" or "X" or "!"
      self.registerNumber=registerNumber  # decimal register number
                                          # a * results in register number 1
                                          # a # results in register number
                                          # R_HASH
                                          # if the number is R_ILLEGAL then
                                          # we have an invalid register

   def __repr__(self): # pragma: no cover
      return ("clsParsedRegister object '{:s}' {:s} '{:d}'".format(self.registerSign, self.registerTyp,self.registerNumber))


#
# Code Info Data class -------------------------------------------------
#
# An object of this class is returned by the code generator
#
class clsCodeInfo(object):
   
   def __init__(self,code, messages, shortList=False):
      self.code= code         # list of generated code (bytes)
      self.messages=messages  # list of error messages
      self.shortList=shortList # do not list all generated code (BSS)

   def __repr__(self): # pragma: no cover
      s="clsCodeInfo object code= "
      for i in self.code:
         s+="{:o} ".format(i)
      return (s)


#
# Code Generator Base class --------------------------------------------
#
# Genertes code and returns an object of class clsCodeInfo
#
class clsCodeGeneratorBase(object):
#
#  Completion for load-/store- instruction templates according to address mode
#
   LOADSTORE_COMPLETION = {
   clsParserInfo.AM_REGISTER_IMMEDIATE    : 0b00000,
   clsParserInfo.AM_REGISTER_DIRECT       : 0b00100,
   clsParserInfo.AM_REGISTER_INDIRECT     : 0b01100,
   clsParserInfo.AM_LITERAL_IMMEDIATE     : 0b01000,
   clsParserInfo.AM_LITERAL_DIRECT        : 0b10000,
   clsParserInfo.AM_LITERAL_INDIRECT      : 0b11000,
   clsParserInfo.AM_INDEX_DIRECT          : 0b10100,
   clsParserInfo.AM_INDEX_INDIRECT        : 0b11100
      
   }
#
#  Completion for arithmetic instruction templates according to address mode
#
   ARI_COMPLETION = {
   clsParserInfo.AM_REGISTER_IMMEDIATE    : 0b00000,
   clsParserInfo.AM_REGISTER_DIRECT       : 0b11000,
   clsParserInfo.AM_LITERAL_IMMEDIATE     : 0b01000,
   clsParserInfo.AM_LITERAL_DIRECT        : 0b10000,
   }
#
#  Completion for jsb instruction templates according to address mode
#
   JSB_COMPLETION = {
   clsParserInfo.JS_LITERAL_DIRECT        : 0b01000,
   clsParserInfo.JS_INDEXED               : 0b00000,
   }
#
#  Completion for stack instruction templates according to address mode
#
   STACK_COMPLETION = {
   clsParserInfo.STACK_INCREMENT          : 0b00000,
   clsParserInfo.STACK_DECREMENT          : 0b00010,
   }
            
   _methodDict_= { }
#
#  Initialize generator
#
   def __init__(self,globVar):
      super().__init__()
      self.__globVar__= globVar
      return
#
#  Add error message to the code generator message list
#
   def addError(self,errno):
      if isinstance(errno,list):
         self.__messages__.extend(errno)
         for e in errno:
            if e  < 1000:
               self.__globVar__.errorCount+=1
            else:
               self.__globVar__.warningCount+=1
      else:
         self.__messages__.append(errno)
         if errno  < 1000:
            self.__globVar__.errorCount+=1
         else:
            self.__globVar__.warningCount+=1
      return
#
#  Generate GTO
#
   def gGto(self):
      SymDict=self.__globVar__.symDict
      defCode= [0]* self.__opcodeLen__
      pLabel=self.__parsedOperand__[1]
      if pLabel.typ != clsParsedOperand.OP_LABEL:
         self.__code__.extend(defCode)
         return
      ret=SymDict.get(pLabel.label,self.__lineInfo__)
      if ret==None:
         self.addError(MESSAGE.E_SYMNOTFOUND)
         self.__code__.extend(defCode)
      else:
#
#        relative jump, only local labels which are not abs
#
         typ=ret[0]
         value=ret[1]
         if typ==clsSymDict.SYM_LCL and not self.__globVar__.hasAbs:
            self.__code__.append(0o313)       # ADMD
            offset= value -(self.__pc__+self.__opcodeLen__-1)
            if offset < 0:
               offset= 0xFFFF  + offset
            self.__code__.extend([offset & 0xFF, (offset >>8)&0xFF])
         else:
#
#        absolute jump
#
            value-=1
            self.__code__.append(0o251)       # LDMD
            self.__code__.extend([value & 0xFF, (value >>8)&0xFF])
      return

#
#  Generate DEF,VAL
#
   def gDef(self):
      SymDict=self.__globVar__.symDict
      defCode= [0]* self.__opcodeLen__
      pLabel=self.__parsedOperand__[0]
      if pLabel.typ != clsParsedOperand.OP_LABEL:
         self.__code__.extend(defCode)
         return
      ret=SymDict.get(pLabel.label,self.__lineInfo__)
      if ret==None:
         self.addError(MESSAGE.E_SYMNOTFOUND)
         self.__code__.extend(defCode)
      else:
         if self.__opcodeLen__==1:
            if ret[1] > 0xFF:
               self.addError(MESSAGE.E_NUMBERTOOLARGE)
               self.__code__.extend(defCode)
            else:
               self.__code__.append(ret[1])
         else:
            self.__code__.extend([ret[1] & 0xFF, ret[1] >>8])
#
#  Generate zeros
#
   def gGenZ(self):
      for i in range(0,self.__opcodeLen__):
         self.__code__.append(0)
      self.__shortList__=True
      return
#
#  Generate nothing

   def gNil(self):
      return
#
#  Generate Data, we have only parsed numbers
#
   def gData(self):
      self.gOperands()
      return
#
#  Generate relative jump instructions
#
   def gJrel(self):
#
#     exit if relative jump of an ELSE was removed due to code optimization
#
      if len(self.__parsedOperand__)==0:
         return
      SymDict=self.__globVar__.symDict
      self.__code__.append(self.__opcodeInfo__[2])
      self.__bytesToGenerate__-=1
      pOperand=self.__parsedOperand__[0]
      if pOperand.typ == clsParsedOperand.OP_LABEL:
         ret=SymDict.get(pOperand.label,self.__lineInfo__)
         if ret==None:
            self.addError(MESSAGE.E_SYMNOTFOUND)
            self.__code__.append(0)
         else:
            value=ret[1]
            offset=value-(self.__pc__+2)
            if offset > 127 or offset < -128:
               offset=0
               self.addError(MESSAGE.E_RELJUMP_TOOLARGE)
            if offset < 0:
               offset=255 -abs(offset)+1
            self.__code__.append(offset)
      else:
         self.__code__.append(0)
      return
#
#  Generate Stack instructions
#
   def gStack(self):
#
#     Complete instruction template according to address mode
#
      self.__code__.append(self.__opcodeInfo__[2] | \
         clsCodeGeneratorBase.STACK_COMPLETION[self.__addressMode__ ] )
      self.__bytesToGenerate__-=1
      self.gOperands()
      return

#
#  Generate JSB instructions
#
   def gJsb(self):
#
#     Complete instruction template according to address mode
#
      self.__code__.append(self.__opcodeInfo__[2] | \
         clsCodeGeneratorBase.JSB_COMPLETION[self.__addressMode__ ] )
      self.__bytesToGenerate__-=1
      self.gOperands()
      return
#
#  generate CM, AD, SB, ANM instructions
#
   def gAri(self):
#
#     Complete instruction template according to address mode
#
      self.__code__.append(self.__opcodeInfo__[2] | \
         clsCodeGeneratorBase.ARI_COMPLETION[self.__addressMode__ ] )
      self.__bytesToGenerate__-=1
      self.gOperands()
      return

#
#  Generate LD, ST instructions
#
   def gLdSt(self):
#
#     Complete instruction template according to address mode
#
      self.__code__.append(self.__opcodeInfo__[2] | \
         clsCodeGeneratorBase.LOADSTORE_COMPLETION[self.__addressMode__ ] )
      self.__bytesToGenerate__-=1
      self.gOperands()
      return
#
#  generate code for operands
#
   def gOperands(self):
      SymDict=self.__globVar__.symDict
      op=[]
      for pOperand in self.__parsedOperand__:
#
#         Noting to to for a register
#
          if pOperand.typ== clsParsedOperand.OP_REGISTER:
             continue
#
#         Process label, 1 or 2 bytes long
#
          elif pOperand.typ== clsParsedOperand.OP_LABEL:
             ret=SymDict.get(pOperand.label,self.__lineInfo__)
#
#            apply the size constraint
#
             if ret==None:
                self.addError(MESSAGE.E_SYMNOTFOUND)
                op.append(0)
             else:
                value=ret[1]
                if pOperand.size==2:
                   op.append(value & 0xFF)
                   op.append(value >>8)
                else:
                   op.append(value & 0xFF)
#
#         Number, 1 bytes
#
          elif pOperand.typ==clsParsedOperand.OP_NUMBER:
             number=pOperand.number
             if number > 0xFF:
                self.addError(MESSAGE.E_NUMBERTOOLARGE)
                op.append(0)
             else:
                op.append(number)
          elif pOperand.typ==clsParsedOperand.OP_EXPRESSION:
             result,byteResult, errors=self.__expression__.execute( \
                pOperand, self.__lineInfo__)
             if len(errors)>0:
                self.addError(errors)
             else:
                for b in byteResult:
                   op.append(b)
#
#     Append to instructions, check if we have too many bytes
#     and exceed section boundaries
#
      if len(op) > self.__bytesToGenerate__:
         self.addError(MESSAGE.E_OPEXCEEDSSECTION)
      else:
#
#     fill missing code with zeros (only necessary for faulty statements)
#
         l=len(op)
         while l < self.__bytesToGenerate__:
            self.__code__.append(0)
            l+=1
         self.__code__.extend(op)
      return
#
#  Generate ARP, DRP instructions. Do not generate any code if
#  the parsedOperand is of type OP_INVALID
#
   def gdarp(self):
#     if self.__opcodeLen__==0:
#        return
      code=self.__opcodeInfo__[2]
      if not self.__parsedOperand__[0].isInvalid():
         code|=self.__parsedOperand__[0].registerNumber
      self.__code__.append(code)
      self.__bytesToGenerate__-=1
      return
#
#  Generate all instructions, where the opcode is not modfied by operands
#
   def gdirect(self):
      self.__code__.append(self.__opcodeInfo__[2])
      self.__bytesToGenerate__-=1
      return
#
#  Generate Control Block (capasm only)
#
   def gNam(self):
      if len(self.__parsedOperand__)==0:
         return
      progName=self.__parsedOperand__[0].string
#
#     if we have no program number, create HP-85 style control block
#
      if len(self.__parsedOperand__)==1:
         progName=progName.ljust(6)
#
#     Prog name (6 characters)
         for i in range(0,6):
            self.__code__.append(ord(progName[i]))
#
#     Type (always 2)
#
         self.__code__.append(2)
#
#       19 zeros
#
         for i in range(0,19):
            self.__code__.append(0)
      else:

#
#     generate HP-87 style control block
#
         progNumber=self.__parsedOperand__[1].number
         progName=progName.ljust(10)
#
#     Prog name (4 characters)
#
         for i in range(0,4):
            self.__code__.append(ord(progName[i]))
#
#     Length (2 bytes)
#
         self.__code__.append(self.__globVar__.codeLen & 0xFF)
         self.__code__.append((self.__globVar__.codeLen>>8) & 0xFF)
#
#     Type (always 2)
#
         self.__code__.append(2)
#
#     Program number
#
         self.__code__.append(progNumber)
#
#     Full ascii name
#
         for i in range (0,10):
            self.__code__.append(ord(progName[i]))
#
#     8 zeros
#
         for i in range(0,8):
            self.__code__.append(0)

      return
#
#  Generate HED pseudo op
#
   def gHed(self):
      self.__globVar__.doPageBreak=True
      self.__globVar__.title=self.__parsedOperand__[0].string
      return
#
#  Generate STE instruction (ncas only)
#
   def gSte(self):
      self.__code__.append(0x9D)
      self.__code__.append(0x9C)
#
#  Generate code, top level method
#
   def generate(self,parsedLine):
      self.__pc__= parsedLine.PC
      self.__opcode__=parsedLine.opcode
      self.__opcodeLen__=parsedLine.opcodeLen
      self.__bytesToGenerate__=self.__opcodeLen__
      self.__needsArp__= parsedLine.needsArp
      self.__needsDrp__= parsedLine.needsDrp
      self.__parsedOperand__= parsedLine.parsedOperand
      self.__addressMode__= parsedLine.addressMode
      self.__lineInfo__= parsedLine.lineInfo
      self.__code__=[]
      self.__messages__=[]
      self.__shortList__=False
      if self.__opcode__=="":
         return clsCodeInfo(self.__code__,self.__messages__)
#
#     Generate DRP, ARP if needed
#
      if self.__needsDrp__>=0:
         self.__code__.append(0o100 | self.__needsDrp__)
         self.__bytesToGenerate__-=1
       
      if self.__needsArp__>=0:
         self.__code__.append(0o0 | self.__needsArp__)
         self.__bytesToGenerate__-=1
#
#     Call the opcode specific generator method
#
      self.__opcodeInfo__=OPCODES.get(self.__opcode__)
      if self.__opcodeInfo__ !=[]:
         fname=self.__opcodeInfo__[1]
         getattr(self,fname)()
      return clsCodeInfo(self.__code__, self.__messages__,self.__shortList__)
#
# Parser Base class ----------------------------------------------------
#
# The parseLine method takes the Program Counter, the list of scanned token
# and the original source line as arguments and returns an object of type
# clsParserInfo
#
class clsParserBase(object):

#
#  Initialize parser
#
   def __init__(self,globVar,infile):
      super().__init__()
      self.__globVar__= globVar
      self.__infile__= infile
      self.__hasLcl__=False
      return
#
#  check if a scanned opcode is single- or multibyte
#
   def getByteMode(self):
      c=self.__scannedOpcode__.string[2]
      if c=="B":
         return clsParserInfo.BM_SINGLEBYTE
      elif c=="M":
         return clsParserInfo.BM_MULTIBYTE
      else:
         return clsParserInfo.BM_UNKNOWN     # dead code?
#
#  Add an error to the parser error list
#
   def addError(self,errno):
      if isinstance(errno,list):
         self.__messages__.extend(errno)
         for e in errno:
            if e  < 1000:
               self.__globVar__.errorCount+=1
            else:
               self.__globVar__.warningCount+=1
      else:
         self.__messages__.append(errno)
         if errno  < 1000:
            self.__globVar__.errorCount+=1
         else:
            self.__globVar__.warningCount+=1
      return
#
#  Parse register [+|-] [R|Z] [OctalNumber | # | *]
#  returns object of class clsParsedRegister
#  If signRequired is True, then a missing sign throws an error
#  If notAllowed is True, then we can have a !<RegisterNumber>
#
   def parseRegister(self,token,signRequired,notAllowed):
      string=token.string
      registerTypes="rRxX"
      if notAllowed:
         registerTypes+="!"
      i=0
      sign=""
      if string[i]=="+" or string[i]=="-":
         sign=string[i]
         i+=1
         if not signRequired:
            self.addError(MESSAGE.E_REGISTERSIGN)
            return clsInvalidOperand()
#     typ="R"
      if signRequired and sign=="":
         self.addError(MESSAGE.E_SIGNEDREGISTER)
         return clsInvalidOperand()
      if string[i] in registerTypes:
         typ=string[i].upper()
         i+=1
         if string[i]=="*":
            return clsParsedRegister(sign, typ, 1)
         elif string[i]=="#":
            return clsParsedRegister(sign, typ, clsParsedRegister.R_HASH)
      else:
         self.addError(MESSAGE.E_ILL_REGISTER)
         return clsInvalidOperand()
      number=parseFunc.parseNumber(string[i:])
      if number is None or number > 0o77 or number==1:
         self.addError(MESSAGE.E_ILL_REGISTER)
         return clsInvalidOperand()
      else:
         return clsParsedRegister(sign, typ, number)
#
#  Parse the Label field
#
   def parseLabelField(self):
      label= self.__scannedLabel__.string
      PC=self.__globVar__.PC
      SymDict=self.__globVar__.symDict
      isLcl=False
#
#     Valid label?
#
      if parseFunc.parseLabel(label,self.__globVar__.symNamLen) is None:
         self.addError(MESSAGE.E_ILL_LABEL)
      else:
#
#        check if we have a "real" LCL and not an EQU or DAD
#
         isLcl=True
         if self.__scannedOpcode__ is not None:
            if self.__scannedOpcode__.string=="EQU" or \
               self.__scannedOpcode__.string=="DAD" or \
               self.__scannedOpcode__.string=="ADDR":
               isLcl=False
#
#        real label, enter it into symbol table and invalidate
#        arp, drp context
#
         if isLcl: 
            ret=SymDict.enter(label,clsSymDict.SYM_LCL,PC,2, \
                self.__lineInfo__)
            if ret is not None:
               self.addError(ret)
#           self.__globVar__.arpReg= -1
#           self.__globVar__.drpReg= -1
      return isLcl 

#
#  Parse Data register, which is the first operand. Handle drp elimination
#
   def parseDr(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False,False)
      if not dRegister.isInvalid():
         if dRegister.registerNumber!= clsParsedRegister.R_HASH and \
               self.__globVar__.drpReg!= dRegister.registerNumber:
            self.__needsDrp__= dRegister.registerNumber
            self.__globVar__.drpReg = dRegister.registerNumber
            self.__opcodeLen__+=1
      return dRegister
#
#  Parse Adress register, which is the second operand. Handle arp elimination
#  Note: the push/pop opcodes require AR to have a sign
#
   def parseAr(self,signRequired=False):
      aRegister=self.parseRegister(self.__scannedOperand__[1],signRequired,\
         False)
      if not aRegister.isInvalid():
         if aRegister.registerNumber!= clsParsedRegister.R_HASH  \
            and self.__globVar__.arpReg!= aRegister.registerNumber:
            self.__needsArp__= aRegister.registerNumber
            self.__globVar__.arpReg = aRegister.registerNumber
            self.__opcodeLen__+=1
      return aRegister
#
#  Parse Index register. Handle arp elimination
#
   def parseXr(self,index):
      xRegister=self.parseRegister(self.__scannedOperand__[index],False,\
                 False)
      if not xRegister.isInvalid():
         if xRegister.registerTyp != "X":
            xRegister.typ= clsParsedOperand.OP_INVALID
            self.addError(MESSAGE.E_XREGEXPECTED)
         if xRegister.registerNumber!= clsParsedRegister.R_HASH  \
            and self.__globVar__.arpReg!= xRegister.registerNumber:
            self.__needsArp__= xRegister.registerNumber
            self.__globVar__.arpReg = xRegister.registerNumber
            self.__opcodeLen__+=1
      return(xRegister)
#
#  Parse label as operand
#
   def parseLabelOp(self,opIndex,size=2):
      label=self.__scannedOperand__[opIndex].string
      if self.__scannedOperand__[opIndex].termChar == ",":
         label+=","
      if label[0]=="=":
         label=label[1:]
      if parseFunc.parseLabel(label,self.__globVar__.symNamLen) is None:
         self.addError(MESSAGE.E_ILL_LABELOP)
         return clsInvalidOperand()
      else:
         return clsParsedLabel(label,size)
#
#  Parse expression list
#
   def parseExpressionList(self,idx,numberOfBytesToStore=None):
      parsedOp=[ ]
      opLen=0
      hasErrors=False
#
#     we have at least one operand which is a "="
#
      for opIndex in range(idx,len(self.__scannedOperand__)):
         opString= self.__scannedOperand__[opIndex].string
#
#        if there is no operand, then quit
#
         if opString=="":
            return opLen,parsedOp

         parsedExpression,errors=self.__expression__.parse(opString,None,\
            True)
         if parsedExpression.typ== clsParsedOperand.OP_INVALID:
            self.addError(errors)
            parsedOp.append(clsInvalidOperand())
            hasErrors=True
            continue
         parsedOp.append(parsedExpression)
         if hasErrors:
            opLen=None
         else:
            opLen+=parsedExpression.size
#
#     check, if we exceed the section boundary
#
      if numberOfBytesToStore is not None and opLen is not None:
         if opLen  > numberOfBytesToStore:
            self.addError(MESSAGE.E_OPEXCEEDSSECTION)
            opLen=None
      return [opLen,parsedOp]
#
#  parse single operand expression
#
   def parseSingleExpression(self,opIndex,indicatedSize=None):
      opString= self.__scannedOperand__[opIndex].string
      parsedExpression,errors=self.__expression__.parse(opString, \
             indicatedSize, False)
      if parsedExpression.typ== clsParsedOperand.OP_INVALID:
         self.addError(errors)
      return parsedExpression
      
      
#
#  Include parsing and processing
#
   def pInc(self):
      self.__globVar__.hasIncludes=True
      fileName=parseFunc.parseAnyString(self.__scannedOperand__[0].string)
      if fileName is None:
         self.addError(MESSAGE.E_ILLSTRING)
      else:
         if self.__scannedOpcode__.string=="LNK":
           self.__infile__.openLink(fileName, \
             self.__globVar__.sourceFileDirectory)
         else:
           self.__infile__.openInclude(fileName, \
             self.__globVar__.sourceFileDirectory)

#
#  Parse the HED statement
#
   def pHed(self):
      title=parseFunc.parseQuotedString(self.__scannedOperand__[0].string)
      if title is None:
         self.addError(MESSAGE.E_ILLSTRING)
         return [clsParsedString("")]
      else:
         return [clsParsedString(title)]
#
#  Parse the conditinal assembly pseudo ops
#
   def pCondSet(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        cond.set(pLabel.label)
      return

   def pCondClr(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        cond.clr(pLabel.label)
      return

   def pCondIfDef(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        cond.ifdef(pLabel.label)
      return

   def pCondIfNotDef(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        cond.ifndef(pLabel.label)
      return

   def pCondIfSet(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        ret=cond.ifset(pLabel.label)
        if not ret:
           self.addError(MESSAGE.E_FLAGNOTDEFINED)
      return

   def pCondIfNotSet(self):
      cond=self.__globVar__.condAssembly
      pLabel=self.parseLabelOp(0)
      if pLabel.isInvalid():
         self.addError(MESSAGE.E_ILLFLAGNAME)
      else:
        ret=cond.ifnset(pLabel.label)
        if not ret:
           self.addError(MESSAGE.E_FLAGNOTDEFINED)
      return

   def pCondElse(self):
      cond=self.__globVar__.condAssembly
      if not cond.isOpen():
         self.addError(MESSAGE.E_AIFEIFMISMATCH)
      else:
         cond.els()
      return

   def pCondEndif(self):
      cond=self.__globVar__.condAssembly
      if not cond.isOpen():
         self.addError(MESSAGE.E_AIFEIFMISMATCH)
      else:
         cond.endif()
      return
#
#  Now the opcode specific parsing methods follow. They are specified
#  in the opcode table.
#
#  Parse GTO, we have to fake a LDM R4, DESTINATION_LABEL-1 (LIT DIRECT)
#
   def pGto(self):
#
#     Rearrange the scanned Operand
#
      self.__scannedOperand__= [clsToken("R4",3,""),self.__scannedOperand__[0]]
      self.__opcodeLen__=1
      dRegister=self.parseDr()
      pLabel=self.parseLabelOp(1)
      self.__opcodeLen__+=2
      return[dRegister,pLabel]
  
#
#  Parse BSS
#
   def pBss(self):
      self.__opcodeLen__=0
      opstring= self.__scannedOperand__[0].string
      result,byteResult,errors=self.__expression__.immediate(opstring, 2, \
         self.__lineInfo__)
      if result is not None:
         if result < 0:
            self.addError(MESSAGE.E_ILLVALUE)
         else:
            self.__opcodeLen__=result
      else:
         self.addError(errors)
      return []

#
#  Parse ignored statements
#
   def pNil(self):
      self.__opcodeLen__=0
      return []
#
#  Parse END statement
#
   def pEnd(self):
      self.__globVar__.isFin=True
#
#     check, if we have any open conditionals
#
      if self.__globVar__.condAssembly.isOpen():
         self.addError(MESSAGE.E_AIFEIFMISMATCH)
#
#     check, if we habe any open structural pseudo ops
#
      if not self.__structCtx__.isEmpty():
         self.addError(MESSAGE.E_ILLSTRUCT)


      self.__opcodeLen__=0
      return []
#
#  Parse Data pseudo op
#
   def pData(self):
      opLen,parsedOperand=self.parseExpressionList(0,None)
      if opLen is None:
         return []
      self.__opcodeLen__=opLen
      return(parsedOperand)
#
#  Parse STE pseudo op which expands to a CLE, STE
#
   def pSte(self):
      self.__opcodeLen__=2
      return
#
# Parse IFxx pseudo op
#
   def pIf(self):
      label=self.__structCtx__.structIf(self.__globVar__.arpReg, \
            self.__globVar__.drpReg)
      self.__opcodeLen__+=2
      return [clsParsedLabel(label,2)]
#
# Parse ELSE pseudo op
#
   def pElse(self):
      SymDict=self.__globVar__.symDict
      ret=self.__structCtx__.structElse(self.__globVar__.arpReg, \
            self.__globVar__.drpReg)
      if ret is None:
         self.addError(MESSAGE.E_ILLSTRUCT)
         return [clsInvalidOperand()]
      else:
         label1,label2,oldArpReg,oldDrpReg=ret
#
#        if the last statement was an unconditional jump then eliminate the
#        ELSE condition and insert the destination label of the IF statement
#        here. 
#
         if self.__globVar__.lastOpcodeWasJmp:
            self.__opcodeLen__=0
            ret=SymDict.enter(label1,clsSymDict.SYM_LCL,self.__globVar__.PC,\
                2,self.__lineInfo__)
            invalidateArp,invalidateDrp=self.__structCtx__.removeElse()
            if invalidateArp:
               self.__globVar__.arpReg= -1
            if invalidateDrp:
               self.__globVar__.drpReg= -1
            return []
         self.__opcodeLen__+=2
         ret=SymDict.enter(label1,clsSymDict.SYM_LCL,self.__globVar__.PC+2,\
                2,self.__lineInfo__)
         self.__globVar__.arpReg= oldArpReg
         self.__globVar__.drpReg= oldDrpReg
 
         return [clsParsedLabel(label2,2)]

#
# Parse ENDIF pseudo op
#
   def pEndif(self):
      SymDict=self.__globVar__.symDict
      ret=self.__structCtx__.structEndif(self.__globVar__.arpReg, \
            self.__globVar__.drpReg)
      if ret is None:
         self.addError(MESSAGE.E_ILLSTRUCT)
      else:
         label,oldArpReg, oldDrpReg, invalidateArp,invalidateDrp=ret
         if label=="":
            return
         ret=SymDict.enter(label,clsSymDict.SYM_LCL,self.__globVar__.PC,2, \
                self.__lineInfo__)
         if self.__globVar__.lastOpcodeWasJmp:
            self.__globVar__.arpReg= oldArpReg
            self.__globVar__.drpReg= oldDrpReg
         else:
            if invalidateArp:
               self.__globVar__.arpReg= -1
            if invalidateDrp:
               self.__globVar__.drpReg= -1
      return 
#
# Parse LOOP pseudo op
#
   def pLoop(self):
      SymDict=self.__globVar__.symDict
      label=self.__structCtx__.structLoop()
      ret=SymDict.enter(label,clsSymDict.SYM_LCL,self.__globVar__.PC,2, \
             self.__lineInfo__)
      self.__globVar__.arpReg= -1
      self.__globVar__.drpReg= -1
      return 
#
# Parse EXxx pseudo op
#
   def pEx(self):
      label=self.__structCtx__.structEx()
      if label is None:
         self.addError(MESSAGE.E_ILLSTRUCT)
         return [clsInvalidOperand()]
      self.__opcodeLen__+=2
      return [clsParsedLabel(label,2)]
#
# Parse WHxx pseudo op
#
   def pWh(self):
      SymDict=self.__globVar__.symDict
      ret=self.__structCtx__.structWhile()
      if ret is None:
         self.addError(MESSAGE.E_ILLSTRUCT)
         return [clsInvalidOperand()]
      label1,label2=ret
      if label2 is not None:
         ret=SymDict.enter(label2,clsSymDict.SYM_LCL,self.__globVar__.PC+3,\
            2, self.__lineInfo__)
         self.__globVar__.arpReg= -1
         self.__globVar__.drpReg= -1

      self.__opcodeLen__+=2
      return [clsParsedLabel(label1,2)]
#
# Parse Rxx pseudo op
#
   def pR(self):
      SymDict=self.__globVar__.symDict
#
#     check distance to a previous label, if within range, then 
#     create a label for that location
#
      if self.__globVar__.PC +2 - self.__globVar__.lastRtnAddr <= 128:
         label=self.__structCtx__.newLabel()
         ret=SymDict.enter(label,clsSymDict.SYM_LCL,\
           self.__globVar__.lastRtnAddr, 2, self.__lineInfo__)
      else:
#
#     otherwise try to create a label for a jump to the next rtn statement
#
         label=self.__structCtx__.structR()
      self.__opcodeLen__+=2
      return [clsParsedLabel(label,2)]
#
#  Parse the LOC statement
#
   def pLoc(self):
      self.__opcodeLen__=0
      number=self.parseAddress(0)
      if number==clsParserInfo.ILL_NUMBER:
         return []
#
#     statement only allowed in ABS programs
#
      if not self.__globVar__.hasAbs:
         self.addError(MESSAGE.E_NOTALLOWED_HERE)
         return []
#
#     do nothing if PC is the specified address
#
      if self.__globVar__.PC== number:
         return []
#
#     error if PC is greater than address
#
      if self.__globVar__.PC> number:
         self.addError(MESSAGE.E_PCGREATERTANADDRESS)
      else:
         self.__opcodeLen__= number- self.__globVar__.PC
      return []
#
#  Parse BYT
#
   def pByt(self):
      err=False
      self.__opcodeLen__=0
      pOperand=[]
      for operand in self.__scannedOperand__:
         number=parseFunc.parseNumber(operand.string)
         if number is None or number > 0xFF:
            err=True
            pOperand.append(clsInvalidOperand())
         else:
            pOperand.append(clsParsedNumber(number))
            self.__opcodeLen__+=1
      if err:
         self.addError(MESSAGE.E_ILLNUMBER)
         pOperand=[clsInvalidOperand()]
      return pOperand
#
#  Parse BSZ
#
   def pBsz(self):
      number=self.parseAddress(0)
      if number!=clsParserInfo.ILL_NUMBER:
         self.__opcodeLen__=number
      else:
         self.__opcodeLen__=0
      return []

#
#  Parse ASP, ASC
#
   def pAsc(self):
      pOperand=[]
#
#     check, if we have a number as first operand
#
      firstOperand=self.__scannedOperand__[0]
      if firstOperand.string[0] in "0123456789":
         numChars=parseFunc.parseNumber(firstOperand.string)
         if numChars is None:
            self.addError(MESSAGE.E_ILLNUMBER)
            return pOperand
#
#        search for the comma
#
         if firstOperand.termChar!=",":
            self.addError(MESSAGE.ILLSTRING)
            return pOperand
         strIndex=self.__line__.find(",",firstOperand.position+
            len(firstOperand.string))+1
         string=self.__line__[strIndex:strIndex+numChars]
         if len(string)!= numChars:
            self.addError(MESSAGE.E_ILLSTRING)
            return pOperand
      else:
         string=parseFunc.parseQuotedString(firstOperand.string)
         if string is None:
            self.addError(MESSAGE.E_ILLSTRING)
            return pOperand
      i=0
      err=False
      for c in string:
         i+=1
         n=ord(c)
         if n > 0o174 or n == 0o173 or n < 0o40 :
           err=True
           n=0
         if i==len(string) and self.__scannedOpcode__.string=="ASP":
           n|=0o200
         pOperand.append(clsParsedNumber(n))
      if err or i==0:
         self.addError(MESSAGE.E_ILLSTRING)
      self.__opcodeLen__=len(pOperand)
      return pOperand
#
#  Parse FIN statement
#
   def pFin(self):
      self.__globVar__.isFin=True
#
#     check, if we have any open conditionals
#
      if self.__globVar__.condAssembly.isOpen():
         self.addError(MESSAGE.E_AIFEIFMISMATCH)
      self.__opcodeLen__=0
      return []
#
#  Parse an address
#
   def parseAddress(self,idx):
      address=parseFunc.parseNumber(self.__scannedOperand__[idx].string)
      if address is None:
         self.addError(MESSAGE.E_ILLNUMBER)
         address=clsParserInfo.ILL_NUMBER
      elif address > 0xFFFF:
         self.addError(MESSAGE.E_NUMBERTOOLARGE)
         address=clsParserInfo.ILL_NUMBER
      return address


#
#  Parse literal data lists
#
   def parseLiteralDataList(self,numberOfBytesToStore):
      parsedOp=[ ]
      opLen=0
#
#     we have at least one operand which is a "="
#
      for opIndex in range(1,len(self.__scannedOperand__)):
         opString= self.__scannedOperand__[opIndex].string
        
#
#        first operand, remove "="
#
         if opIndex==1:
            opString=opString[1:]
#
#        if there is no operand, then quit
#
            if opString=="":
               return opLen,parsedOp
#
#       check, if we have a label
#
            if not opString[0] in "0123456789":
#
#        no more operands are allowed
#
               if len(self.__scannedOperand__) > 2:
                  self.addError(MESSAGE.E_ILL_NUMOPERANDS)
                  return opLen,parsedOp
#
#        check, if we have to truncate the label value FIX
#
               if numberOfBytesToStore==1:
                  parsedOp.append(self.parseLabelOp(opIndex,1))
                  opLen+=1
               else:
                  parsedOp.append(self.parseLabelOp(opIndex,2))
                  opLen+=2
#
#       exit, if label
#
               return opLen,parsedOp
#
#      numbers, the code generator checks that they do not exceed 0xFF
#
         
         number=parseFunc.parseNumber(opString)
         if number is None:
            self.addError(MESSAGE.E_ILLNUMBER)
            parsedOp.append(clsInvalidOperand())
            continue
#
#        check, if we exceed the section boundary
#
         if numberOfBytesToStore is not None:
            if opLen+1> numberOfBytesToStore:
               self.addError(MESSAGE.E_OPEXCEEDSSECTION)
               break
         parsedOp.append(clsParsedNumber(number))
         opLen+=1
      
      return opLen,parsedOp
#
#  Parse NAM pseudoop
#  Syntax is NAM unquotedString (HP83/85 only)
#         or NAM octalNumber, unquotedString (HP86/87 only)
#  not supported on HP-75
#
   def pNam(self):
      pOperand=[ ]
#
#     throw error if HP-75
#
      if self.__globVar__.hasNam:
            self.addError(MESSAGE.E_NOTALLOWED_HERE)
            return pOperand
      self.__globVar__.hasNam=True
#
#     ABS only allowed before, if PC >= 0o77777
#
      if self.__globVar__.hasAbs and self.__globVar__.PC<=0o77777:
         self.addError(MESSAGE.E_NOTALLOWED_HERE)
         return pOperand
#
#
#     check if we have two parameters, then decode program number first
#
      pnIndex=0
      progNumber= -1
      allowedLen=6
      if len(self.__scannedOperand__)==2:
         pnIndex=1
         allowedLen=10
      if len(self.__scannedOperand__)==2:
         number=parseFunc.parseNumber(\
            self.__scannedOperand__[0].string)
         if number is None or number > 0o377:
            progNumber=0
            self.addError(MESSAGE.E_ILLNUMBER)
            return pOperand
         else:
            progNumber=number   
#
#     decode and check program name
#      
      progName= self.__scannedOperand__[pnIndex].string
      match=re.fullmatch("[\x20-\x7A|\|]{1,"+str(allowedLen)+"}",progName)
      if not match:
         self.addError(MESSAGE.E_ILL_PROGNAME)
         return pOperand

      self.__opcodeLen__=26
#
      if progNumber >=0:
         return [clsParsedString(progName),clsParsedNumber(progNumber)]
      else:
         return [clsParsedString(progName)]
#
#  Parse JMP relative instructions
#
   def pJrel(self):
      self.__opcodeLen__=2
      return [self.parseLabelOp(0)]
      
#
#  Parse Push-/Pop- instructions
#
   def pStack(self):
      
      parsedOperand=[]
      self.__opcodeLen__=1
#
#     parse DR
#
      dRegister=self.parseDr()
#
#     parse AR (signed!)
#
      aRegister=self.parseAr(True)
      if not aRegister.isInvalid():
         if aRegister.registerSign=="+":
            self.__addressMode__= clsParserInfo.STACK_INCREMENT
         else:
            self.__addressMode__= clsParserInfo.STACK_DECREMENT
      return [dRegister,aRegister]
 
#
#  Parse or/xor- instructions, they have two operands DR and AR
#
   def pOrXr(self):
      self.__opcodeLen__=1
      dRegister=self.parseDr()
      aRegister=self.parseAr()
      if dRegister.isInvalid() or aRegister.isInvalid():
         self.__opcodeLen__=1
      return [dRegister,aRegister]
#
#  Parse instructions without operand. If PAD was encountered set a flag to
#  ensure that the DRP/ARP conetext becomes disabled
#
   def pNoPer(self):
      self.__opcodeLen__=1
      if  self.__opcode__== "PAD":
         self.__globVar__.lastStmtWasPAD=True
      return [ ]

#
#  Parse p1reg instructions, the only operand is the data register
#
   def p1reg(self):
      self.__opcodeLen__=1
      dRegister=self.parseDr()
      if dRegister.isInvalid():
         self.__opcodeLen__=1
      return [dRegister]
#
#  Parse arp instruction, the only operand is the data register
#
   def pArp(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False,True)
      self.__opcodeLen__=1
      if not dRegister.isInvalid():
         self.__globVar__.arpReg= dRegister.registerNumber
         if dRegister.registerTyp=="!":
            self.__opcodeLen__=0
      return [dRegister]
#
#  Parse drp instruction, the only operand is the data register
#
   def pDrp(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False,True)
      self.__opcodeLen__=1
      if not dRegister.isInvalid():
         self.__globVar__.drpReg= dRegister.registerNumber
         if dRegister.registerTyp=="!":
            self.__opcodeLen__=0
      return [dRegister]
#
#  Parse line, top level method
#
   def parseLine(self,scannedLine,line):
      self.__messages__= [ ]
      self.__scannedLine__=scannedLine
      self.__scannedLineNumber__= scannedLine[0]
      self.__scannedLabel__= scannedLine[1]
      self.__line__=line
      self.__scannedOpcode__=self.__scannedLine__[2]
      self.__scannedOperand__= self.__scannedLine__[3]

      self.__parsedOperand__= [ ]
      self.__opcodeLen__=0
      self.__needsArp__= -1
      self.__needsDrp__= -1
      self.__addressMode__= clsParserInfo.AM_REGISTER_IMMEDIATE
      PC=self.__globVar__.PC
      self.__lineInfo__=self.__infile__.getLineInfo()

      condAssemblyIsSuppressed=self.__globVar__.condAssembly.isSuppressed()
#
#     Parse lineNumber, if we have one (may be not a valid integer)
#
      if self.__scannedLineNumber__ is not None:
         if parseFunc.parseDecimal( \
                    self.__scannedLineNumber__.string) is None:
            self.addError(MESSAGE.E_ILL_LINENUMBER)
#
#     If we have a label field, parse it and enter label into symbol table
#
      if self.__scannedLabel__ is not None and not condAssemblyIsSuppressed:
         self.__hasLcl__=self.parseLabelField()
#
#     Return if we have no opcode nor operands
#
      if self.__scannedOpcode__ is None:
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__)
#
#     Return if we have a comment ! in the opcode field
#
      if self.__scannedOpcode__.string=="!":
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__)

      self.__opcode__=self.__scannedOpcode__.string
#
#     Get information how to parse the opcode
# 
      self.__opcodeInfo__=OPCODES.get(self.__opcode__)
#
#        return error information, if opcode not found
#
      if self.__opcodeInfo__ ==[]:
         self.__hasLcl__=False
         self.addError(MESSAGE.E_ILL_OPCODE)
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
#
#     We have to check the conditional assembly status,
#     treat the line as comment if we are in False state
#     except we have an conditional assembly statement
#
      if self.__opcodeInfo__[7]:
         condAssemblyIsSuppressed=False
      if condAssemblyIsSuppressed: 
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__)
#
#     Invalidate arp, drp context if the previous statement was a subroutine 
#     call or PAD
#
      if self.__globVar__.lastStmtWasPAD or self.__globVar__.lastStmtWasJSB:
         self.__globVar__.arpReg= -1
         self.__globVar__.drpReg= -1
         self.__globVar__.lastStmtWasPAD=False
         self.__globVar__.lastStmtWasJSB=False

#
#     Check number of params for the opcode
#
      if len(self.__scannedOperand__)< self.__opcodeInfo__[3]:
            self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                           self.__line__)
      if self.__opcodeInfo__[4] != OPCODES.NUM_OPERANDS_ANY:
         if len(self.__scannedOperand__)> self.__opcodeInfo__[4]:
            self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
#
#     Invalidate arp/drp context if we the following conditions are met:
#     - the opcode generates executable code
#     - the opcode is no unconditional jump
#     - a local label exists for that line 
#
      if not self.__opcodeInfo__[6]:
         if self.__hasLcl__ and not self.__opcodeInfo__[5]:
             self.__globVar__.arpReg= -1
             self.__globVar__.drpReg= -1
      self.__hasLcl__=False
#
#     Call operand parse method
#
      fname=self.__opcodeInfo__[0]
      self.__parsedOperand__= getattr(self,fname)()
#
#     Set flag, if the parsed operand is an unconditional JMP
#     This flag is needed for parsing an immediately following ELSE
#     statement which will eliminate the jump instructions to the
#     corresponding ENDIF
#
      if self.__opcodeInfo__[5]:
         self.__globVar__.lastOpcodeWasJmp=True
      else:
         if not self.__opcodeInfo__[6]:
            self.__globVar__.lastOpcodeWasJmp=False
#
#     return parsed statement information
#
      return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
             self.__line__, \
             self.__opcode__,self.__opcodeLen__, self.__parsedOperand__, \
             self.__needsArp__,self.__needsDrp__,self.__addressMode__)

