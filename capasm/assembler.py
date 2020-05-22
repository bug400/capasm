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
#

import argparse,sys,os,datetime,importlib
from pathlib import Path
#
# Program Constants -----------------------------------------------------
#
CAPASM_VERSION="Version 0.9.1"
CAPASM_VERSION_DATE="May 2020"
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
   "ABS"  : ["pAbs","gNil",0,1,1],
   "FIN"  : ["pFin","gNil",0,0,0],
   "LST"  : ["pNil","gNil",0,0,0],
   "UNL"  : ["pNil","gNil",0,0,0],
   "ASC"   : ["pAsc","gData",0,1,1],
   "ASP"   : ["pAsc","gData",0,1,1],
   "NAM"   : ["pNam","gData",0,1,1],
   "BSZ"   : ["pBsz","gGenZ",0,1,1],
   "BYT"   : ["pByt","gData",0,1,256],
   "DAD"   : ["pEqu","gNil",0,1,1],
   "DEF"   : ["pDef","gDef",0,1,1],
   "EQU"   : ["pEqu","gNil",0,1,1],
   "GTO"   : ["pGto","gGto",0,1,1],
   "VAL"   : ["pDef","gDef",0,1,1],
   "ORG"   : ["pOrg","gNil",0,1,1],
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
   E_PROGNAME_TOOLONG=17
   E_GLOBALSYMBOL_REDEFINED=18
   E_RELJUMP_TOOLARGE=19
   E_ILL_LITOPERAND=20
   E_ILL_LITERALLENGTH=21
   E_RHASH_LITERAL=22
   E_MISSING_LABEL=23

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
      E_PROGNAME_TOOLONG: "Program name exceeds six characters",
      E_GLOBALSYMBOL_REDEFINED: "Redefinition of a global symbol",
      E_RELJUMP_TOOLARGE: "Relative jump too large",
      E_ILL_LITOPERAND: "Illegal literal operand",
      E_ILL_LITERALLENGTH: "Illegal byte length of literal operand",
      E_RHASH_LITERAL: "Dangerous R#, cannot check section boundary",
      E_MISSING_LABEL: "Missing label in label field",
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
# Static class for number parsing -----------------------------------------
#
class numParse(object):
#
#  Parse decimal number (without D at the end, e.g. line numbers)
#
   @staticmethod
   def parseDecimal(string):
      retVal=0
      for c in string:
         if "0123456789".find(c)>=0:
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
            if "01234567".find(c)>=0:
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
         if "0123456789".find(c)>=0:
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
         return numParse.parseDecimal(string[:-1])
      elif string[-1]=="C" or string[-1]=="c":
         return numParse.parseBCD(string[:-1])
      elif "01234567".find(string[-1])>=0:
         return numParse.parseOctal(string)
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
#  Line number that indicates a global symbol
#
   LN_GLOBAL=100000

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
   def enter(self,name,typ,value,lineNumber,firstRefLineNumber=None):
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
          if not firstRefLineNumber:
             self.__symbols__[name]=[typ,value,lineNumber,[]]
          else:
             self.__symbols__[name]=[typ,value,lineNumber,[firstRefLineNumber]]
       return None
#
#  Get a symbol. We look first in our own symbol dictionary. If the
#  symbol is not found, try the Globals dictionary. If a symbol was
#  found in the Globals dictionary the insert it into the local dict.
#
   def get(self,name,lineNumber=None):
      try:
         ret=self.__symbols__[name]
         if lineNumber is not None:
            lines=ret[3]
            lines.append(lineNumber)
            self.__symbols__[name]=[ret[0],ret[1],ret[2], lines]
         return ret
      except KeyError:
         ret=self.__globalSyms__.globalSymbols.get(name)
         if ret:
            self.enter(name,ret[0],ret[1],clsSymDict.LN_GLOBAL,lineNumber)
         return ret
#
#  Get a list of all symbols in the local dictionary
# 
   def getList(self):
      return list(self.__symbols__.keys())
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
      self.allowHashRLiteral=True    # allow LD R#,=Literal
      self.hasAbs=False              # if ABS was used
      self.hasNam=False              # if NAM was used
      self.labelLen=6                # label length parameter
      self.isRegressionTest=False    # true to run assembler in regtest mode
      self.isFin=False               # FIN Statement encountered
      self.symDict=None              # Symbol dictionary
      self.errorCount=0              # Error counter
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
      inString=False
      doubleQuote=False
      termString=" "
      if termSyms is not None:
         termString+=termSyms
         if termSyms.find(char)>=0:
            return clsToken(char, pos, nxtChar)
#
#     Loop until end of line, blank or termchar encountered
#
      while char!="":
         if not inString and termString.find(char) >=0:
               termchar= char
               break
#
#     String handling
#
         if char=="\"":
            if not inString:
               inString=True
            else:
#
#              In string mode and we have a "
#
               if not doubleQuote:
                  inString=False
               if nxtChar=="\"":
                  doubleQuote= True
#
#        Accumulate token
#
         if len(token)==0:
            position= pos
         if not doubleQuote:
            token+=char
         doubleQuote=False
         char, pos, nxtChar=self.scanChar()
      return clsToken(token, position, termchar)
#
#  Scan input line and return scanned line number, label, opcode and a list
#  of operands. Missing items are None
#
   def scanLine(self,lineCount,line):

      scannedLineNumber=None
      scannedLabel=None
      scannedOpcode=None
      scannedOperand=[]

      self.__line__= line
      self.__lineCount__= lineCount
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
         scannedLineNumber=clsToken(str(self.__lineCount__),0,' ')
         return [scannedLineNumber,scannedLabel,scannedOpcode,scannedOperand]
#
#     Is the first token a line number?
#
      lineBegin=0
      if "0123456789".find(tok.string[0])>=0:
         scannedLineNumber=tok
         lineBegin=len(scannedLineNumber.string)+tok.position
         tok=self.scanTok()
      else:
#
#        We have no source line number, put the line count into token
#
         scannedLineNumber=clsToken(str(self.__lineCount__),0,' ')
#
#     No next token, leave ...

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
#      Opcode
#
      scannedOpcode= tok
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

   def __init__(self,PC,lineNumber,messages,line,opcode="",opcodeLen=0,parsedOperand= [],needsArp=-1,needsDrp=-1,addressMode=AM_REGISTER_IMMEDIATE):
      self.PC=PC                          # program counter
      self.lineNumber= lineNumber         # line number (parsed or generated)
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
   def __init__(self,globVar):
      super().__init__()
      self.__globVar__= globVar
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
      if string[i]=="R" or string[i]=="X":
         typ=string[i]
         i+=1
         if string[i]=="*":
            return clsParsedRegister(sign, typ, 1)
         elif string[i]=="#":
            return clsParsedRegister(sign, typ, clsParsedRegister.R_HASH)
      number=numParse.parseOctal(string[i:])
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
#     We have a label, invalidate arp, drp context
#
      self.__globVar__.arpReg= -1
      self.__globVar__.drpReg= -1
#
#     Valid label?
#
      if len(label) > self.__globVar__.labelLen:
         self.addError(ERROR.E_ILL_LABEL)
      elif not label[0].isalpha():
         self.addError(ERROR.E_ILL_LABEL)
      else:
#
#     Enter label into symbol table (NOT IF EQU OR DAD!!)
#     but the opcode has not been parsed yet
#
         doEnter=True
         if self.__scannedOpcode__ is not None:
            if self.__scannedOpcode__.string=="EQU" or \
               self.__scannedOpcode__.string=="DAD":
               doEnter=False
         if doEnter: 
            ret=SymDict.enter(label,clsSymDict.SYM_LCL,PC,self.__lineNumber__)
            if ret is not None:
               self.addError(ret)

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
      err=False
      if label[0]=="=":
         label=label[1:]
      if len(label) > self.__globVar__.labelLen:
         self.addError(ERROR.E_ILL_LABELOP)
         err=True
      if not label[0].isalpha():
         self.addError(ERROR.E_ILL_LABELOP)
         err=True
      if err:
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
            if "0123456789".find(opString[0]) >=0:
               number=numParse.parseNumber(opString)
               if number is None:
                  self.addError(ERROR.E_ILLNUMBER)
                  parsedOp.append(clsInvalidOperand())
               else:
                  parsedOp.append(clsParsedNumber(number))
               opLen+=1
            else:
               label=opString
               if len(label)> self.__globVar__.labelLen or not label[0].isalpha():
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
      address=numParse.parseNumber(self.__scannedOperand__[idx].string)
      if address is None:
         self.addError(ERROR.E_ILLNUMBER)
         address=clsParserInfo.ILL_NUMBER
      elif address > 0xFFFF:
         self.addError(ERROR.E_NUMBERTOOLARGE)
         address=clsParserInfo.ILL_NUMBER
      return address
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
         number=numParse.parseNumber(operand.string)
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
      string=self.__scannedOperand__[0].string
      if string[0]!="\"" or string[-1]!="\"":
         self.addError(ERROR.E_ILLSTRING)
         return pOperand
      string=string[1:len(string)-1]
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
      self.__opcodeLen__=0
      self.__globVar__.isFin=True
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
                   self.__lineNumber__)
         else:
            address+=self.__globVar__.ORG
            ret=SymDict.enter(label,clsSymDict.SYM_DAD,address, \
                   self.__lineNumber__)
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
#  Syntax is: ABS nnnn 
# 
#
   def pAbs(self):
      address=self.parseAddress(0)
      self.__globVar__.hasAbs=True
      if self.__globVar__.PC !=0 or self.__globVar__.hasNam:
         self.addError(ERROR.E_NOTALLOWED_HERE)
      if address!=clsParserInfo.ILL_NUMBER:
         self.__globVar__.PC=address 
      return []
#
#  Parse NAM pseudoop
#  Syntax is NAM: UnquotedString
#
   def pNam(self):
      self.__globVar__.hasNam=True
      if self.__globVar__.PC !=0 or self.__globVar__.hasAbs:
         self.addError(ERROR.E_NOTALLOWED_HERE)
      progName= self.__scannedOperand__[0].string
      if len(progName)>6:
         self.addError(ERROR.E_PROGNAME_TOOLONG)

      self.__opcodeLen__=26
#
#     Now build the program control block
#
      progName=progName.ljust(6)
      pOperand=[ ]
      err=False
      for c in progName:
         n=ord(c)
         if n > 0o177:
           err=True
           n=0
         pOperand.append(clsParsedNumber(n))
      if err:
         self.addError(ERROR.E_ILLSTRING)
#
#     BPGM type 2
#
      pOperand.append(clsParsedNumber(2))
#
#     19 bytess 0 follow
#
      for i in range(0,19):
         pOperand.append(clsParsedNumber(0))
      return pOperand
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
                  self.__opcodeLen__+= ret[0] # WEAK!
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(ERROR.E_RHASH_LITERAL)
               else:
                  self.__opcodeLen__+=numberOfBytesToStore
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
                  self.__opcodeLen__+= ret[0]   # Weak !
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(ERROR.E_RHASH_LITERAL)
               else:
                  self.__opcodeLen__+=numberOfBytesToStore
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
#
#     Parse lineNumber, we always have one (may be not a valid integer)
#
      self.__lineNumber__=numParse.parseDecimal( \
                    self.__scannedLineNumber__.string)
      if self.__lineNumber__ == None:
         self.__lineNumber__= clsParserInfo.ILL_NUMBER
         self.addError(ERROR.E_ILL_LINENUMBER)
#
#     If we have a label field, parse it and enter label into symbol table
#
      if self.__scannedLabel__ is not None:
         self.parseLabelField()
#
#     Return if we have no opcode nor operands
#
      if self.__scannedOpcode__ is None:
         return clsParserInfo(PC,self.__lineNumber__,self.__messages__, \
                self.__line__)
#
#     Return if we have a comment ! in the opcode field
#
      if self.__scannedOpcode__.string=="!":
         return clsParserInfo(PC,self.__lineNumber__,self.__messages__, \
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
               return clsParserInfo(PC,self.__lineNumber__,self.__messages__, \
                              self.__line__)
#
#        Call operand parse method
#
         self.__parsedOperand__= \
               clsParser.__methodDict__[self.__opcodeInfo__[0]](self)
         return clsParserInfo(PC,self.__lineNumber__,self.__messages__, \
                self.__line__, \
                self.__opcode__,self.__opcodeLen__, self.__parsedOperand__, \
                self.__needsArp__,self.__needsDrp__,self.__addressMode__)
      else:
         self.addError(ERROR.E_ILL_OPCODE)
         return clsParserInfo(PC,self.__lineNumber__,self.__messages__, \
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
      self.__code__.append(0o251)       # LDM
      defCode= [0]* self.__opcodeLen__
      pLabel=self.__parsedOperand__[1]
      if pLabel.typ != clsParsedOperand.OP_LABEL:
         self.__code__.extend(defCode)
         return
      ret=SymDict.get(pLabel.label,self.__lineNumber__)
      if ret==None:
         self.addError(ERROR.E_LBLNOTFOUND)
         self.__code__.extend(defCode)
      else:
         value=ret[1]-1
         self.__code__.extend([value & 0xFF, value >>8])
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
      ret=SymDict.get(pLabel.label,self.__lineNumber__)
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
         ret=SymDict.get(pOperand.label,self.__lineNumber__)
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
             ret=SymDict.get(pOperand.label,self.__lineNumber__)
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
      self.__lineNumber__= parsedLine.lineNumber
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
#     PC 6 digits octal
#
      s="{:06o}".format(pc)+" "
#
#     Bytes of code (max 3) octal
#
      for i in range(0,3):
         if i>= codeLen:
            s+="    "
         else:
            s+="{:03o}".format(codeInfo.code[i])+" "
#
#     Source code line
#
      s+=line
      self.wrL(s)
#
#     Continuation line(s) for code, if we have more than 3 bytes of code
#
      j=0
      i=3
      s=""
      while i < codeLen:
         if j==0:
            pc+=3
            s="{:06o}".format(pc)+" "
         if i>= codeLen:
            s+="    "
         else:
            s+="{:03o}".format(codeInfo.code[i])+" "
         j+=1
         if j==3:
            self.wrL(s)
            j=0
         i+=1
      if j>0:
         self.wrL(s)
#
#     Error messages of parser and code generator, if any
#
      for e in parsedLine.messages:
         s="**ERROR(P) at {:4d}: {:s}".format(parsedLine.lineNumber, \
            ERROR.getMsg(e))
         self.wrL(s)
      for e in codeInfo.messages:
         s="**ERROR(P) at {:4d}: {:s}".format(parsedLine.lineNumber, \
            ERROR.getMsg(e))
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
         s=("{:10s} {:s} {:6o}".format(s,clsSymDict.dictSymbolTypes[l[0]],l[1]))
         nSkip=len(s)+7
#
#        Output symbol dictionary
#        first print the line number where the symbol was defined
#        this value is clsSymDict.LN_GLOBAL for global symbols
#
         lineDefined=l[2]
         if lineDefined==clsSymDict.LN_GLOBAL:
            s+=" GLOBL"
         elif lineDefined>=0:
            s+=" {:4d}D".format(l[2])
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
                  if ln == clsParserInfo.ILL_NUMBER:
                     continue                         # dead code ??
                  j+=1
                  s+=" {:4d} ".format(ln)
#
#                 We need a continuation line
#
                  if len(s)+5>= self.__lineWidth__:
                     self.wrL(s)
                     s=" "*nSkip
                     j=0
            if j!=0:
               self.wrL(s)
         else:
            self.wrL(s)
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
#  Initialize and open source file
#
   def __init__(self,inputfilename):
      super().__init__()
      self.__inputfile__=None
      try:
        self.__inputfile__=open(inputfilename,"r")
      except OSError:
        ERROR.fatalError("Error opening source file")
#
#  Read a line
#
   def read(self):
      try:
         line=self.__inputfile__.readline()
      except OSError:
        ERROR.fatalError("Error reading source file")
      if not line:
         return None
      return line.strip("\r\n")
#
#  Destructor, close file
#
   def __del__(self):
      if self.__inputfile__ is not None:
         self.__inputfile__.close()
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
#  with different parameters
#     
   def assemble(self,sourceFileName,binFileName="",listFileName="", \
       referenceOpt=1, pageSize=66, pageWidth=80, machine="85", \
       extendedChecks=False,  labelSize=6):
#
#      Create global variables data object
#
       self.__globVar__=clsGlobVar()
       self.__sourceFileName__= sourceFileName
#
#      Build file name of object file if not specified
#
       if binFileName=="":
          binfile=Path(self.__sourceFileName__)
          self.__binFileName__=binfile.with_suffix(".bin")
       else:
          self.__binFileName__=binFileName
       self.__listFileName__= listFileName
       self.__referenceOpt__= referenceOpt
       self.__pageSize__= pageSize
       self.__pageWidth__= pageWidth
       self.__machine__= machine
       self.__extendedChecks__= extendedChecks
       self.__labelSize__= labelSize
#
#      Create symbol table object
#
       self.__globVar__.symDict=clsSymDict(self.__machine__, \
              self.__extendedChecks__)
#
#      Check if we run in regression test mode
#
       if os.getenv("CAPASMREGRESSIONTEST"):
          self.__globVar__.isRegressionTest=True
#
#      Check extended checks mode
#
       if self.__extendedChecks__:
          self.__globVar__.allowHashRLiteral=False
#
#      Set label length
#
       self.__globVar__.labelLen=self.__labelSize__
#
#      Pass 1: scan and parse lines, accumulate results in the
#      pass1Info list
#
       pass1Info=[]
       lineCount=0
       infile=clsSourceReader(self.__sourceFileName__)
       lineScanner=clsLineScanner()
       lineParser=clsParser(self.__globVar__)

       while not self.__globVar__.isFin:
          line=infile.read()
          if line is None:
             break
#
#         Scan line
#
          lineCount+=1
          scannedLine=lineScanner.scanLine(lineCount,line)
#
#         Parse line
#
          parsedLine=lineParser.parseLine(scannedLine,line)
          pass1Info.append(parsedLine)
#
#         Increment PC with length of instructions
#
          self.__globVar__.PC+=parsedLine.opcodeLen

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
#  delete objectfile if any errors
#
       if self.__globVar__.errorCount>0:
          os.remove(self.__binFileName__)
       self.__globVar__=None

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
# Main program ----------------------------------------------------
# 
# The main program parses the command line parameters, creates an
# assembler object and executes it with the parsed command line parameters
#
def capasm():             # pragma: no cover
   global GLOBALMODULE
#
#  Command line arguments processing
#
   argparser=argparse.ArgumentParser()
   argparser.add_argument("sourcefile",help="source code file")
   argparser.add_argument("-b","--binfile",help="binary object code file",default="")
   argparser.add_argument("-l","--listfile",help="list file",default="")
   argparser.add_argument("-r","--reference",type=int,default=1,\
      help="symbol reference 0:none, 1:short, 2:full",choices=[0,1,2])
   argparser.add_argument("-p","--pagesize",type=int,default=66, \
      help="lines per page",action=argPageSizeCheck)
   argparser.add_argument("-w","--width",type=int,default=80, \
      help="page width",action=argWidthCheck)
   argparser.add_argument("-m","--machine",choices=['75','85','87'], \
      help="Machine type",default='85')
   argparser.add_argument("-c","--check",help="activate additional checks", \
      action='store_true')
   argparser.add_argument("-s","--labelsize",help="length of labels", \
      type=int,default=6,choices=[6,7,8,9,10])
   args= argparser.parse_args()
#
#  Create assembler object and run it
#
   capasm= clsAssembler()
   try:
      capasm.assemble(args.sourcefile,listFileName=args.listfile,\
           binFileName=args.binfile, referenceOpt=args.reference, \
           pageSize=args.pagesize,pageWidth=args.width, \
           machine=args.machine,extendedChecks=args.check, \
           labelSize=args.labelsize)
   except capasmError as e:
      print(e.msg+"-- Assembler terminated")
      sys.exit(1)
#
#  Run the capasm procedure, if this file is called as top level script
#
if __name__ == '__main__':  # pragma: no cover
   capasm()

