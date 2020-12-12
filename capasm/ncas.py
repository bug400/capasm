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
from .capcommon import capasmError,BYTESTOSTORE,parseFunc,OPCODES, \
     MESSAGE,clsSymDict,CAPASM_VERSION, CAPASM_VERSION_DATE, \
     clsConditionalAssembly, clsGlobVar, clsToken, clsLineScanner, \
     clsObjWriter, clsListWriter, clsSourceReader, clsParserInfo, \
     clsParsedOperand, clsParsedExpression, clsInvalidOperand, \
     clsParsedLabel,clsParsedString, clsParsedRegister, clsCodeInfo, \
     clsCodeGeneratorBase, clsParserBase

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
class clsParser(clsParserBase):

#
#  Initialize parser
#
   def __init__(self,globVar,infile):
      super().__init__(globVar,infile)
      self.__expression__=clsExpression(globVar)
      self.__structCtx__= clsStructContext()
      return

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
# Code Generator class -------------------------------------------------
#
# Genertes code and returns an object of class clsCodeInfo
#
class clsCodeGenerator(clsCodeGeneratorBase):

#
#  Initialize generator
#
   def __init__(self,globVar):
      super().__init__(globVar)
      self.__expression__=clsExpression(self.__globVar__)
      return
#
#  Generate ARP, DRP instructions. Overwrite superclass method
#
   def gdarp(self):
      if self.__opcodeLen__==0:
         return
      super().gdarp()
      return
#
# NCAS Assembler class ---------------------------------------------------------
#
# This is the top level class for the entire assembler
#
class clsNcas(object):

   def __init__(self):
       super().__init__()
#
#  extend the OPCODES dictionary with the ncas specific OPS
#
   def extendOpcodes(self):
      OPCODES.extendDict( {
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
      "DATA"  : ["pData","gData",0,1,OPCODES.NUM_OPERANDS_ANY,False,True],
      "TITLE" : ["pHed","gHed",0,1,1,False,True],
      "STE" : ["pSte","gSte",0o235,0,0,False,False],
#     "NOP" : ["pNoPer","gdirect",0o235,0,0,False,False],
      "NOP" : ["pNoPer","gdirect",0o220,0,0,False,False], #  Karma NOP
      "NOP1" : ["pNoPer","gdirect",0o336,0,0,False,False], # see Series 80 wiki
      })
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
#      initialize opcode
#
       self.extendOpcodes()
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
# Entry point ncas --------------------------------------------------------
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
   ncas= clsNcas()
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

