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
# - development version 0.9.6
# - HP86/87 compatible NAM statement
# - jump relative GTO
# - bug fixes
# - conditional assembly support
# - include and link file support
# 04.07.2020 jsi
# - allow quoted strings for INC and LNK files
# - use path of assembler source files for INC and LNK files, if there 
#   is only a file name specified
# 08.07.2020 jsi
# - development version 0.9.7
# - number parsing refactored, allow hex and bin numbers
# 20.07.2020 jsi
# - literal data list error fixes
# - support non octal numbers for registers
# - support LOC and HED statements
# 23.07.2020 jsi
# - development version 0.9.8
# - support for ASC/ASP statements with numeric length qualifiers
# - removed "'" as alternate string delimiter
# - do not issue page break triggered by "HED" if there is no list file
# 27.07.2020 jsi
# - removed "-m" option
# - added "-g" option and enhanced global symbols capabilities
# 31.07.2020 jsi
# - refactoring
# - allow more special characters in symbols

import argparse,sys,os,importlib,re
import importlib.util
from pathlib import Path
from .capcommon import capasmError,BYTESTOSTORE,parseFunc,basicOPCODES, \
     MESSAGE,clsSymDict, CAPASM_VERSION, CAPASM_VERSION_DATE, \
     clsConditionalAssembly, clsGlobVar, clsToken, clsLineScanner, \
     clsObjWriter, clsListWriter, clsSourceReader, clsParserInfo


#
#  Static class for the opcode dictionary ----------------------------------
#
class OPCODES():

#
#  capasm specific ops
#
   addOpcodeDict= {
   "RTN" : ["pNoPer","gdirect",0o236,0,0,False,False],
   "ABS"  : ["pAbs","gNil",0,1,2,False,False],
   "FIN"  : ["pFin","gNil",0,0,0,False,False],
   "LST"  : ["pNil","gNil",0,0,0,False,False],
   "UNL"  : ["pNil","gNil",0,0,0,False,False],
   "GLO"  : ["pNil","gNil",0,1,1,False,False],
   "ASC"   : ["pAsc","gData",0,1,256,False,False],
   "ASP"   : ["pAsc","gData",0,1,256,False,False],
   "NAM"   : ["pNam","gNam",0,1,2,False,False],
   "BSZ"   : ["pBsz","gGenZ",0,1,1,False,False],
   "BYT"   : ["pByt","gData",0,1,256,False,False],
   "OCT"   : ["pByt","gData",0,1,256,False,False],
   "DAD"   : ["pEqu","gNil",0,1,1,False,False],
   "DEF"   : ["pDef","gDef",0,1,1,False,False],
   "EQU"   : ["pEqu","gNil",0,1,1,False,False],
   "GTO"   : ["pGto","gGto",0,1,1,False,False],
   "VAL"   : ["pDef","gDef",0,1,1,False,False],
   "ORG"   : ["pOrg","gNil",0,1,1,False,False],
   "SET"   : ["pCond","gNil",0,1,1,False,False],
   "CLR"   : ["pCond","gNil",0,1,1,False,False],
   "AIF"   : ["pCond","gNil",0,1,1,False,False],
   "EIF"   : ["pCond","gNil",0,0,0,False,False],
   "ELS"   : ["pCond","gNil",0,0,0,False,False],
   "INC"   : ["pInc","gNil",0,1,1,False,False],
   "LNK"   : ["pInc","gNil",0,1,1,False,False],
   "HED"   : ["pHed","gHed",0,1,1,False,False],
   "LOC"   : ["pLoc","gGenZ",0,1,1,False,False],
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

   def __init__(self,label,size=2):
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
#     if notAllowed:
#        registerTypes+="!"
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
               self.__scannedOpcode__.string=="DAD":
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
            self.__globVar__.arpReg= -1
            self.__globVar__.drpReg= -1

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
#  Include parsing and processing
#
   def pInc(self):
      self.__globVar__.hasIncludes=True
      fileName=parseFunc.parseAnyString(self.__scannedOperand__[0].string)
      if fileName is None:
         self.addError(MESSAGE.E_ILLSTRING)
      else:
         if self.__scannedOpcode__.string== "INC":
            self.__infile__.openInclude(fileName, \
              self.__globVar__.sourceFileDirectory)
         else:
            self.__infile__.openLink(fileName, \
              self.__globVar__.sourceFileDirectory)

#
#  Parse the conditinal assembly pseudo ops FIX
#
   def pCond(self):
      cond=self.__globVar__.condAssembly
      opcode=self.__scannedOpcode__.string
      if len(self.__scannedOperand__)==1:
        pLabel=self.parseLabelOp(0)
        if pLabel.isInvalid():
           self.addError(MESSAGE.E_ILLFLAGNAME)
           return
        else:
           name=pLabel.label
      if opcode== "SET":
         cond.set(name)
      elif opcode== "CLR":
         cond.clr(name)
      elif opcode== "AIF":
         ret=cond.aif(name)
         if not ret:
            self.addError(MESSAGE.E_FLAGNOTDEFINED)
      elif opcode=="ELS":
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
         self.addError(MESSAGE.E_AIFEIFMISMATCH)
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
      isDAD=False
      if self.__scannedOpcode__=="DAD":
         isDAD=True
      SymDict=self.__globVar__.symDict
      if self.__scannedLabel__ is None:
         self.addError(MESSAGE.E_MISSING_LABEL)
         return []

      label=self.__scannedLabel__.string
      address=self.parseAddress(0)

      if address!=clsParserInfo.ILL_NUMBER:
         size=2
         if self.__scannedOpcode__.string=="EQU":
            if address < 256:
               size=1
            ret=SymDict.enter(label,clsSymDict.SYM_EQU,address, size,\
                   self.__lineInfo__)
         else:
            address+=self.__globVar__.ORG
            ret=SymDict.enter(label,clsSymDict.SYM_DAD,address, size,\
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
         self.addError(MESSAGE.E_NOTALLOWED_HERE)
      addrIndex=0
      if len(self.__scannedOperand__)==2:
         if self.__scannedOperand__[0].string.upper()== "ROM":
            addrIndex=1
         else:
            self.addError(MESSAGE.E_ROM_EXPECTED)
            return []
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
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               numberOfBytesToStore=1
               ret=self.parseLiteralDataList(numberOfBytesToStore)
               self.__opcodeLen__+= ret[0]
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore is None:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(MESSAGE.W_RHASH_LITERAL)
               ret=self.parseLiteralDataList(numberOfBytesToStore)
               self.__opcodeLen__+= ret[0] 
            parsedOperand.extend(ret[1])

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_IMMEDIATE
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())
      else:                            # ADBD, ADMD, SBBD, ANMD

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))
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
            if byteMode== clsParserInfo.BM_SINGLEBYTE:
               numberOfBytesToStore=1
               ret=self.parseLiteralDataList(numberOfBytesToStore)
               self.__opcodeLen__+= ret[0]
            else:
               numberOfBytesToStore= \
                  BYTESTOSTORE.numBytes(dRegister.registerNumber)
               if numberOfBytesToStore is None:
                  if not self.__globVar__.allowHashRLiteral:
                     self.addError(MESSAGE.W_RHASH_LITERAL)
               ret=self.parseLiteralDataList(numberOfBytesToStore)
               self.__opcodeLen__+= ret[0] 
            parsedOperand.extend(ret[1])

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
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))

         elif self.__scannedOperand__[1].string[0] in "xX":
            self.__addressMode__=clsParserInfo.AM_INDEX_DIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseLabelOp(2))

         else:
            self.__addressMode__=clsParserInfo.AM_REGISTER_DIRECT
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseAr())

      elif self.__opcode__[-1]=="I":       # LDBI, STBI, LDMI, STMI

         if self.__scannedOperand__[1].string[0]== "=":
            self.__addressMode__=clsParserInfo.AM_LITERAL_INDIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=2:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseLabelOp(1))

         elif self.__scannedOperand__[1].string[0] in "xX":
            self.__addressMode__=clsParserInfo.AM_INDEX_INDIRECT
            self.__opcodeLen__+= 2
            if len(self.__scannedOperand__)!=3:
               self.addError(MESSAGE.E_ILL_NUMOPERANDS)
            else:
               parsedOperand.append(self.parseXr(1))
               parsedOperand.append(self.parseLabelOp(2))

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
#        if dRegister.registerTyp=="!":
#           self.__opcodeLen__=0
      return [dRegister]
#
#  Parse drp instruction, the only operand is the data register
#
   def pDrp(self):
      dRegister=self.parseRegister(self.__scannedOperand__[0],False,True)
      self.__opcodeLen__=1
      if not dRegister.isInvalid():
         self.__globVar__.drpReg= dRegister.registerNumber
#        if dRegister.registerTyp=="!":
#           self.__opcodeLen__=0
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
#        Call operand parse method
#
         self.__parsedOperand__= \
               clsParser.__methodDict__[self.__opcodeInfo__[0]](self)
         return clsParserInfo(PC,self.__lineInfo__,self.__messages__, \
                self.__line__, \
                self.__opcode__,self.__opcodeLen__, self.__parsedOperand__, \
                self.__needsArp__,self.__needsDrp__,self.__addressMode__)
      else:
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
      "pHed": pHed,
      "pLoc": pLoc,
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
          if pOperand.typ== clsParsedOperand.OP_LABEL:
             ret=SymDict.get(pOperand.label,self.__lineInfo__)
#
#            apply the size constraint
#
             if ret==None:
                self.addError(MESSAGE.E_SYMNOTFOUND)
                op.append(0)
             else:
                if pOperand.size==2:
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
                self.addError(MESSAGE.E_NUMBERTOOLARGE)
                op.append(0)
             else:
                op.append(number)
#
#     Append to instructions, check if we have too many bytes
#     and exceed section boundaries
#
      if len(op) > self.__bytesToGenerate__:
         self.addError(MESSAGE.E_OPEXCEEDSSECTION)
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
      "gDef": gDef,
      "gGenZ": gGenZ,
      "gGto": gGto,
      "gNam": gNam,
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
       extendedChecks=False,  symNamLen=6,useHex=False,
       globalSymbolFile="none"):
#
#      initialize error condition
#
       hasError=False
#
#      Create global variables data object
#
       self.__globVar__=clsGlobVar()
       self.__globVar__.useHex=useHex
       self.__sourceFileName__= sourceFileName
       self.__globalSymbolFile__= globalSymbolFile
       self.__globVar__.progName="CAPASM"
#
#      Initalize basic parser functions
#
       parseFunc.DELIMITER='"'
       parseFunc.LABELMATCHSTRING="[(^0-9)(\x20-\x7A|\|)][\x20-\x7A|\|]{0,"
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
       self.__symNamLen__= symNamLen
#
#      Create symbol table object
#
       self.__globVar__.symDict=clsSymDict( self.__extendedChecks__, \
            self.__globalSymbolFile__, \
           { clsSymDict.SYM_DAD: "DAD", \
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
       lineScanner=clsLineScanner("!","!",'"')
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
def capasm():             # pragma: no cover
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
   argparser.add_argument("-x","--hex",help="use hex output", \
      action='store_true')
   argparser.add_argument("-s","--symnamelength",\
                  help="maximum length of symbol names (default:6)", \
      type=int,default=6,choices=[6,7,8,9,10,11,12])
   args= argparser.parse_args()
#
#  Create assembler object and run it
#
   capasm= clsAssembler()
   try:
      ret=capasm.assemble(args.sourcefile,listFileName=args.listfile,\
           binFileName=args.binfile, referenceOpt=args.reference, \
           pageSize=args.pagesize,pageWidth=args.width, \
           extendedChecks=args.check, \
           symNamLen=args.symnamelength,useHex=args.hex,\
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
   capasm()

