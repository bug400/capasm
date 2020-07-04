#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This module contains the assembler for the capricorn cpu. 
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
#-------------------------------------------------------------------
#
# Changelog
# 18.05.2020 jsi
# - start changelog
# 19.05.2020 jsi
# - changed number parsing to static methods
# 21.05.2020 jsi
# - renamed parseLiteralOp to parseLiteralDataList
# 22.05.2020 jsi
# - raise custom exception on fatal error
# - fixed output of short symbol table
# - allow comment text to follow immediately the comment sign "!"
# - development version 0.9.1
# 24.05.2020 jsi
# - do not invalidate arp, drp conext on EQU or DAD pseudo ops
# 25.05.2020 jsi
# - store default bin file in the local directory
# 26.05.2020 jsi
# - add return value for assemble method
# 30.05.2020 jsi
# - beta version 0.9.5
# - improved help text
# 30.06.2020 jsi
# - beta version 0.9.6
# - HP86/87 compatible NAM statement
# - jump relative GTO
# - bug fixes
# - conditional assembly support
# - include and link file support
# 04.07.2020 jsi
# - allow quoted strings for INC and LNK files
# - use path of assembler source files for INC and LNK files, if there 
#   is only a file name specified

import argparse,sys,os,datetime,importlib,re
from pathlib import Path
#
# Program Constants -----------------------------------------------------
#
CAPASM_VERSION="Version 0.9.6"
CAPASM_VERSION_DATE="July 2020"
#
# CAPASM custom exception -----------------------------------------------
# The assembler raises this exception, if a fatal error occurred
#
class capasmError(Exception):
   def __init__(self,msg):
      super().__init__()
      self.msg= msg
#
# Static classes below only contain read only data
#
# Static class for the bytes to store check --------------------------------
#
# Returns the number of bytes that can be stored according to the
# data register and the design of the CPU register bank
#
class BYTESTOSTORE(object):

   UNKNOWN_BYTESTOSTORE=-1

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

   @staticmethod 
   def numBytes(reg):
      if reg<0:
         return BYTESTOSTORE.UNKNOWN_BYTESTOSTORE
      else:
         return BYTESTOSTORE.__dictBytesToStore__[reg]
#
#  Static class for the opcode dictionary ----------------------------------
#
class OPCODES(object):
#
#    Each opcode is associated to a list with the items:
#    - parse method
#    - code generator method
#    - instruction or instruction template which must be completed later
#    - number of operand parameters min
#    - number of operand parameters max
#
   __opcodedict__= {
   "ARP" : ["pArp","gdarp",0o0,1,1],
   "DRP" : ["pDrp","gdarp",0o100,1,1],
   "ELB" : ["p1reg","gdirect",0o200,1,1],
   "ELM" : ["p1reg","gdirect",0o201,1,1],
   "ERB" : ["p1reg","gdirect",0o202,1,1],
   "ERM" : ["p1reg","gdirect",0o203,1,1],
   "LLB" : ["p1reg","gdirect",0o204,1,1],
   "LLM" : ["p1reg","gdirect",0o205,1,1],
   "LRB" : ["p1reg","gdirect",0o206,1,1],
   "LRM" : ["p1reg","gdirect",0o207,1,1],
   "ICB" : ["p1reg","gdirect",0o210,1,1],
   "ICM" : ["p1reg","gdirect",0o211,1,1],
   "DCB" : ["p1reg","gdirect",0o212,1,1],
   "DCM" : ["p1reg","gdirect",0o213,1,1],
   "TCB" : ["p1reg","gdirect",0o214,1,1],
   "TCM" : ["p1reg","gdirect",0o215,1,1],
   "NCB" : ["p1reg","gdirect",0o216,1,1],
   "NCM" : ["p1reg","gdirect",0o217,1,1],
   "TSB" : ["p1reg","gdirect",0o220,1,1],
   "TSM" : ["p1reg","gdirect",0o221,1,1],
   "CLB" : ["p1reg","gdirect",0o222,1,1],
   "CLM" : ["p1reg","gdirect",0o223,1,1],
   "ORB" : ["pOrXr","gdirect",0o224,2,2],
   "ORM" : ["pOrXr","gdirect",0o225,2,2],
   "XRB" : ["pOrXr","gdirect",0o226,2,2],
   "XRM" : ["pOrXr","gdirect",0o227,2,2],
   "BIN" : ["pNoPer","gdirect",0o230,0,0],
   "BCD" : ["pNoPer","gdirect",0o231,0,0],
   "SAD" : ["pNoPer","gdirect",0o232,0,0],
   "DCE" : ["pNoPer","gdirect",0o233,0,0],
   "ICE" : ["pNoPer","gdirect",0o234,0,0],
   "CLE" : ["pNoPer","gdirect",0o235,0,0],
   "RTN" : ["pNoPer","gdirect",0o236,0,0],
   "PAD" : ["pNoPer","gdirect",0o237,0,0],
   "LDB" : ["pLdSt","gLdSt",0o240,2,10],
   "LDBI" : ["pLdSt","gLdSt",0o240,2,10],
   "LDBD" : ["pLdSt","gLdSt",0o240,2,10],
   "LDM" : ["pLdSt","gLdSt",0o241,2,10],
   "LDMI" : ["pLdSt","gLdSt",0o241,2,10],
   "LDMD" : ["pLdSt","gLdSt",0o241,2,10],
   "STB" : ["pLdSt","gLdSt",0o242,2,10],
   "STBI" : ["pLdSt","gLdSt",0o242,2,10],
   "STBD" : ["pLdSt","gLdSt",0o242,2,10],
   "STM" : ["pLdSt","gLdSt",0o243,2,10],
   "STMI" : ["pLdSt","gLdSt",0o243,2,10],
   "STMD" : ["pLdSt","gLdSt",0o243,2,10],
   "CMB"  : ["pAri","gAri",0o300,2,9],
   "CMM"  : ["pAri","gAri",0o301,2,9],
   "CMBD"  : ["pAri","gAri",0o300,2,9],
   "CMMD"  : ["pAri","gAri",0o301,2,9],
   "ADB"  : ["pAri","gAri",0o302,2,9],
   "ADM"  : ["pAri","gAri",0o303,2,9],
   "ADBD"  : ["pAri","gAri",0o302,2,9],
   "ADMD"  : ["pAri","gAri",0o303,2,9],
   "SBB"  : ["pAri","gAri",0o304,2,9],
   "SBM"  : ["pAri","gAri",0o305,2,9],
   "SBBD"  : ["pAri","gAri",0o304,2,9],
   "SBMD"  : ["pAri","gAri",0o305,2,9],
   "ANM"  : ["pAri","gAri",0o307,2,9],
   "ANMD"  : ["pAri","gAri",0o307,2,9],
   "JSB"  : ["pJsb","gJsb",0o306,1,2],
   "POBD" : ["pStack","gStack",0o340,2,2],
   "POMD" : ["pStack","gStack",0o341,2,2],
   "PUBD" : ["pStack","gStack",0o344,2,2],
   "PUMD" : ["pStack","gStack",0o345,2,2],
   "POBI" : ["pStack","gStack",0o350,2,2],
   "POMI" : ["pStack","gStack",0o351,2,2],
   "PUBI" : ["pStack","gStack",0o354,2,2],
   "PUMI" : ["pStack","gStack",0o355,2,2],
   "JMP"  : ["pJrel","gJrel",0o360,1,1],
   "JNO"  : ["pJrel","gJrel",0o361,1,1],
   "JOD"  : ["pJrel","gJrel",0o362,1,1],
   "JEV"  : ["pJrel","gJrel",0o363,1,1],
   "JNG"  : ["pJrel","gJrel",0o364,1,1],
   "JPS"  : ["pJrel","gJrel",0o365,1,1],
   "JNZ"  : ["pJrel","gJrel",0o366,1,1],
   "JZR"  : ["pJrel","gJrel",0o367,1,1],
   "JEN"  : ["pJrel","gJrel",0o370,1,1],
   "JEZ"  : ["pJrel","gJrel",0o371,1,1],
   "JNC"  : ["pJrel","gJrel",0o372,1,1],
   "JCY"  : ["pJrel","gJrel",0o373,1,1],
   "JLZ"  : ["pJrel","gJrel",0o374,1,1],
   "JLN"  : ["pJrel","gJrel",0o375,1,1],
   "JRZ"  : ["pJrel","gJrel",0o376,1,1],
   "JRN"  : ["pJrel","gJrel",0o377,1,1],
   "ABS"  : ["pAbs","gNil",0,1,2],
   "FIN"  : ["pFin","gNil",0,0,0],
   "LST"  : ["pNil","gNil",0,0,0],
   "UNL"  : ["pNil","gNil",0,0,0],
   "ASC"   : ["pAsc","gData",0,1,1],
   "ASP"   : ["pAsc","gData",0,1,1],
   "NAM"   : ["pNam","gNam",0,1,2],
   "BSZ"   : ["pBsz","gGenZ",0,1,1],
   "BYT"   : ["pByt","gData",0,1,256],
   "DAD"   : ["pEqu","gNil",0,1,1],
   "DEF"   : ["pDef","gDef",0,1,1],
   "EQU"   : ["pEqu","gNil",0,1,1],
   "GTO"   : ["pGto","gGto",0,1,1],
   "VAL"   : ["pDef","gDef",0,1,1],
   "ORG"   : ["pOrg","gNil",0,1,1],
   "SET"   : ["pCond","gNil",0,1,1],
   "CLR"   : ["pCond","gNil",0,1,1],
   "AIF"   : ["pCond","gNil",0,1,1],
   "EIF"   : ["pCond","gNil",0,0,0],
   "ELS"   : ["pCond","gNil",0,0,0],
   "INC"   : ["pInc","gNil",0,1,1],
   "LNK"   : ["pInc","gNil",0,1,1],
   }

   @staticmethod 
   def get(opcode):
      lookUp=opcode
      if lookUp in OPCODES.__opcodedict__.keys():
         return OPCODES.__opcodedict__[lookUp]
      else:
         return []
#
# Error Messages static class --------------------------------------------
#
class ERROR(object):
   E_ILL_OPCODE = 0
   E_ILL_REGISTER= 1
   E_ILL_LABEL = 2
   E_DUP_LABEL = 3
   E_ILL_NUMOPERANDS= 4
   E_REGISTERSIGN=5
   E_XREGEXPECTED=6
   E_ILLADDRESSMODE=7
   E_LBLNOTFOUND=8
   E_NUMBERTOOLARGE=9
   E_OPEXCEEDSSECTION=10
   E_SIGNEDREGISTER=11
   E_ILLNUMBER=12
   E_ILLSTRING=13
   E_ILL_LABELOP=14
   E_ILL_LINENUMBER=15
   E_NOTALLOWED_HERE=16
   E_ILL_PROGNAME=17
   E_GLOBALSYMBOL_REDEFINED=18
   E_RELJUMP_TOOLARGE=19
   E_ILL_LITOPERAND=20
   E_ILL_LITERALLENGTH=21
   E_RHASH_LITERAL=22
   E_MISSING_LABEL=23
   E_UNSUPPORTED=24
   E_FLAGNOTDEFINED=25
   E_AIFEIFMISMATCH=26
   E_ILLFLAGNAME=27
   E_MISSING_FIN=28
   E_ROM_EXPECTED=29

   messages= {
      E_ILL_OPCODE : "Illegal opcode or pseudo opcode",
      E_ILL_REGISTER: "Illegal register",
      E_ILL_LABEL: "Illegal label in label field",
      E_DUP_LABEL: "Label in label field is already defined",
      E_ILL_NUMOPERANDS: "Illegal number of operands",
      E_REGISTERSIGN: "+/- not allowed in register definition",
      E_XREGEXPECTED: "X register expected as second operand",
      E_ILLADDRESSMODE: "Illegal address mode",
      E_LBLNOTFOUND: "Label not found",
      E_NUMBERTOOLARGE: "Number too large",
      E_OPEXCEEDSSECTION: "Literal or label data exceed section boundary",
      E_SIGNEDREGISTER: "+/- required for address register",
      E_ILLNUMBER: "Illegal number",
      E_ILLSTRING: "Illagal string",
      E_ILL_LABELOP: "Illegal label in operand field",
      E_ILL_LINENUMBER: "Illegal line number",
      E_NOTALLOWED_HERE: "Pseudo opcode not allowed here",
      E_ILL_PROGNAME: "Illegal program name",
      E_GLOBALSYMBOL_REDEFINED: "Redefinition of a global symbol",
      E_RELJUMP_TOOLARGE: "Relative jump too large",
      E_ILL_LITOPERAND: "Illegal literal operand",
      E_ILL_LITERALLENGTH: "Illegal byte length of literal operand",
      E_RHASH_LITERAL: "Dangerous R#, cannot check section boundary",
      E_MISSING_LABEL: "Missing label in label field",
      E_UNSUPPORTED: "Not supported for this machine",
      E_FLAGNOTDEFINED: "Flag not defined",
      E_AIFEIFMISMATCH: "AIF/EIF mismatch",
      E_ILLFLAGNAME: "Illegal flag name",
      E_MISSING_FIN: "Missing FIN statement",
      E_ROM_EXPECTED: "ROM expected",
   }

#
#  Get message text for a message number
#
   def getMsg(msgno):
      return ERROR.messages[msgno]
#
# Fatal error handler (I/O errors etc.). Raise custom exception
#
   @staticmethod
   def fatalError(msg):
     raise capasmError(msg)

#
# Static class for number and label parsing ----------------------------------
#
class parseFunc(object):

#  Parse quoted string
#
   @staticmethod
   def parseQuotedString(string):
      if string[0] != "'" and string[0] != '"':
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
      if string[0]=="'" or string[0]=='"':
         return parseFunc.parseQuotedString(string)
      else:
         return string
#
#  Parse label
#
   @staticmethod
   def parseLabel(string,length):
      match=re.fullmatch("[A-Za-z][A-Za-z0-9_$\+\-\.#/?\(\!\&)=:<>\|@*^]{0,"+\
           str(length)+"}",string)
      if match:
         return string
      else:
         return None
      
#
#  Parse decimal number (without D at the end, e.g. line numbers)
#
   @staticmethod
   def parseDecimal(string):
      retVal=0
      for c in string:
         if c in "0123456789":
            retVal=retVal*10 + ord(c)-ord("0")
         else:
            return None
      return retVal
#
#  Parse octal number
#
   @staticmethod
   def parseOctal(string):
         retVal=0
         for c in string:
            if c in "01234567":
               retVal=retVal*8 + ord(c)-ord("0")
            else:
               return None
         return retVal
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
#  Parse a number, guess the type from the type attribute character at the end
#  
   @staticmethod
   def parseNumber(string):
      retval=0
      if string[-1]=="D" or string[-1]=="d":
         return parseFunc.parseDecimal(string[:-1])
      elif string[-1]=="C" or string[-1]=="c":
         return parseFunc.parseBCD(string[:-1])
      elif string[-1] in "01234567":
         return parseFunc.parseOctal(string)
      else:
         return None
#
# Non static classes
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
   dictSymbolTypes= { SYM_DAD: "DAD", SYM_EQU: "EQU", SYM_LCL: "LCL" }
#
#  Line Info that idicates a global symbol
#
   LN_GLOBAL= None

   def __init__(self,machine,extendedChecks):
      super().__init__()
      
      self.__extendedChecks__=extendedChecks
      self.__symbols__= { }
#
#  Load global symbols for the selected machine
#
      globalModuleName=".globals"+machine
      self.__globalSyms__=importlib.import_module(globalModuleName, \
                              package='capasm')
#
#  Enter new symbol, we have to check for duplicates in the global symbol
#  dictionary and this dictionary as well. Returns None if we have no
#  error or an error number otherwise
#
   def enter(self,name,typ,value,lineInfo):
#
#      Check global dict, if redefinition of global symbols is not allowed
#
       if  self.__extendedChecks__:
          ret=self.__globalSyms__.globalSymbols.get(name)
          if ret is not None:
             return ERROR.E_GLOBALSYMBOL_REDEFINED
#
#      Check our own dict
#
       if name in self.__symbols__.keys():
          return ERROR.E_DUP_LABEL
       else:
          self.__symbols__[name]=[typ,value,lineInfo,[]]
       return None
#
#  Get a symbol. We look first in our own symbol dictionary. If the
#  symbol is not found, try the Globals dictionary. If a symbol was
#  found in the Globals dictionary the insert it into the local dict.
#
   def get(self,name,lineInfo=None):
      try:
         ret=self.__symbols__[name]
         if lineInfo is not None:
            lines=ret[3]
            lines.append(lineInfo)
            self.__symbols__[name]=[ret[0],ret[1],ret[2], lines]
         return ret
      except KeyError:
         ret=self.__globalSyms__.globalSymbols.get(name)
         if ret:
            self.enter(name,ret[0],ret[1],clsSymDict.LN_GLOBAL)
         return ret
#
#  Get a list of all symbols in the local dictionary
# 
   def getList(self):
      return list(self.__symbols__.keys())
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
      self.machine= "85"             # machine type
      self.sourceFileDirectory=""    # directory of source file if specified
      self.condAssembly= None        # conditional assembly object
      self.symDict= None             # global symbol dictionary object
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

   def __init__(self):
      super().__init__()
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
         if char=='"' or char=="'":
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
         if tok.string[0]!= "!":
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
      if tok.string[0]=="!":
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
         if tok.string[0]=="!":
            break
#
#        Comma, continue loop
#
         if tok.string!=",":
            scannedOperand.append(tok)
         tok= self.scanTok(",")
      return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
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

   def __init__(self,typ=OP_INVALID):
      self.typ=typ

   def __repr__(self): # pragma: no cover
      return("clsParsedOperand (generic)")
#
#  Invalid operand, operand that had issues during parsing
#
class clsInvalidOperand(clsParsedOperand):
   
   def __init__(self):
      super().__init__(clsParsedOperand.OP_INVALID)

   def __repr__(self): # pragma: no cover
      return("clsParsedOperand (invalid)")

#
#  Valid number operand (syntax checked)
#
class clsParsedNumber(clsParsedOperand):
   
   def __init__(self,number):
      super().__init__(clsParsedOperand.OP_NUMBER)
      self.number=number

   def __repr__(self): # pragma: no cover
      return ("clsParsedNumber number= {:o}".format(self.number))
#
# Valid string operand (syntax checked)
#
class clsParsedString(clsParsedOperand):
   
   def __init__(self,string):
      super().__init__(clsParsedOperand.OP_NUMBER)
      self.string=string

   def __repr__(self): # pragma: no cover
      return ("clsParsedString string= {:s}".format(self.string))

#
#  Valid label operand (syntax checked)
#
class clsParsedLabel(clsParsedOperand):

   def __init__(self,label):
      super().__init__(clsParsedOperand.OP_LABEL)
      self.label=label

   def __repr__(self): # pragma: no cover
      return ("clsParsedLabel label= "+self.label)
#
# Valid register operand (syntax checked)
#
class clsParsedRegister(clsParsedOperand):

   R_HASH=-1
   R_ILLEGAL=-2

   def __init__(self,registerSign="", registerTyp="", registerNumber=R_ILLEGAL):
      super().__init__(clsParsedOperand.OP_REGISTER)
      self.registerSign=registerSign      # sign of the register "+", "-" or ""
      self.registerTyp=registerTyp        # register typ "R" or "X"
      self.registerNumber=registerNumber  # decimal register number
                                          # a * results in register number 1
                                          # a # results in register number
                                          # R_HASH
                                          # if the number is R_ILLEGAL then
                                          # we have an invalid register

   def __repr__(self): # pragma: no cover
      return ("clsParsedRegister object '{:s}' {:s} '{:d}'".format(self.registerSign, self.registerTyp,self.registerNumber))

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
# Parser ---------------------------------------------------------------
#
# The parseLine method takes the Program Counter, the list of scanned token
# and the original source line as arguments and returns an object of type
# clsParserInfo
#
class clsParser(object):

#
#  Initialize parser
#
   def __init__(self,globVar,infile):
      super().__init__()
      self.__globVar__= globVar
      self.__infile__= infile
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
      self.__messages__.append(errno)
      self.__globVar__.errorCount+=1
      return
#
#  Parse register [+|-] [R|Z] [OctalNumber | # | *]
#  returns object of class clsParsedRegister
#  If signRequired is True, then a missing sign throws an error
#
   def parseRegister(self,token,signRequired):
      string=token.string
      i=0
      sign=""
      if string[i]=="+" or string[i]=="-":
         sign=string[i]
         i+=1
         if not signRequired:
            self.addError(ERROR.E_REGISTERSIGN)
            return clsInvalidOperand()
      typ="R"
      if signRequired and sign=="":
         self.addError(ERROR.E_SIGNEDREGISTER)
         return clsInvalidOperand()
      if string[i] in "rRxX":
         typ=string[i].upper()
         i+=1
         if string[i]=="*":
            return clsParsedRegister(sign, typ, 1)
         elif string[i]=="#":
            return clsParsedRegister(sign, typ, clsParsedRegister.R_HASH)
      number=parseFunc.parseOctal(string[i:])
      if number is None or number > 0o77 or number==1:
         self.addError(ERROR.E_ILL_REGISTER)
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
#
#     Valid label?
#
      if parseFunc.parseLabel(label,self.__globVar__.symNamLen) is None:
         self.addError(ERROR.E_ILL_LABEL)
      else:
#
#        check if we have a "real" LCL and not an EQU or DAD
#
         isLcl=True
         if self.__scannedOpcode__ is not None:
            if self.__scannedOpcode__.string=="EQU" or \
               self.__scannedOpcode__.string=="DAD":
               isLcl=False
#
#        real label, enter it into symbol table and invalidate
#        arp, drp context
#
         if isLcl: 
            ret=SymDict.enter(label,clsSymDict.SYM_LCL,PC,self.__lineInfo__)
            if ret is not None:
               self.addError(ret)
            self.__globVar__.arpReg= -1
            self.__globVar__.drpReg= -1

#
#  Parse Data register, which is the first operand. Handle drp elimination
#
   def parseDr(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False)
      if dRegister.typ != clsParsedOperand.OP_INVALID:
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
      aRegister=self.parseRegister(self.__scannedOperand__[1],signRequired)
      if aRegister.typ!= clsParsedOperand.OP_INVALID:
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
      xRegister=self.parseRegister(self.__scannedOperand__[index],False)
      if xRegister.typ != clsParsedOperand.OP_INVALID:
         if xRegister.registerTyp != "X":
            xRegister.typ= clsParsedOperand.OP_INVALID
            self.addError(ERROR.E_XREGEXPECTED)
         if xRegister.registerNumber!= clsParsedRegister.R_HASH  \
            and self.__globVar__.arpReg!= xRegister.registerNumber:
            self.__needsArp__= xRegister.registerNumber
            self.__globVar__.arpReg = xRegister.registerNumber
            self.__opcodeLen__+=1
      return(xRegister)
#
#  Parse label as operand
#
   def parseLabelOp(self,opIndex):
      label=self.__scannedOperand__[opIndex].string
      if label[0]=="=":
         label=label[1:]
      if parseFunc.parseLabel(label,self.__globVar__.symNamLen) is None:
         self.addError(ERROR.E_ILL_LABELOP)
         return clsInvalidOperand()
      else:
         return clsParsedLabel(label)
#
#  Parse literal data lists
#
   def parseLiteralDataList(self):
      err=False
      opIndex=1
      parsedOp=[ ]
      opLen=0
      while opIndex < len(self.__scannedOperand__):
         opString= self.__scannedOperand__[opIndex].string
         if opString[0]=="=":
            opString= opString[1:]
         if opString == "":
             self.addError(ERROR.E_ILL_LITOPERAND)
             parsedOp.append(clsInvalidOperand())
         else:
            if opString[0] in "0123456789":
               number=parseFunc.parseNumber(opString)
               if number is None:
                  self.addError(ERROR.E_ILLNUMBER)
                  parsedOp.append(clsInvalidOperand())
               else:
                  parsedOp.append(clsParsedNumber(number))
               opLen+=1
            else:
               label=opString
               if parseFunc.parseLabel(label,self.__globVar__.symNamLen)\
                   is None:
                  self.addError(ERROR.E_ILL_LABELOP)
                  parsedOp.append(clsInvalidOperand())
               else:
                  parsedOp.append(clsParsedLabel(label))
               opLen+=2
         opIndex+=1

      if opIndex==1:
         self.addError(ERROR.E_ILL_NUMOPERANDS)    # dead code??
      return [opLen,parsedOp]
#
#  Parse an address
#
   def parseAddress(self,idx):
      address=parseFunc.parseNumber(self.__scannedOperand__[idx].string)
      if address is None:
         self.addError(ERROR.E_ILLNUMBER)
         address=clsParserInfo.ILL_NUMBER
      elif address > 0xFFFF:
         self.addError(ERROR.E_NUMBERTOOLARGE)
         address=clsParserInfo.ILL_NUMBER
      return address
#
#  Include parsing and processing
#
   def pInc(self):
      self.__globVar__.hasIncludes=True
      fileName=parseFunc.parseAnyString(self.__scannedOperand__[0].string)
      if fileName is None:
         self.addError(ERROR.E_ILLSTRING)
      else:
         if self.__scannedOpcode__.string== "INC":
            self.__infile__.openInclude(fileName, \
              self.__globVar__.sourceFileDirectory)
         else:
            self.__infile__.openLink(fileName, \
              self.__globVar__.sourceFileDirectory)

#
#  Parse the conditinal assembly pseudo ops
#
   def pCond(self):
      cond=self.__globVar__.condAssembly
      opcode=self.__scannedOpcode__.string
      if len(self.__scannedOperand__)==1:
         name=parseFunc.parseLabel(self.__scannedOperand__[0].string, \
            self.__globVar__.symNamLen)
         if name is None:
            self.addError(ERROR.E_ILLFLAGNAME)
            return
      if opcode== "SET":
         cond.set(name)
      elif opcode== "CLR":
         cond.clr(name)
      elif opcode== "AIF":
         ret=cond.aif(name)
         if not ret:
            self.addError(ERROR.E_FLAGNOTDEFINED)
      elif opcode=="ELS":
         if not cond.isOpen():
            self.addError(ERROR.E_AIFEIFMISMATCH)
         else:
            cond.els()
      else:  # EIF
         if not cond.isOpen():
            self.addError(ERROR.E_AIFEIFMISMATCH)
         else:
            cond.eif()


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
#  Parse DEF and VAL
#
   def pDef(self):
      if self.__scannedOpcode__.string== "DEF":
         self.__opcodeLen__=2
      else:
         self.__opcodeLen__=1
      return[self.parseLabelOp(0)]
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
         self.addError(ERROR.E_ILLNUMBER)
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
      string=parseFunc.parseQuotedString(self.__scannedOperand__[0].string)
      if string is None:
         self.addError(ERROR.E_ILLSTRING)
         return pOperand
      i=0
      err=False
      for c in string:
         i+=1
         n=ord(c)
         if n > 0o177:
           err=True
           n=0
         if i==len(string) and self.__scannedOpcode__.string=="ASP":
           n|=0o200
         pOperand.append(clsParsedNumber(n))
      if err or i==0:
         self.addError(ERROR.E_ILLSTRING)
      self.__opcodeLen__=len(pOperand)
      return pOperand
#
#  Parse ignored statements
#
   def pNil(self):
      self.__opcodeLen__=0
      return []
#
#  Parse FIN statement
#
   def pFin(self):
      self.__globVar__.isFin=True
#
#     check, if we have any open conditionals
#
      if self.__globVar__.condAssembly.isOpen():
         self.addError(ERROR.E_AIFEIFMISMATCH)
      self.__opcodeLen__=0
      return []
#
#  Parse EQU and DAD pseudoops
#
   def pEqu(self):
#
#     The label in the self.__scannedLabel__ field has already been
#     parsed by the parseLine method
#
      SymDict=self.__globVar__.symDict
      if self.__scannedLabel__ is None:
         self.addError(ERROR.E_MISSING_LABEL)
         return []

      label=self.__scannedLabel__.string
      address=self.parseAddress(0)
      if address!=clsParserInfo.ILL_NUMBER:
         if self.__scannedOpcode__.string=="EQU":
            ret=SymDict.enter(label,clsSymDict.SYM_EQU,address, \
                   self.__lineInfo__)
         else:
            address+=self.__globVar__.ORG
            ret=SymDict.enter(label,clsSymDict.SYM_DAD,address, \
                   self.__lineInfo__)
         if ret is not None:
            self.addError(ret)
      return []
      
#
#  Parse ORG pseudoop
#
   def pOrg(self):
      address=self.parseAddress(0)
      if address!=clsParserInfo.ILL_NUMBER:
         self.__globVar__.ORG=address 
      return []
#
#  Parse ABS pseudoop
#  Syntax is: ABS {ROM} nnnn
#  ROM does not matter here
#
   def pAbs(self):
      self.__globVar__.hasAbs=True
      if self.__globVar__.PC !=0 or self.__globVar__.hasNam:
         self.addError(ERROR.E_NOTALLOWED_HERE)
      addrIndex=0
      if len(self.__scannedOperand__)==2:
         if self.__scannedOperand__[0].string.upper()== "ROM":
            addrIndex=1
         else:
           self.addError(ERROR.E_ROMEXPECTED)
      address=self.parseAddress(addrIndex)
      if address!=clsParserInfo.ILL_NUMBER:
         self.__globVar__.PC=address 
      return []
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
      if self.__globVar__.machine=="75":
         self.addError(ERROR.E_UNSUPPORTED)
         self.__opcodeLen__=0
         return pOperand
      if self.__globVar__.hasNam:
            self.addError(ERROR.E_NOTALLOWED_HERE)
            return pOperand
      self.__globVar__.hasNam=True
#
#     ABS only allowed before, if PC >= 0x100000
#
      if self.__globVar__.hasAbs and self.__globVar__.PC<=0o100000:
         self.addError(ERROR.E_NOTALLOWED_HERE)
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
            self.addError(ERROR.E_ILLNUMBER)
            return pOperand
         else:
            progNumber=number   
#
#     decode and check program name
#      
      progName= self.__scannedOperand__[pnIndex].string
      match=re.fullmatch("[A-Z][A-Z0-9_$&]{1,6}",progName)
      if not match or len(progName)>allowedLen  :
         self.addError(ERROR.E_ILL_PROGNAME)
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
#  Parse JSB instruction
#
   def pJsb(self):
      self.__opcodeLen__=1
      numBytesToStore=2
      parsedOperand=[]
#
#     Invalidate Arp, Drp context
#
      self.__globVar__.lastStmtWasJSB=True
#
#     Determine mode
#
      if self.__scannedOperand__[0].string[0]=="=":
#
#        JSB literal direct
#
         self.__addressMode__=clsParserInfo.JS_LITERAL_DIRECT
         self.__opcodeLen__+=numBytesToStore
         if len(self.__scannedOperand__)!=1:
            self.addError(ERROR.E_ILL_NUMOPERANDS)
            parsedOperand.append(clsInvalidOperand())
         else:
            parsedOperand.append(self.parseLabelOp(0))
      else:
#
#        JSB indexed
#
         self.__addressMode__=clsParserInfo.JS_INDEXED
         self.__opcodeLen__+=numBytesToStore
         if len(self.__scannedOperand__)!=2:
            self.addError(ERROR.E_ILL_NUMOPERANDS)   # dead code ??
         else:
            parsedOperand.append(self.parseXr(0))
            parsedOperand.append(self.parseLabelOp(1))
      return parsedOperand

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
      if aRegister.typ != clsParsedOperand.OP_INVALID:
         if aRegister.registerSign=="+":
            self.__addressMode__= clsParserInfo.STACK_INCREMENT
         else:
            self.__addressMode__= clsParserInfo.STACK_DECREMENT
      return [dRegister,aRegister]
 
#
#  Parse AD, AN, CM and SB instructions
#
   def pAri(self):
      
      parsedOperand=[]
      self.__opcodeLen__=1
      byteMode=self.getByteMode()
#
#     Parse DR, if we have a valid register then determine the number of
#     bytes to store for literals or labels
#
      dRegister=self.parseDr()
      if dRegister.typ== clsParsedOperand.OP_INVALID:
         self.__opcodeLen__=1
         return [dRegister]
#
#     Now determina Address Mode and check number of opderands
#     and parse opcodes
#
      if len(self.__opcode__)==3:       # ADB, ADM, SBB, SBM, CMB, CMM, ANM
         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_IMMEDIATE
            ret=self.parseLiteralDataList()
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               self.__opcodeLen__+= 1
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore == BYTESTOSTORE.UNKNOWN_BYTESTOSTORE:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(ERROR.E_RHASH_LITERAL)
               self.__opcodeLen__+= ret[0] 
            parsedOperand.extend(ret[1])

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_IMMEDIATE
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())
      else:                            # ADBD, ADMD, SBBD, ANMD

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))
         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_DIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      return parsedOperand

#
#  Parse LD / ST instructions: full to bursting of address modes
#
   def pLdSt(self):

      parsedOperand=[]
      self.__opcodeLen__=1
      byteMode=self.getByteMode()
#
#     Parse DR, if we have a valid register then determine the number of
#     bytes to store for literals or labels
#
      dRegister=self.parseDr()
      if dRegister.typ== clsParsedOperand.OP_INVALID:
         self.__opcodeLen__=1
         return [dRegister]
#
#     Now determina Address Mode and check number of opderands
#     and parse opcodes
#
      if len(self.__opcode__)==3:       # LDB, STB, LDM, STM

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_IMMEDIATE
            ret=self.parseLiteralDataList()
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               self.__opcodeLen__+= 1
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore == BYTESTOSTORE.UNKNOWN_BYTESTOSTORE:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(ERROR.E_RHASH_LITERAL)
               self.__opcodeLen__+= ret[0] 
            parsedOperand.extend(ret[1])

         elif self.__scannedOperand__[1].string[0]=="X":
            self.addError(ERROR.E_ILLADDRESSMODE)

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_IMMEDIATE
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      elif self.__opcode__[-1]=="D":         # LDBD, STBD, LDMD, STMD

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))

         elif self.__scannedOperand__[1].string[0]=="X":
            self.__addressMode__=clsParserInfo.AM_INDEX_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseLabelOp(2))

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_DIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      elif self.__opcode__[-1]=="I":       # LDBI, STBI, LDMI, STMI

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_INDIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))

         elif self.__scannedOperand__[1].string[0]=="X":
            self.__addressMode__=clsParserInfo.AM_INDEX_INDIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseLabelOp(2))

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_INDIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())
      
      return parsedOperand
#
#  Parse or/xor- instructions, they have two operands DR and AR
#
   def pOrXr(self):
      self.__opcodeLen__=1
      dRegister=self.parseDr()
      aRegister=self.parseAr()
      if dRegister.typ== clsParsedOperand.OP_INVALID or aRegister.typ== clsParsedOperand.OP_INVALID:
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
      if dRegister.typ == clsParsedOperand.OP_INVALID:
         self.__opcodeLen__=1
      return [dRegister]
#
#  Parse arp instruction, the only operand is the data register
#
   def pArp(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False)
      if dRegister.typ!= clsParsedOperand.OP_INVALID:
         self.__globVar__.arpReg= dRegister.registerNumber
      self.__opcodeLen__=1
      return [dRegister]
#
#  Parse drp instruction, the only operand is the data register
#
   def pDrp(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False)
      if dRegister.typ != clsParsedOperand.OP_INVALID:
         self.__globVar__.drpReg= dRegister.registerNumber
      self.__opcodeLen__=1
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
            self.addError(ERROR.E_ILL_LINENUMBER)
#
#     If we have a label field, parse it and enter label into symbol table
#
      if self.__scannedLabel__ is not None and not condAssemblyIsSuppressed:
         self.parseLabelField()
#
#     Return if we have no opcode nor operands
#
      if self.__scannedOpcode__ is None:
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__)
#
#     We have to check the conditional assembly status,
#     treat the line as comment if we are in False state
#     except we have an EIF statement
#
      if condAssemblyIsSuppressed and \
         self.__scannedOpcode__.string !="EIF":
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
#     Invalidate arp, drp context if last statement was a return or PAD
#
      if self.__globVar__.lastStmtWasPAD or self.__globVar__.lastStmtWasJSB:
         self.__globVar__.arpReg= -1
         self.__globVar__.drpReg= -1
         self.__globVar__.lastStmtWasPAD=False
         self.__globVar__.lastStmtWasJSB=False
#
#     Get information how to parse the opcode
# 
      self.__opcodeInfo__=OPCODES.get(self.__opcode__)

      if self.__opcodeInfo__ !=[]:
#
#        We have a valid opcode or pseudo opcode, check number of params
#
         if len(self.__scannedOperand__)< self.__opcodeInfo__[3] or \
            len(self.__scannedOperand__)> self.__opcodeInfo__[4]:
               self.addError(ERROR.E_ILL_NUMOPERANDS)
               return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
#
#        Call operand parse method
#
         self.__parsedOperand__= \
               clsParser.__methodDict__[self.__opcodeInfo__[0]](self)
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__, \
                self.__opcode__,self.__opcodeLen__, self.__parsedOperand__, \
                self.__needsArp__,self.__needsDrp__,self.__addressMode__)
      else:
         self.addError(ERROR.E_ILL_OPCODE)
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
#
#  Dictionary or parse methods
#   
   __methodDict__ = {
      "p1reg": p1reg,
      "pArp": pArp,
      "pDrp": pDrp,
      "pOrXr": pOrXr,
      "pNoPer": pNoPer,
      "pLdSt" : pLdSt,
      "pAri": pAri,
      "pJsb": pJsb,
      "pStack": pStack,
      "pJrel": pJrel,
      "pOrg": pOrg,
      "pAbs": pAbs,
      "pEqu": pEqu,
      "pNil": pNil,
      "pFin": pFin,
      "pAsc": pAsc,
      "pNam": pNam,
      "pBsz": pBsz,
      "pByt": pByt,
      "pDef": pDef,
      "pGto": pGto,
      "pCond": pCond,
      "pInc": pInc,
   }
#
# Code Info Data class -------------------------------------------------
#
# An object of this class is returned by the code generator
#
class clsCodeInfo(object):
   
   def __init__(self,code, messages):
      self.code= code         # list of generated code (bytes)
      self.messages=messages  # list of error messages

   def __repr__(self): # pragma: no cover
      s="clsCodeInfo object code= "
      for i in self.code:
         s+="{:o} ".format(i)
      return (s)
#
# Code Generator class -------------------------------------------------
#
# Genertes code and returns an object of class clsCodeInfo
#
class clsCodeGenerator(object):

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
      self.__messages__.append(errno)
      self.__globVar__.errorCount+=1
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
         self.addError(ERROR.E_LBLNOTFOUND)
         self.__code__.extend(defCode)
      else:
#
#        relative jump, only local labels which are not abs
#
         value=ret[1]
         if ret[0]==clsSymDict.SYM_LCL and not self.__globVar__.hasAbs:
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
         self.addError(ERROR.E_LBLNOTFOUND)
         self.__code__.extend(defCode)
      else:
         if self.__opcodeLen__==1:
            if ret[1] > 0xFF:
               self.addError(ERROR.E_NUMBERTOOLARGE)
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
      return
#
#  Generate nothing

   def gNil(self):
      return
#
#  Generate Data, we have only parsed numbers
#
   def gData(self):
      for op in self.__parsedOperand__:
         if op.typ== clsParsedOperand.OP_NUMBER:
            self.__code__.append(op.number)
      return
#
#  Generate relative jump instructions
#
   def gJrel(self):

      SymDict=self.__globVar__.symDict
      self.__code__.append(self.__opcodeInfo__[2])
      self.__bytesToGenerate__-=1
      pOperand=self.__parsedOperand__[0]
      if pOperand.typ == clsParsedOperand.OP_LABEL:
         ret=SymDict.get(pOperand.label,self.__lineInfo__)
         if ret==None:
            self.addError(ERROR.E_LBLNOTFOUND)
            self.__code__.append(0)
         else:
            offset=ret[1]-(self.__pc__+2)
            if offset < 0:
               offset=255 -abs(offset)+1
            if offset > 255 or offset < 0:
               offset=0
               self.addError(ERROR.E_RELJUMP_TOOLARGE)
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
         clsCodeGenerator.STACK_COMPLETION[self.__addressMode__ ] )
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
         clsCodeGenerator.JSB_COMPLETION[self.__addressMode__ ] )
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
         clsCodeGenerator.ARI_COMPLETION[self.__addressMode__ ] )
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
         clsCodeGenerator.LOADSTORE_COMPLETION[self.__addressMode__ ] )
      self.__bytesToGenerate__-=1
      self.gOperands()
      return

#
#  Process operands
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
          if pOperand.typ== clsParsedOperand.OP_LABEL:
             ret=SymDict.get(pOperand.label,self.__lineInfo__)
#
#            If the value is unknown generate one byte
#
             if ret==None:
                self.addError(ERROR.E_LBLNOTFOUND)
                op.append(0)
             else:
                if ret[1]> 0xFF:
                   op.append(ret[1] & 0xFF)
                   op.append(ret[1] >>8)
                else:
                   op.append(ret[1] & 0xFF)
#
#         Number, 1 bytes
#
          if pOperand.typ==clsParsedOperand.OP_NUMBER:
             number=pOperand.number
             if number > 0xFF:
                self.addError(ERROR.E_NUMBERTOOLARGE)
                op.append(0)
             else:
                op.append(number)
#
#     Append to instructions, check if we have too many bytes
#     and exceed section boundaries
#
      if len(op) > self.__bytesToGenerate__:
         self.addError(ERROR.E_OPEXCEEDSSECTION)
      else:
         self.__code__.extend(op)
#
#     Now fill remaining bytes with zeros
#
      l=len(op)
      while l < self.__bytesToGenerate__:
         self.__code__.append(0)
         l+=1
      return
#
#  Generate ARP, DRP instructions
#
   def gdarp(self):
      code=self.__opcodeInfo__[2]
      if self.__parsedOperand__[0].typ!= clsParsedOperand.OP_INVALID:
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
#  Generate Control Block
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
         clsCodeGenerator.__methodDict__[self.__opcodeInfo__[1]](self)
      return clsCodeInfo(self.__code__, self.__messages__)
#
#  Dictionary of opcode specific generator methods
#
   __methodDict__ = {
      "gdarp": gdarp,
      "gdirect": gdirect,
      "gLdSt": gLdSt,
      "gAri": gAri,
      "gJsb": gJsb,
      "gStack": gStack,
      "gJrel": gJrel,
      "gNil": gNil,
      "gData": gData,
      "gDef": gDef,
      "gGenZ": gGenZ,
      "gGto": gGto,
      "gNam":gNam,
   }
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
         ERROR.fatalError("Error opening object file")
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
            ERROR.fatalError("Error writing object file")
         except OverflowError:
            ERROR.fatalError("Internal error: code overflow")
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
         ERROR.fatalError("Error opening list file")
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
         headerString="CAPASM\n(c) Joachim Siebold\n\n"
      else:
         s1="CAPASM  "+CAPASM_VERSION+"       "+CAPASM_VERSION_DATE
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
      self.__listFile__.write("")
      self.__listFile__.write("Page {:4d}\n".format(self.__pageCount__))
      self.__listFile__.write("CAPASM\n")
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
         ERROR.fatalError("Error writing list file")
#
#  Write list file information for a source line including code, sourceline
#  and diagnostics. If no list file is specified, this information is
#  printed to standard output only if any diagnostics exist
#
   def writeLine(self,parsedLine,codeInfo):
       
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
         s="**ERROR(P) at {:s}({:d}): {:s}".format(parsedLine.lineInfo[0], \
            parsedLine.lineInfo[1],ERROR.getMsg(e))
         self.wrL(s)
      for e in codeInfo.messages:
         s="**ERROR(P) at {:s}({:d}): {:s}".format(parsedLine.lineInfo[0], \
            parsedLine.lineInfo[1],ERROR.getMsg(e))
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
      for s in symlist:
#
#        Output dictionary entry
#
         l=SymDict.get(s)
         symAddr=self.formatAddress(l[1])
         s=("{:10s} {:s} {:s}".format(s,clsSymDict.dictSymbolTypes[l[0]],\
             symAddr))
         nSkip=len(s)
#
#        Output symbol dictionary
#        first print the line number where the symbol was defined
#        this value is clsSymDict.LN_GLOBAL for global symbols
#
         lineDefined=l[2]
         if lineDefined==clsSymDict.LN_GLOBAL:
            s+=" GLOBL"
         elif lineDefined[1]>=0:
            s+=self.formatLineReference(lineDefined)
         else:
            s+="     ?"                          # dead code ??
         j=0
#
#        Now output line references, output a warning if we have none
#
         if reference==2:
            lineRefs=l[3]
            if len(lineRefs)==0:
               s+=" ** Not referenced!"
               j+=1
            else:
               for ln in lineRefs:
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
      s1="Assembly completed"
      s2=" {:d} lines processed, {:d} error(s) encountered".format(self.__totalLines__, numberOfErrors)
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
        ERROR.fatalError("Error opening source file")
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
         ERROR.fatalError("Maximum include depth exceeded")
      fileName=self.buildFileName(inputFileName,sourceFileDirectory)
      try:
        self.__inputFiles__.append(open(fileName,"r"))
        self.__lineInfos__.append([Path(inputFileName).name,0])
      except OSError:
        ERROR.fatalError("Error opening include or link file "+\
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
            ERROR.fatalError("Error reading source or include file")
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
# Assembler class ---------------------------------------------------------
#
# This is the top level class for the entire assembler
#
class clsAssembler(object):

   def __init__(self):
       super().__init__()
#
#  Assemble method. The method takes the values of the command line
#  switches and parameters. This method may be called multiple times
#  with different parameters.
#  Returns:
#     False:  everything o.k.
#     True:   errors in assembly
#  Raises capasmError on I/O error
#     
   def assemble(self,sourceFileName,binFileName="",listFileName="", \
       referenceOpt=1, pageSize=66, pageWidth=80, machine="85", \
       extendedChecks=False,  symNamLen=6,useHex=False):
#
#      initialize error condition
#
       hasError=False
#
#      Create global variables data object
#
       self.__globVar__=clsGlobVar()
       self.__globVar__.machine=machine
       self.__globVar__.useHex=useHex
       self.__sourceFileName__= sourceFileName
#
#      Build file name of object file if not specified
#
       if binFileName=="":
          self.__binFileName__= \
               Path(self.__sourceFileName__).with_suffix(".bin").name
       else:
          self.__binFileName__=binFileName
       self.__listFileName__= listFileName
       self.__referenceOpt__= referenceOpt
       self.__pageSize__= pageSize
       self.__pageWidth__= pageWidth
       self.__machine__= machine
       self.__extendedChecks__= extendedChecks
       self.__symNamLen__= symNamLen
#
#      Create symbol table object
#
       self.__globVar__.symDict=clsSymDict(self.__machine__, \
              self.__extendedChecks__)
#
#      Create conditional assembly object
#
       self.__globVar__.condAssembly=clsConditionalAssembly()
#
#      Check if we run in regression test mode
#
       if os.getenv("CAPASMREGRESSIONTEST"):
          self.__globVar__.isRegressionTest=True
#
#      get directory of source file
#
       self.__globVar__.sourceFileDirectory=\
          str(Path(self.__sourceFileName__).parent)
#
#      Check extended checks mode
#
       if self.__extendedChecks__:
          self.__globVar__.allowHashRLiteral=False
#
#      Set symbol name length
#
       self.__globVar__.symNamLen=self.__symNamLen__
#
#      Pass 1: scan and parse lines, accumulate results in the
#      pass1Info list
#
       pass1Info=[]
       infile=clsSourceReader(self.__sourceFileName__)
       lineScanner=clsLineScanner()
       lineParser=clsParser(self.__globVar__,infile)

       while not self.__globVar__.isFin:
          line=infile.read()
          if line is None:
             pass1Info[-1].messages.append(ERROR.E_MISSING_FIN)
             break
#
#         Scan line
#
          scannedLine=lineScanner.scanLine(line)
#
#         Parse line
#
          parsedLine=lineParser.parseLine(scannedLine,line)
          pass1Info.append(parsedLine)
#
#         Increment PC and codeLen with length of instructions
#
          self.__globVar__.PC+=parsedLine.opcodeLen
          self.__globVar__.codeLen+=parsedLine.opcodeLen

       infile=None
       lineScanner=None
       lineParser=None
#
#      Passe 2: process content of pass1Info list, generate code,
#      write code to binary output file and output information to 
#      the list file
#
       objWriter=clsObjWriter(self.__binFileName__)
       listWriter=clsListWriter(self.__globVar__,self.__listFileName__, \
                  self.__pageSize__, self.__pageWidth__)
       codeGenerator=clsCodeGenerator(self.__globVar__)

       for parsedLine in pass1Info:
#
#         Generate code
#
          codeInfo=codeGenerator.generate(parsedLine)
#
#         Write code
#
          objWriter.writeCode(codeInfo,parsedLine)
#
#         Write listing
#
          listWriter.writeLine(parsedLine,codeInfo)

       codeGenerator=None
       objWriter=None

       listWriter.writeSymbols(self.__referenceOpt__)
       listWriter.writeStatistics()
       listWriter=None
#
#      delete objectfile if any errors
#
       if self.__globVar__.errorCount>0:
          os.remove(self.__binFileName__)
          hasError=True
       self.__globVar__=None
#
#      return error condition
#
       return hasError
#
# custom arg checks ----------------------------------------------------
#
# Helper function to check the range for the page size parameter
#
class argPageSizeCheck(argparse.Action): # pragma: no cover
   def __call__(self, parser, namespace, values, option_string=None):
        if values < 40 or values> 100:
            parser.error("Valid range for {0} is 40 to 100".format(option_string))
        setattr(namespace, self.dest, values)

#
# Helper function to check the range for the line width parameter
#
class argWidthCheck(argparse.Action): # pragma: no cover
   def __call__(self, parser, namespace, values, option_string=None):
        if values < 80 or values> 132:
            parser.error("Valid range for {0} is 80 to 132".format(option_string))
        setattr(namespace, self.dest, values)



#
# Entry point capasm ------------------------------------------------------
# 
# This entry point parses the command line parameters, creates an
# assembler object and executes it with the parsed command line parameters
#
def capasm():             # pragma: no cover
   global GLOBALMODULE
#
#  Command line arguments processing
#
   argparser=argparse.ArgumentParser(description=\
   "An assembler for the Hewlett Packard Capricorn CPU (Series 80 and HP-75)",\
   epilog=\
   "See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   
   
   argparser.add_argument("sourcefile",help="source code file (required)")
   argparser.add_argument("-b","--binfile",\
      help="binary object code file (default: sourcefilename with suffix .bin",\
      default="")
   argparser.add_argument("-l","--listfile",\
      help="list file (default: no list file)",default="")
   argparser.add_argument("-r","--reference",type=int,default=1,\
      help="symbol reference 0:none, 1:short, 2:full (default:1)",\
      choices=[0,1,2])
   argparser.add_argument("-p","--pagesize",type=int,default=66, \
      help="lines per page (default: 66)",action=argPageSizeCheck)
   argparser.add_argument("-w","--width",type=int,default=80, \
      help="page width (default:80)",action=argWidthCheck)
   argparser.add_argument("-m","--machine",choices=['75','85','87'], \
      help="Machine type (default:85)",default='85')
   argparser.add_argument("-c","--check",help="activate additional checks", \
      action='store_true')
   argparser.add_argument("-x","--hex",help="use hex output", \
      action='store_true')
   argparser.add_argument("-s","--symnamelength",\
                  help="maximum length of symbol names (default:6)", \
      type=int,default=6,choices=[6,7,8,9,10])
   args= argparser.parse_args()
#
#  Create assembler object and run it
#
   capasm= clsAssembler()
   try:
      ret=capasm.assemble(args.sourcefile,listFileName=args.listfile,\
           binFileName=args.binfile, referenceOpt=args.reference, \
           pageSize=args.pagesize,pageWidth=args.width, \
           machine=args.machine,extendedChecks=args.check, \
           symNamLen=args.symnamelength,useHex=args.hex)
   except capasmError as e:
      print(e.msg+"-- Assembler terminated")
      ret=True
   if ret:
      sys.exit(1)
#
#  Run the capasm procedure, if this file is called as top level script
#
if __name__ == '__main__':  # pragma: no cover
   capasm()

