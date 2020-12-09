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

import argparse,sys,os,math
import importlib.util
from pathlib import Path
from .capcommon import capasmError,BYTESTOSTORE,parseFunc,basicOPCODES, \
     MESSAGE,clsSymDict,CAPASM_VERSION, CAPASM_VERSION_DATE, \
     clsConditionalAssembly, clsGlobVar, clsToken, clsLineScanner, \
     clsObjWriter, clsListWriter, clsSourceReader, clsParserInfo

#
#  Static class for the opcode dictionary ----------------------------------
#
class OPCODES(object):

   addOpcodeDict= {
#
#  ncas specific ops
#
   "RTN" : ["pRtn","gdirect",0o236,0,0,True,False],
#
#  This is a karma "special" and it means a JSB without return
#  Therefore this instruction is handled the same way as a RTN or GTO
#  at the end of IF-ELSE clauses in optimizing ARP/DRP elimination
#
   "JSBN"  : ["pJsb","gJsb",0o306,1,2,True,False],
#
#  conditional jump alias
#
   "JEQ"  : ["pJrel","gJrel",0o367,1,1,False,False], # alias of JZR
   "JNE"  : ["pJrel","gJrel",0o366,1,1,False,False], # alias of JNZ
   "JGE"  : ["pJrel","gJrel",0o365,1,1,False,False], # alias of JPS
   "JLT"  : ["pJrel","gJrel",0o364,1,1,False,False], # alias of JNG
   "JHS"  : ["pJrel","gJrel",0o373,1,1,False,False], # alias of JCY
   "JLO"  : ["pJrel","gJrel",0o372,1,1,False,False], # alias of JNC
#
#  IF pseudo op (we have to take the opposite condition there)
#
   "IFOV"  : ["pIf","gJrel",0o361,0,0,False,False],  # is JNO
   "IFEV"  : ["pIf","gJrel",0o362,0,0,False,False],  # is JOD
   "IFOD"  : ["pIf","gJrel",0o363,0,0,False,False],  # is JEV
   "IFPS"  : ["pIf","gJrel",0o364,0,0,False,False],  # is JNG
   "IFNG"  : ["pIf","gJrel",0o365,0,0,False,False],  # is JPS
   "IFZR"  : ["pIf","gJrel",0o366,0,0,False,False],  # is JNZ
   "IFNZ"  : ["pIf","gJrel",0o367,0,0,False,False],  # is JZR
   "IFEZ"  : ["pIf","gJrel",0o370,0,0,False,False],  # is JEN
   "IFEN"  : ["pIf","gJrel",0o371,0,0,False,False],  # is JEZ
   "IFCY"  : ["pIf","gJrel",0o372,0,0,False,False],  # is JNC
   "IFNC"  : ["pIf","gJrel",0o373,0,0,False,False],  # is JCY
   "IFLN"  : ["pIf","gJrel",0o374,0,0,False,False],  # is JLZ
   "IFLZ"  : ["pIf","gJrel",0o375,0,0,False,False],  # IS JLN
   "IFRN"  : ["pIf","gJrel",0o376,0,0,False,False],  # is JRZ
   "IFRZ"  : ["pIf","gJrel",0o377,0,0,False,False],  # is JRN
   "IFNE"  : ["pIf","gJrel",0o367,0,0,False,False], # alias of JZR
   "IFEQ"  : ["pIf","gJrel",0o366,0,0,False,False], # alias of JNZ
   "IFLT"  : ["pIf","gJrel",0o365,0,0,False,False], # alias of JPS
   "IFLE"  : ["pIf","gJrel",0o364,0,0,False,False], # alias of JNG
   "IFLO"  : ["pIf","gJrel",0o373,0,0,False,False], # alias of JCY
   "IFHS"  : ["pIf","gJrel",0o372,0,0,False,False], # alias of JNC
#
#  While pseudo op
#
   "WHMP"  : ["pWh","gJrel",0o360,0,0,False,False],
   "WHNO"  : ["pWh","gJrel",0o361,0,0,False,False],
   "WHOD"  : ["pWh","gJrel",0o362,0,0,False,False],
   "WHEV"  : ["pWh","gJrel",0o363,0,0,False,False],
   "WHNG"  : ["pWh","gJrel",0o364,0,0,False,False],
   "WHPS"  : ["pWh","gJrel",0o365,0,0,False,False],
   "WHNZ"  : ["pWh","gJrel",0o366,0,0,False,False],
   "WHZR"  : ["pWh","gJrel",0o367,0,0,False,False],
   "WHEN"  : ["pWh","gJrel",0o370,0,0,False,False],
   "WHEZ"  : ["pWh","gJrel",0o371,0,0,False,False],
   "WHNC"  : ["pWh","gJrel",0o372,0,0,False,False],
   "WHCY"  : ["pWh","gJrel",0o373,0,0,False,False],
   "WHLZ"  : ["pWh","gJrel",0o374,0,0,False,False],
   "WHLN"  : ["pWh","gJrel",0o375,0,0,False,False],
   "WHRZ"  : ["pWh","gJrel",0o376,0,0,False,False],
   "WHRN"  : ["pWh","gJrel",0o377,0,0,False,False],
   "WHEQ"  : ["pWh","gJrel",0o367,0,0,False,False], # alias of WHZR
   "WHNE"  : ["pWh","gJrel",0o366,0,0,False,False], # alias of WHNZ
   "WHGE"  : ["pWh","gJrel",0o365,0,0,False,False], # alias of WHPS
   "WHLT"  : ["pWh","gJrel",0o364,0,0,False,False], # alias of WHNG
   "WHHS"  : ["pWh","gJrel",0o373,0,0,False,False], # alias of WHCY
   "WHLO"  : ["pWh","gJrel",0o372,0,0,False,False], # alias of WHNC
#
#  conditional return pseudo op
#
   "RNO"  : ["pR","gJrel",0o361,0,0,False,False],
   "ROD"  : ["pR","gJrel",0o362,0,0,False,False],
   "REV"  : ["pR","gJrel",0o363,0,0,False,False],
   "RNG"  : ["pR","gJrel",0o364,0,0,False,False],
   "RPS"  : ["pR","gJrel",0o365,0,0,False,False],
   "RNZ"  : ["pR","gJrel",0o366,0,0,False,False],
   "RZR"  : ["pR","gJrel",0o367,0,0,False,False],
   "REN"  : ["pR","gJrel",0o370,0,0,False,False],
   "REZ"  : ["pR","gJrel",0o371,0,0,False,False],
   "RNC"  : ["pR","gJrel",0o372,0,0,False,False],
   "RCY"  : ["pR","gJrel",0o373,0,0,False,False],
   "RLZ"  : ["pR","gJrel",0o374,0,0,False,False],
   "RLN"  : ["pR","gJrel",0o375,0,0,False,False],
   "RRZ"  : ["pR","gJrel",0o376,0,0,False,False],
   "RRN"  : ["pR","gJrel",0o377,0,0,False,False],
   "REQ"  : ["pR","gJrel",0o367,0,0,False,False], # alias of RZR
   "RNE"  : ["pR","gJrel",0o366,0,0,False,False], # alias of RNZ
   "RGE"  : ["pR","gJrel",0o365,0,0,False,False], # alias of RPS
   "RLT"  : ["pR","gJrel",0o364,0,0,False,False], # alias of RNG
   "RHS"  : ["pR","gJrel",0o373,0,0,False,False], # alias of RCY
   "RLO"  : ["pR","gJrel",0o372,0,0,False,False], # alias of RNC
#
#  conditional exit pseudo op
#
   "EXNO"  : ["pEx","gJrel",0o361,0,0,False,False],
   "EXOD"  : ["pEx","gJrel",0o362,0,0,False,False],
   "EXEV"  : ["pEx","gJrel",0o363,0,0,False,False],
   "EXNG"  : ["pEx","gJrel",0o364,0,0,False,False],
   "EXPS"  : ["pEx","gJrel",0o365,0,0,False,False],
   "EXNZ"  : ["pEx","gJrel",0o366,0,0,False,False],
   "EXZR"  : ["pEx","gJrel",0o367,0,0,False,False],
   "EXEN"  : ["pEx","gJrel",0o370,0,0,False,False],
   "EXEZ"  : ["pEx","gJrel",0o371,0,0,False,False],
   "EXNC"  : ["pEx","gJrel",0o372,0,0,False,False],
   "EXCY"  : ["pEx","gJrel",0o373,0,0,False,False],
   "EXLZ"  : ["pEx","gJrel",0o374,0,0,False,False],
   "EXLN"  : ["pEx","gJrel",0o375,0,0,False,False],
   "EXRZ"  : ["pEx","gJrel",0o376,0,0,False,False],
   "EXRN"  : ["pEx","gJrel",0o377,0,0,False,False],
   "EXEQ"  : ["pEx","gJrel",0o367,0,0,False,False], # alias of RZR
   "EXNE"  : ["pEx","gJrel",0o366,0,0,False,False], # alias of RNZ
   "EXGE"  : ["pEx","gJrel",0o365,0,0,False,False], # alias of RPS
   "EXLT"  : ["pEx","gJrel",0o364,0,0,False,False], # alias of RNG
   "EXHS"  : ["pEx","gJrel",0o373,0,0,False,False], # alias of RCY
   "EXLO"  : ["pEx","gJrel",0o372,0,0,False,False], # alias of RNC
   "LOOP"  : ["pLoop","gNil",0,0,0,False,False],
   "ENDIF" : ["pEndif","gNil",0,0,0,False,False],
   "ELSE"  : ["pElse","gJrel",0o360,0,0,False,False],
#
#  compatibility pseudo ops
#
   "DEF"   : ["pDef","gData",0,1,1,False,True],
   "VAL"   : ["pDef","gData",0,1,1,False,True],

#
#  ncas pseudo ops
#
   "END"  : ["pEnd","gNil",0,0,0,False,False],
   "BSS"   : ["pBss","gGenZ",0,1,1,False,True],
   "ADDR"   : ["pEqu","gNil",0,1,1,False,True],
   "EQU"   : ["pEqu","gNil",0,1,1,False,True],
   "GTO"   : ["pGto","gGto",0,1,1,True,False],
   "ORG"   : ["pOrg","gNil",0,1,1,False,True],
   ".SET"   : ["pCond","gNil",0,1,1,False,True],
   ".CLR"   : ["pCond","gNil",0,1,1,False,True],
   ".IFSET"   : ["pCond","gNil",0,1,1,False,True],
   ".ENDIF"   : ["pCond","gNil",0,0,0,False,True],
   ".ELSE"   : ["pCond","gNil",0,0,0,False,True],
   "INCLUDE"   : ["pInc","gNil",0,1,1,False,True],
   "DATA"  : ["pData","gData",0,1,basicOPCODES.NUM_OPERANDS_ANY,False,True],
   "TITLE" : ["pHed","gHed",0,1,1,False,True],
   "STE" : ["pSte","gSte",0o235,0,0,False,False],
#  "NOP" : ["pNoPer","gdirect",0o235,0,0,False,False],
   "NOP" : ["pNoPer","gdirect",0o220,0,0,False,False], #  Karma NOP
   "NOP1" : ["pNoPer","gdirect",0o336,0,0,False,False], # see Series 80 wiki
   }
   __opcodeDict__= dict(basicOPCODES.basicOpcodeDict, **addOpcodeDict)

   @classmethod
   def get(cls,opcode):
      lookUp=opcode
      if lookUp in OPCODES.__opcodeDict__.keys():
         return OPCODES.__opcodeDict__[lookUp]
      else:
         return []
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
      return ("clsParsedOperand expression")
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
# Expression parser and execute class -----------------------------------
#
class clsExpression(object):

   EX_NUM=0
   EX_SYM=1
   EX_OP=2

   OP_PLUS=0
   OP_MINUS=1
   OP_DIV=2
   OP_MULT=3
   OP_OR=4
   OP_AND=5
   OP_NOT=6
   OP_MOD=7
   OP_RESIZE=8
   OP_CHS=9
   OP_NONE=10


   def __init__(self,globVar):
      super().__init__()
      self.__globVar__=globVar

   def addError(self,errnum):
      self.__errors__.append(errnum)
#
#  generate Bytecode
#
#  number
#
   def genNumber(self,value):
      self.__bc__.append([clsExpression.EX_NUM,value])
      self.__lastNumber__=value
      self.__size__=self.byteLen(value)
#
# location counter
#
   def genLoc(self,value):
      self.__bc__.append([clsExpression.EX_NUM,value])
      self.__size__=2
      
#
#  symbol
#
   def genSymbol(self,name):
      self.__bc__.append([clsExpression.EX_SYM,name])
      ret=self.__globVar__.symDict.get(name,noGlobStore=True)
      if ret is None:
         self.__size__= None
      else:
         self.__size__=ret[2]
#
#  opcode
#
   def genOp(self,op):
      self.__bc__.append([clsExpression.EX_OP,op])
      if op== clsExpression.OP_RESIZE:
         self.__size__=self.__bc__[-2][1]
      else:
         self.__size__= None
#
#  returns the number of bytes value will occupy
#
   def byteLen(self,value):
      if value==0:
         return 1
      else:
         return (1+math.floor(math.log(abs(value))/(0.69314718055994530942*8)))
#
#  convert the result into a list of byte values
#
   def makeBytes(self,value,size=None):
      if size is None:
         nBytes=self.byteLen(value)
      else:
         nBytes=size
      b= [0]* nBytes
      for i in range(0,nBytes):
            b[i]= value & 0xFF
            value=value>>8
      return b

#
#  resize a value to a given size
#  positve integers are returned unchanged
#  negative integers are padded with 0xFF
#  returns None if size is too small
#
   def resize(self,value,size):
      nBytes=self.byteLen(value)
      if size< nBytes:
         return None
      nPad=size-nBytes
      rVal=value
      if rVal < 0:
         for i in range(0,nPad):
             nBytes+=1
             rVal |=0xFF << (nBytes*8)
      return rVal
#
#  scan a character
#
   def getch(self):
      self.__getchCount__+=1
      if self.__getchCount__ == len (self.__exprString__):
         self.__GCH__= "\n"
      else:
         self.__GCH__= self.__exprString__[self.__getchCount__]
#
#  location counter symbol "$"
#
   def LOC(self):
      self.getch()
      self.genLoc(self.__globVar__.PC)
      return 
#
#  number, which can be ocal, decimal, bcd or hex. Hex numbers must always
#  begin with a digit
#
   def number(self):
      numString=""
      while True:
         numString+=self.__GCH__
         self.getch()
         if "01234567890abcdefABCDEFhHoOKk#".find(self.__GCH__)< 0:
            break
      value=parseFunc.parseNumber(numString)
      if value is None:
         self.addError(MESSAGE.E_ILLNUMBER)
         bValue=0
      else:
         bValue=value
      self.genNumber(bValue)
      return 
#
#  ASCII string, which can be either enclosed in ",',` or ^
#
   def asc(self):

      value=0
      term=self.__GCH__
      self.getch()
      string=""
      while self.__GCH__ != term:
         string+= self.__GCH__
         self.getch()
         if self.__GCH__== "\n":
            self.addError(MESSAGE.E_ILLSTRING)
            return
      self.getch()
      i=0
      for c in string[::-1]:
         if i== 0 and term in "^`":
            c=chr(ord(c)+128)
         value= value*256 + ord(c)
         i+=1
      self.genNumber(value)
      return
#
#  symbol name which always begins with a letter
#  
   def symbol(self):
      symName=""
      while True:
         symName+=self.__GCH__
         self.getch()
         if " )\n".find(self.__GCH__)>=0:
            break
      if parseFunc.parseLabel(symName,self.__globVar__.symNamLen) is None:
         self.addError(MESSAGE.E_ILL_LABELOP)
         return 
      self.genSymbol(symName)
      return 
#
#  expression base
#   
   def base(self):
      strTerm="'`^"+'"'
#
#     location counter symbol
#
      if self.__GCH__== "$":
         self.LOC()
#
#     number
#
      elif "01234567890".find(self.__GCH__) >=0:
         self.number()
#
#     quoted string
#
      elif self.__GCH__ in strTerm:
         self.asc()
#
#     left paranthesis, begin of a new term
#
      elif self.__GCH__=="(":
         self.getch()
         self.term()
         if self.__GCH__ != ")":
            self.addError(MESSAGE.E_MISSINGRPAREN)
            return 
         self.getch()
#
#    returned from term, look for a size specifier
#
         if self.__GCH__==".":
            self.getch()
            if  "01234567890".find(self.__GCH__) >=0:
               self.number()
               self.genOp(clsExpression.OP_RESIZE)
               size=self.__lastNumber__
               if size ==None:
                  self.addError(MESSAGE.E_INVALIDSIZESPEC)
                  return 
      else:
         self.symbol()
      return 
#
#  expression unary, operators are "-" or "~"
#
   def unary(self):
      if self.__GCH__== "-":
         self.getch()
         self.base()
         self.genOp(clsExpression.OP_CHS)
      elif self.__GCH__=="~":
         self.getch()
         self.base()
         self.genOp(clsExpression.OP_NOT)
      else:
         self.base()
      return 
#
#  expression bool, operators are "&" or "|"
#
   def bool(self):
      first=True
      operator=clsExpression.OP_NONE
      done=False
      while not done:
         self.unary()
         if first:
            first=False
         else:
            if operator== clsExpression.OP_AND:
               self.genOp(operator)
            elif operator== clsExpression.OP_OR:
               self.genOp(operator)
         done=True
         if self.__GCH__=="&":
            operator= clsExpression.OP_AND
            done= False
            self.getch()
         if self.__GCH__=="|":
            operator= clsExpression.OP_OR
            done= False
            self.getch()

      return 
#
#  expression factor, operators are "*", "/", "%" (modulo)
#
   def factor(self):

      operator=clsExpression.OP_NONE
      first=True
      done=False
      while not done:
         self.bool()
         if first:
            first=False
         else:
            if operator== clsExpression.OP_MULT:
               self.genOp(operator)
            elif operator== clsExpression.OP_DIV:
               self.genOp(operator)
            elif operator == clsExpression.OP_MOD:
               self.genOp(operator)
         done=True
         if self.__GCH__=="*":
            operator=clsExpression.OP_MULT
            done= False
            self.getch()
         if self.__GCH__=="/":
            operator=clsExpression.OP_DIV
            done= False
            self.getch()
         if self.__GCH__=="%":
            operator=clsExpression.OP_MOD
            done= False
            self.getch()

      return 
#
#  expression term, operators are "+" and "-"
#
   def term(self):

      operator=clsExpression.OP_NONE
      first=True
      done=False
      while not done:
         self.factor()
         if first:
            first=False
         else:
            if operator== clsExpression.OP_PLUS:
               self.genOp(operator)
            elif operator== clsExpression.OP_MINUS:
               self.genOp(operator)
         done=True
         if self.__GCH__=="+":
            operator=clsExpression.OP_PLUS
            done= False
            self.getch()
         if self.__GCH__=="-":
            operator=clsExpression.OP_MINUS
            done= False
            self.getch()

      return 

#
#  parse expression string
#  expr         : string with expression
#  indicatedSize: force size of result to this size if not None
#  sizeRequired : True if the size of the expression must be determined by
#                 parsing
#
   def parse(self,expr,indicatedSize=None,sizeRequired=False):
      self.__exprString__=expr
      self.__getchCount__=-1
      self.__GCH__=""
      self.__errors__= []
      self.__size__= None
      self.__bc__= []
      self.__lastNumber__=None
      self.getch()
#
#     parse expression
#
      self.term()
#
#     no more characters?
#
      if self.__GCH__ != "\n":
         self.addError(MESSAGE.E_ILLEXPRESSION)
#
#     do we have to resize to a determined size?
#
      if indicatedSize is not None:
         if self.__size__ is None or \
            self.__size__ !=  indicatedSize:
            self.genNumber(indicatedSize)
            self.genOp(clsExpression.OP_RESIZE)
            self.__size__= indicatedSize
#
#     no determined size, check if a size is required
#
      else:
         if self.__size__ is None and sizeRequired:
            self.addError(MESSAGE.E_UNSIZEDEXPRESSION)
 
      if len(self.__errors__)==0:
         parsedExpression=clsParsedExpression(self.__bc__,self.__size__)
      else:
         parsedExpression=clsInvalidOperand()
      return parsedExpression,self.__errors__
#
#  execute the byte code of an expression
#
   def execute(self,parsedExpression,lineInfo):

      stack=[]
      self.__errors__= []
      size=parsedExpression.size

      for typ,op in parsedExpression.byteCode:
         if typ== clsExpression.EX_NUM:
            stack.append(op)
         elif typ==clsExpression.EX_SYM:
            ret=self.__globVar__.symDict.get(op,lineInfo)
            if ret is None:
               self.addError(MESSAGE.E_SYMNOTFOUND)
               return None, None, self.__errors__
            value=ret[1]
            stack.append(value)
         elif typ==clsExpression.EX_OP:
            if op==clsExpression.OP_PLUS:
               stack[-2]+=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_MINUS:
               stack[-2]-=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_MULT:
               stack[-2]*=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_DIV:
               if stack[-1]==0:
                  self.addError(MESSAGE.E_DIVBYZERO)
                  return None, None, self.__errors__
               stack[-2]//=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_MOD:
               if stack[-1]==0:
                  self.addError(MESSAGE.E_DIVBYZERO)
                  return None, None, self.__errors__
               stack[-2]%=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_AND:
               stack[-2]&=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_OR:
               stack[-2]|=stack[-1]
               stack.pop()
            elif op==clsExpression.OP_CHS:
               stack[-1]|=-stack[-1]
            elif op==clsExpression.OP_NOT:
               stack[-1]|= ~ stack[-1]
            elif op==clsExpression.OP_RESIZE:
               value=self.resize(stack[-2],stack[-1])
               if value== None:
                  self.addError(MESSAGE.E_VALTOOLARGE)
                  return None, None,self.__errors__
               else:
                  stack[-2]=value
                  stack.pop()
 
      result=stack [0]
      byteResult=self.makeBytes(result,size)
      return result,byteResult,self.__errors__

   def immediate(self,expression,lineInfo):
      parsedExpression,errors=self.parse(expression,None,False)
      if len(errors)!=0:
         return None, None,errors
      result,byteResult, errors=self.execute(parsedExpression,lineInfo)
      return result,byteResult,errors
#
#  Struct context ------------------------------------------------------
#
class clsStructContext(object):

   CTX_IF=0
   CTX_LOOP=1
   CTX_RTN=2
   CTX_DISABLED=3

   def __init__(self):
      super().__init__()
      self.__lblCount__=0
      self.__ctxStack__= [ ]
      self.__rtnDest__= None

   def isEmpty(self):
      return len(self.__ctxStack__)==0

   def push(self,ctxInfo):
      if not self.__ctxStack__:
         self.__ctxStack__=[ctxInfo]
      else:
         self.__ctxStack__.append(ctxInfo)

   def pop(self):
      self.__ctxStack__.pop()

   def newLabel(self):
      self.__lblCount__+=1
      return("{:06d}".format(self.__lblCount__))

   def structR(self):
      if self.__rtnDest__ is None:
         self.__rtnDest__= self.newLabel()
      return(self.__rtnDest__)

   def getRtnDest(self):
      d=self.__rtnDest__
      self.__rtnDest__= None
      return(d)

   def structIf(self,arpReg,drpReg):
      lbl=self.newLabel()
      self.push([clsStructContext.CTX_IF,lbl,None,arpReg,drpReg,False,False,-1,-1])
      return(lbl)

   def structElse(self,arpReg,drpReg):
      if not self.__ctxStack__:
         return None
      if self.__ctxStack__[-1][0]!= clsStructContext.CTX_IF:
         return None
      if self.__ctxStack__[-1][2]!= None:
         return None
      lbl1=self.__ctxStack__[-1][1]
      lbl2=self.newLabel()
      self.__ctxStack__[-1][2]=lbl2
#
#     check, if arp or drp were changed in the if clause, if so then
#     set the invalidate flag to True
#
      oldArpReg=self.__ctxStack__[-1][3]
      if oldArpReg != arpReg:
         self.__ctxStack__[-1][5]=True
      oldDrpReg=self.__ctxStack__[-1][4]
      if oldDrpReg != drpReg:
         self.__ctxStack__[-1][6]=True
#
#     store last adp, drp if the IF part
#
      self.__ctxStack__[-1][7]=arpReg
      self.__ctxStack__[-1][8]=drpReg
      return (lbl1,lbl2,oldArpReg,oldDrpReg)
#
#  handle removed ELSE clause, return arp/drp status and invalidate entry
#
   def removeElse(self):

      self.__ctxStack__[-1][0]= clsStructContext.CTX_DISABLED
      return self.__ctxStack__[-1][5],self.__ctxStack__[-1][6]

   def structEndif(self,arpReg,drpReg):
      if not self.__ctxStack__:
         return None
      if self.__ctxStack__[-1][0]== clsStructContext.CTX_DISABLED:
         self.pop()
         return "",-1,-1,False,False
      if self.__ctxStack__[-1][0]!= clsStructContext.CTX_IF:
         return None
      if self.__ctxStack__[-1][2]!= None:
         lbl=self.__ctxStack__[-1][2]
      else: 
         lbl=self.__ctxStack__[-1][1]
#
#     check, if arp or drp were changed in the if clause, if so then
#     set the invalidate flag to True
#
      oldArpReg=self.__ctxStack__[-1][3]
      if oldArpReg != arpReg:
         self.__ctxStack__[-1][5]=True
#
#     but not if drp was the same in the if and the else clause
#
      if arpReg == self.__ctxStack__[-1][7]:
         if arpReg != -1:
            self.__ctxStack__[-1][5]=False
      oldDrpReg=self.__ctxStack__[-1][4]
      if oldDrpReg != drpReg:
         self.__ctxStack__[-1][6]=True
#
#     but not if drp was the same in the if and the else clause
#
      if drpReg == self.__ctxStack__[-1][8]:
         if drpReg != -1:
           self.__ctxStack__[-1][6]=False
      invalidateArp= self.__ctxStack__[-1][5]
      invalidateDrp= self.__ctxStack__[-1][6]
      self.pop()
      return(lbl,oldArpReg,oldDrpReg,invalidateArp,invalidateDrp)

   def structLoop(self):
      lbl=self.newLabel()
      self.push([clsStructContext.CTX_LOOP,lbl,None])
      return(lbl)

   def structEx(self):
      if not self.__ctxStack__:
         return None
      if self.__ctxStack__[-1][0]!= clsStructContext.CTX_LOOP:
         return None
      lbl2=self.newLabel()
      self.__ctxStack__[-1][2]=lbl2
      return(lbl2)

   def structWhile(self):
      if not self.__ctxStack__:
         return None
      if self.__ctxStack__[-1][0]!= clsStructContext.CTX_LOOP:
         return None
      lbl1=self.__ctxStack__[-1][1]
      lbl2=self.__ctxStack__[-1][2]
      self.pop()
      return(lbl1,lbl2)

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
      self.__expression__=clsExpression(self.__globVar__)
      self.__structCtx__= clsStructContext()
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
         self.__infile__.openInclude(fileName, \
           self.__globVar__.sourceFileDirectory)

#
#  Parse the conditinal assembly pseudo ops
#
   def pCond(self):
      cond=self.__globVar__.condAssembly
      opcode=self.__scannedOpcode__.string
      if len(self.__scannedOperand__)==1:
        flag=parseFunc.parseLabel(self.__scannedOperand__[0].string)
        if flag is None:
           self.addError(MESSAGE.E_ILLFLAGNAME)
           return
      if opcode== ".SET":
         cond.set(flag)
      elif opcode== ".CLR":
         cond.clr(flag)
      elif opcode== ".IFSET":
         ret=cond.aif(flag)
         if not ret:
            self.addError(MESSAGE.E_FLAGNOTDEFINED)
      elif opcode==".ELSE":
         if not cond.isOpen():
            self.addError(MESSAGE.E_AIFEIFMISMATCH)
         else:
            cond.els()
      else:  # EIF
         if not cond.isOpen():
            self.addError(MESSAGE.E_AIFEIFMISMATCH)
         else:
            cond.eif()
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
      result,byteResult,errors=self.__expression__.immediate(opstring, \
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
#  Parse EQU, Addr pseudoop
#
   def pEqu(self):
#
#     The label in the self.__scannedLabel__ field has already been
#     parsed by the parseLine method
#
      isAddr=False
      if self.__scannedOpcode__=="ADDR":
         isAddr=True
      SymDict=self.__globVar__.symDict
      if self.__scannedLabel__ is None:
         self.addError(MESSAGE.E_MISSING_LABEL)
         return []

      label=self.__scannedLabel__.string
      opstring= self.__scannedOperand__[0].string
#
#     evaluate expression immediately
#
      result,byteResult,errors=self.__expression__.immediate(opstring, \
         self.__lineInfo__)

      if result is not None:
         size=len(byteResult)
         if isAddr:
            if size  > 2:
               self.addError(MESSAGE.E_ILL_ADDRESS)
               return []
            ret=SymDict.enter(label,clsSymDict.SYM_DAD,result,size, \
                self.__lineInfo__)
         else:
            ret=SymDict.enter(label,clsSymDict.SYM_EQU,result,size, \
                self.__lineInfo__)
         if ret is not None:
            self.addError(ret)
      else:
         self.addError(errors)
      return []
      
#
#  Parse ORG pseudoop
#
   def pOrg(self):
      self.__globVar__.hasAbs=True
      opstring= self.__scannedOperand__[0].string
      result,byteResult,errors=self.__expression__.immediate(opstring, \
          self.__lineInfo__)
      if result is not None:
         if result >= 0 and result <= 0xFFFF:
            self.__globVar__.PC=result
         else:
            self.addError(MESSAGE.E_ILL_ADDRESS)
      else:
         self.addError(errors)
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
            ret=SymDict.enter(label1,clsSymDict.SYM_DAD,self.__globVar__.PC,\
                2,self.__lineInfo__)
            invalidateArp,invalidateDrp=self.__structCtx__.removeElse()
            if invalidateArp:
               self.__globVar__.arpReg= -1
            if invalidateDrp:
               self.__globVar__.drpReg= -1
            return []
         self.__opcodeLen__+=2
         ret=SymDict.enter(label1,clsSymDict.SYM_DAD,self.__globVar__.PC+2,\
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
         ret=SymDict.enter(label,clsSymDict.SYM_DAD,self.__globVar__.PC,2, \
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
      ret=SymDict.enter(label,clsSymDict.SYM_DAD,self.__globVar__.PC,2, \
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
         ret=SymDict.enter(label2,clsSymDict.SYM_DAD,self.__globVar__.PC+3,\
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
         ret=SymDict.enter(label,clsSymDict.SYM_DAD,\
           self.__globVar__.lastRtnAddr, 2, self.__lineInfo__)
      else:
#
#     otherwise try to create a label for a jump to the next rtn statement
#
         label=self.__structCtx__.structR()
      self.__opcodeLen__+=2
      return [clsParsedLabel(label,2)]

#
#  parse DEF, VAL
#
   def pDef(self):
     if self.__scannedOpcode__.string== "DEF":
        self.__opcodeLen__=2
        return [self.parseSingleExpression(0,2)]
     else:
        self.__opcodeLen__=1
        return [self.parseSingleExpression(0,1)]
#
#  Parse RTN statement
#
   def pRtn(self):
      self.__globVar__.lastRtnAddr=self.__globVar__.PC
      self.__opcodeLen__=1
      SymDict=self.__globVar__.symDict
      label=self.__structCtx__.getRtnDest()
      if label is not None:
         ret=SymDict.enter(label,clsSymDict.SYM_DAD,self.__globVar__.PC,2, \
             self.__lineInfo__)
      return
         
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
      if self.__scannedOpcode__.string!="JSBN":
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
            self.addError(MESSAGE.E_ILL_NUMOPERANDS)
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
            self.addError(MESSAGE.E_ILL_NUMOPERANDS)   # dead code ??
         else:
            parsedOperand.append(self.parseXr(0))
            parsedOperand.append(self.parseSingleExpression(1,2))
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
      if not aRegister.isInvalid():
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
      if dRegister.isInvalid():
         self.__opcodeLen__=1
         return [dRegister]
#
#     Now determina Address Mode and check number of opderands
#     and parse opcodes
#
      if len(self.__opcode__)==3:       # ADB, ADM, SBB, SBM, CMB, CMM, ANM
         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_IMMEDIATE
            self.__scannedOperand__[1].string= \
                 self.__scannedOperand__[1].string[1:]
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               if len(self.__scannedOperand__[1].string) > 0:
                  self.__opcodeLen__+= 1
                  parsedOperand.append(self.parseSingleExpression(1,1))
               else:
                  self.addError(MESSAGE.W_LITDATADOESNOTFILL)
        
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore is None:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(MESSAGE.W_RHASH_LITERAL)
               opLen,parsedExpressions=self.parseExpressionList(1,\
                     numberOfBytesToStore)
               if opLen is not None:
                  if numberOfBytesToStore is not None:
                     if numberOfBytesToStore != opLen:
                        self.addError(MESSAGE.W_LITDATADOESNOTFILL)
                  self.__opcodeLen__+= opLen
                  parsedOperand.extend(parsedExpressions)

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_IMMEDIATE
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())
      else:                            # ADBD, ADMD, SBBD, ANMD

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_DIRECT
            self.__scannedOperand__[1].string= \
                 self.__scannedOperand__[1].string[1:]
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseSingleExpression(1,2))
         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_DIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
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
      if dRegister.isInvalid():
         self.__opcodeLen__=1
         return [dRegister]
#
#     Now determina Address Mode and check number of opderands
#     and parse opcodes
#
      if len(self.__opcode__)==3:       # LDB, STB, LDM, STM

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_IMMEDIATE
            self.__scannedOperand__[1].string= \
                 self.__scannedOperand__[1].string[1:]
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               if len(self.__scannedOperand__[1].string) > 0:
                 self.__opcodeLen__+= 1
                 parsedOperand.append(self.parseSingleExpression(1,1))
               else:
                  self.addError(MESSAGE.W_LITDATADOESNOTFILL)
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore is None:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(MESSAGE.W_RHASH_LITERAL)
               opLen,parsedExpressions=self.parseExpressionList(1,\
                     numberOfBytesToStore)
               if opLen is not None:
                  if numberOfBytesToStore is not None:
                     if numberOfBytesToStore != opLen:
                        self.addError(MESSAGE.W_LITDATADOESNOTFILL)
                  self.__opcodeLen__+= opLen
                  parsedOperand.extend(parsedExpressions)

         elif self.__scannedOperand__[1].string[0] in "xX":
            self.addError(MESSAGE.E_ILLADDRESSMODE)

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_IMMEDIATE
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      elif self.__opcode__[-1]=="D":         # LDBD, STBD, LDMD, STMD

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_DIRECT
            self.__scannedOperand__[1].string= \
                 self.__scannedOperand__[1].string[1:]
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseSingleExpression(1,2))

         elif self.__scannedOperand__[1].string[0] in "xX":
            self.__addressMode__=clsParserInfo.AM_INDEX_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseSingleExpression(2,2))

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_DIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      elif self.__opcode__[-1]=="I":       # LDBI, STBI, LDMI, STMI

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_INDIRECT
            self.__scannedOperand__[1].string= \
                 self.__scannedOperand__[1].string[1:]
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseSingleExpression(1,2))

         elif self.__scannedOperand__[1].string[0] in "xX":
            self.__addressMode__=clsParserInfo.AM_INDEX_INDIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseSingleExpression(2,2))

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_INDIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
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
#     Invalidate arp, drp context if the previous statement was a subroutine 
#     call or PAD
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
         if len(self.__scannedOperand__)< self.__opcodeInfo__[3]:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
               return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
         if self.__opcodeInfo__[4] != basicOPCODES.NUM_OPERANDS_ANY:
            if len(self.__scannedOperand__)> self.__opcodeInfo__[4]:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
               return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                              self.__line__)
#
#        Invalidate arp/drp context if we the following conditions are met:
#        - the opcode generates executable code
#        - the opcode is no unconditional jump
#        - a local label exists for that line 
#
         if not self.__opcodeInfo__[6]:
            if self.__hasLcl__ and not self.__opcodeInfo__[5]:
                self.__globVar__.arpReg= -1
                self.__globVar__.drpReg= -1
         self.__hasLcl__=False
#
#        Call operand parse method
#
         self.__parsedOperand__= \
               clsParser.__methodDict__[self.__opcodeInfo__[0]](self)
#
#        Set flag, if the parsed operand is an unconditional JMP
#        This flag is needed for parsing an immediately following ELSE
#        statement which will eliminate the jump instructions to the
#        corresponding ENDIF
#
         if self.__opcodeInfo__[5]:
            self.__globVar__.lastOpcodeWasJmp=True
         else:
            if not self.__opcodeInfo__[6]:
               self.__globVar__.lastOpcodeWasJmp=False
#
#        return parsed statement information
#
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__, \
                self.__opcode__,self.__opcodeLen__, self.__parsedOperand__, \
                self.__needsArp__,self.__needsDrp__,self.__addressMode__)

      else:
#
#        return error information
#
         self.__hasLcl__=False
         self.addError(MESSAGE.E_ILL_OPCODE)
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
      "pEqu": pEqu,
      "pNil": pNil,
      "pEnd": pEnd,
      "pBss": pBss,
      "pGto": pGto,
      "pCond": pCond,
      "pInc": pInc,
      "pData":pData,
      "pHed":pHed,
      "pIf": pIf,
      "pElse": pElse,
      "pEndif": pEndif,
      "pLoop": pLoop,
      "pWh" : pWh,
      "pR" : pR,
      "pEx": pEx,
      "pRtn": pRtn,
      "pDef": pDef,
      "pSte": pSte,
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
      self.__expression__=clsExpression(self.__globVar__)
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
#  Generate Data, we have only parsed expressions
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
            if offset < 0:
               offset=255 -abs(offset)+1
            if offset > 255 or offset < 0:
               offset=0
               self.addError(MESSAGE.E_RELJUMP_TOOLARGE)
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
         self.__code__.extend(op)
      return
#
#  Generate ARP, DRP instructions. Do not generate any code if
#  the parsedOperand is of type OP_INVALID
#
   def gdarp(self):
      if self.__opcodeLen__==0:
         return
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
#  Generate STE instruction
#
   def gSte(self):
      self.__code__.append(0x9D)
      self.__code__.append(0x9C)
#
#  Generate HED pseudo op
#
   def gHed(self):
      self.__globVar__.doPageBreak=True
      self.__globVar__.title=self.__parsedOperand__[0].string
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
      "gGenZ": gGenZ,
      "gGto": gGto,
      "gSte": gSte,
      "gHed": gHed,
   }
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
       referenceOpt=1, pageSize=66, pageWidth=80, \
       extendedChecks=False,useOct=False,
       globalSymbolFile="none"):
#
#      initialize error condition
#
       hasError=False
#
#      Create global variables data object
#
       self.__globVar__=clsGlobVar()
       self.__globVar__.useHex= not useOct
       self.__sourceFileName__= sourceFileName
       self.__globalSymbolFile__= globalSymbolFile
       self.__globVar__.progName="NCAS"
#
#      initialize basic parser functions
#
       parseFunc.DELIMITER="'"+'"'
       parseFunc.LABELMATCHSTRING=\
          "[A-Za-z][A-Za-z0-9_$\+\-\.#/?\(\!\&)=:<>\|@*^]{0,"
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
       self.__extendedChecks__= extendedChecks
       self.__symNamLen__= 32
#
#      Create symbol table object
#
       self.__globVar__.symDict=clsSymDict( self.__extendedChecks__, \
            self.__globalSymbolFile__, \
            { clsSymDict.SYM_DAD: "ADR", \
              clsSymDict.SYM_EQU: "EQU", \
              clsSymDict.SYM_LCL: "LCL" })
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
       lineScanner=clsLineScanner("*",";","'`^"+'"')
       lineParser=clsParser(self.__globVar__,infile)

       while not self.__globVar__.isFin:
          line=infile.read()
          if line is None:
             if pass1Info:
                pass1Info[-1].messages.append(MESSAGE.E_MISSING_FIN)
                break
             else:
                MESSAGE.fatalError("Empty source file")
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
def ncas():             # pragma: no cover
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
   argparser.add_argument("-g","--globalsymbolfile",\
      help="global symbol file. Use either the built in symbol table names {\"85\",\"87\",\"75\",\"none\"} or specify a file name for a custom table (default: none)",default="none")
   argparser.add_argument("-r","--reference",type=int,default=1,\
      help="symbol reference 0:none, 1:short, 2:full (default:1)",\
      choices=[0,1,2])
   argparser.add_argument("-p","--pagesize",type=int,default=66, \
      help="lines per page (default: 66)",action=argPageSizeCheck)
   argparser.add_argument("-w","--width",type=int,default=80, \
      help="page width (default:80)",action=argWidthCheck)
   argparser.add_argument("-c","--check",help="activate additional checks", \
      action='store_true')
   argparser.add_argument("-o","--oct",help="use octal output", \
      action='store_true')
   args= argparser.parse_args()
#
#  Create assembler object and run it
#
   ncas= clsAssembler()
   try:
      ret=ncas.assemble(args.sourcefile,listFileName=args.listfile,\
           binFileName=args.binfile, referenceOpt=args.reference, \
           pageSize=args.pagesize,pageWidth=args.width, \
           extendedChecks=args.check, \
           useOct=args.oct,\
           globalSymbolFile=args.globalsymbolfile)
   except capasmError as e:
      print(e.msg+" -- Assembler terminated")
      ret=True
   if ret:
      sys.exit(1)
#
#  Run the capasm procedure, if this file is called as top level script
#
if __name__ == '__main__':  # pragma: no cover
   ncas()

