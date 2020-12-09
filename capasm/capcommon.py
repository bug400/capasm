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
#
import re,os,sys,importlib,datetime
from pathlib import Path
#
# Program Constants -----------------------------------------------------
#
CAPASM_VERSION="Version 1.0.0"
CAPASM_VERSION_DATE="December 2020"

#
# CAPASM custom exception -----------------------------------------------
# The assembler raises this exception, if a fatal error occurred
#
class capasmError(Exception):
   def __init__(self,msg):
      super().__init__()
      self.msg= msg
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
#  Parse binar number
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
class basicOPCODES(object):

   NUM_OPERANDS_ANY=-1
#
#    Each opcode is associated to a list with the items:
#    - parse method
#    - code generator method
#    - instruction or instruction template which must be completed later
#    - number of operand parameters min
#    - number of operand parameters max
#
   basicOpcodeDict= {
   "ARP" : ["pArp","gdarp",0o0,1,1,False,False],
   "DRP" : ["pDrp","gdarp",0o100,1,1,False,False],
   "ELB" : ["p1reg","gdirect",0o200,1,1,False,False],
   "ELM" : ["p1reg","gdirect",0o201,1,1,False,False],
   "ERB" : ["p1reg","gdirect",0o202,1,1,False,False],
   "ERM" : ["p1reg","gdirect",0o203,1,1,False,False],
   "LLB" : ["p1reg","gdirect",0o204,1,1,False,False],
   "LLM" : ["p1reg","gdirect",0o205,1,1,False,False],
   "LRB" : ["p1reg","gdirect",0o206,1,1,False,False],
   "LRM" : ["p1reg","gdirect",0o207,1,1,False,False],
   "ICB" : ["p1reg","gdirect",0o210,1,1,False,False],
   "ICM" : ["p1reg","gdirect",0o211,1,1,False,False],
   "DCB" : ["p1reg","gdirect",0o212,1,1,False,False],
   "DCM" : ["p1reg","gdirect",0o213,1,1,False,False],
   "TCB" : ["p1reg","gdirect",0o214,1,1,False,False],
   "TCM" : ["p1reg","gdirect",0o215,1,1,False,False],
   "NCB" : ["p1reg","gdirect",0o216,1,1,False,False],
   "NCM" : ["p1reg","gdirect",0o217,1,1,False,False],
   "TSB" : ["p1reg","gdirect",0o220,1,1,False,False],
   "TSM" : ["p1reg","gdirect",0o221,1,1,False,False],
   "CLB" : ["p1reg","gdirect",0o222,1,1,False,False],
   "CLM" : ["p1reg","gdirect",0o223,1,1,False,False],
   "ORB" : ["pOrXr","gdirect",0o224,2,2,False,False],
   "ORM" : ["pOrXr","gdirect",0o225,2,2,False,False],
   "XRB" : ["pOrXr","gdirect",0o226,2,2,False,False],
   "XRM" : ["pOrXr","gdirect",0o227,2,2,False,False],
   "BIN" : ["pNoPer","gdirect",0o230,0,0,False,False],
   "BCD" : ["pNoPer","gdirect",0o231,0,0,False,False],
   "SAD" : ["pNoPer","gdirect",0o232,0,0,False,False],
   "DCE" : ["pNoPer","gdirect",0o233,0,0,False,False],
   "ICE" : ["pNoPer","gdirect",0o234,0,0,False,False],
   "CLE" : ["pNoPer","gdirect",0o235,0,0,False,False],
   "PAD" : ["pNoPer","gdirect",0o237,0,0,False,False],
   "LDB" : ["pLdSt","gLdSt",0o240,2,10,False,False],
   "LDBI" : ["pLdSt","gLdSt",0o240,2,NUM_OPERANDS_ANY,False,False],
   "LDBD" : ["pLdSt","gLdSt",0o240,2,NUM_OPERANDS_ANY,False,False],
   "LDM" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False],
   "LDMI" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False],
   "LDMD" : ["pLdSt","gLdSt",0o241,2,NUM_OPERANDS_ANY,False,False],
   "STB" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False],
   "STBI" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False],
   "STBD" : ["pLdSt","gLdSt",0o242,2,NUM_OPERANDS_ANY,False,False],
   "STM" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False],
   "STMI" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False],
   "STMD" : ["pLdSt","gLdSt",0o243,2,NUM_OPERANDS_ANY,False,False],
   "CMB"  : ["pAri","gAri",0o300,2,NUM_OPERANDS_ANY,False,False],
   "CMM"  : ["pAri","gAri",0o301,2,NUM_OPERANDS_ANY,False,False],
   "CMBD"  : ["pAri","gAri",0o300,2,NUM_OPERANDS_ANY,False,False],
   "CMMD"  : ["pAri","gAri",0o301,2,NUM_OPERANDS_ANY,False,False],
   "ADB"  : ["pAri","gAri",0o302,2,NUM_OPERANDS_ANY,False,False],
   "ADM"  : ["pAri","gAri",0o303,2,NUM_OPERANDS_ANY,False,False],
   "ADBD"  : ["pAri","gAri",0o302,2,NUM_OPERANDS_ANY,False,False],
   "ADMD"  : ["pAri","gAri",0o303,2,NUM_OPERANDS_ANY,False,False],
   "SBB"  : ["pAri","gAri",0o304,2,NUM_OPERANDS_ANY,False,False],
   "SBM"  : ["pAri","gAri",0o305,2,NUM_OPERANDS_ANY,False,False],
   "SBBD"  : ["pAri","gAri",0o304,2,NUM_OPERANDS_ANY,False,False],
   "SBMD"  : ["pAri","gAri",0o305,2,NUM_OPERANDS_ANY,False,False],
   "ANM"  : ["pAri","gAri",0o307,2,NUM_OPERANDS_ANY,False,False],
   "ANMD"  : ["pAri","gAri",0o307,2,NUM_OPERANDS_ANY,False,False],
   "JSB"  : ["pJsb","gJsb",0o306,1,2,False,False],
   "POBD" : ["pStack","gStack",0o340,2,2,False,False],
   "POMD" : ["pStack","gStack",0o341,2,2,False,False],
   "PUBD" : ["pStack","gStack",0o344,2,2,False,False],
   "PUMD" : ["pStack","gStack",0o345,2,2,False,False],
   "POBI" : ["pStack","gStack",0o350,2,2,False,False],
   "POMI" : ["pStack","gStack",0o351,2,2,False,False],
   "PUBI" : ["pStack","gStack",0o354,2,2,False,False],
   "PUMI" : ["pStack","gStack",0o355,2,2,False,False],
#
#  Jump and conditional jump Instructions
#
   "JMP"  : ["pJrel","gJrel",0o360,1,1,True,0],
   "JNO"  : ["pJrel","gJrel",0o361,1,1,False,False],
   "JOD"  : ["pJrel","gJrel",0o362,1,1,False,False],
   "JEV"  : ["pJrel","gJrel",0o363,1,1,False,False],
   "JNG"  : ["pJrel","gJrel",0o364,1,1,False,False],
   "JPS"  : ["pJrel","gJrel",0o365,1,1,False,False],
   "JNZ"  : ["pJrel","gJrel",0o366,1,1,False,False],
   "JZR"  : ["pJrel","gJrel",0o367,1,1,False,False],
   "JEN"  : ["pJrel","gJrel",0o370,1,1,False,False],
   "JEZ"  : ["pJrel","gJrel",0o371,1,1,False,False],
   "JNC"  : ["pJrel","gJrel",0o372,1,1,False,False],
   "JCY"  : ["pJrel","gJrel",0o373,1,1,False,False],
   "JLZ"  : ["pJrel","gJrel",0o374,1,1,False,False],
   "JLN"  : ["pJrel","gJrel",0o375,1,1,False,False],
   "JRZ"  : ["pJrel","gJrel",0o376,1,1,False,False],
   "JRN"  : ["pJrel","gJrel",0o377,1,1,False,False],
   }

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
      E_MISSING_FIN: "Missing FIN statement",
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
# Conditional assembling class ---------------------------------------------
#
class clsConditionalAssembly(object):

   def __init__(self):
    
      super().__init__()
      self.__stack__= []
      self.__flags__ = { }
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
      return self.__stack__[-1]
#
#  eif, pop condition from stack
#
   def eif(self):
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
#  aif, push new condition on stack
#
   def aif(self,name):
      try:
        self.__stack__.append(self.__flags__[name]==False)
        return True
      except KeyError:
        return False
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
      s=self.formatAddress(pc)+" "
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
#     of code. i is the index of the current byte
#
      j=0
      i=numCode
      s=""
      while i < codeLen:
         if j==0:
            pc+=numCode
            s=self.formatAddress(pc)+" "
         s+=self.formatCode(codeInfo.code[i])+" "
         j+=1
         if j==numCode:
            self.wrL(s)
            j=0
         i+=1
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
