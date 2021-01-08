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
from .capcommon import capasmError,BYTESTOSTORE,parseFunc,OPCODES, \
     MESSAGE,clsSymDict, CAPASM_VERSION, CAPASM_VERSION_DATE, \
     clsConditionalAssembly, clsGlobVar, clsToken, clsLineScanner, \
     clsObjWriter, clsListWriter, clsSourceReader, clsParserInfo, \
     clsParsedOperand, clsCodeInfo, clsInvalidOperand, clsParsedNumber, \
     clsParsedString, clsParsedLabel, clsParsedRegister, clsCodeGeneratorBase, \
     clsParserBase

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
      return
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
#  Parse DEF and VAL
#
   def pDef(self):
      if self.__scannedOpcode__.string== "DEF":
         self.__opcodeLen__=2
      else:
         self.__opcodeLen__=1
      return[self.parseLabelOp(0)]

      
#
#  Parse ORG pseudoop
#
   def pOrg(self):
      address=self.parseAddress(0)
      if address!=clsParserInfo.ILL_NUMBER:
         self.__globVar__.ORG=address 
      return []
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
#  extend the OPCODES dictionary with the capasm specific OPS
#
   def extendOpcodes(self):
      OPCODES.extendDict( {
      "RTN" : ["pNoPer","gdirect",0o236,0,0,False,False,False],
      "ABS"  : ["pAbs","gNil",0,1,2,False,False,False],
      "FIN"  : ["pFin","gNil",0,0,0,False,False,False],
      "LST"  : ["pNil","gNil",0,0,0,False,False,False],
      "UNL"  : ["pNil","gNil",0,0,0,False,False,False],
      "GLO"  : ["pNil","gNil",0,1,1,False,False,False],
      "ASC"   : ["pAsc","gData",0,1,256,False,False,False],
      "ASP"   : ["pAsc","gData",0,1,256,False,False,False],
      "NAM"   : ["pNam","gNam",0,1,2,False,False,False],
      "BSZ"   : ["pBsz","gGenZ",0,1,1,False,False,False],
      "BYT"   : ["pByt","gData",0,1,256,False,False,False],
      "OCT"   : ["pByt","gData",0,1,256,False,False,False],
      "DAD"   : ["pEqu","gNil",0,1,1,False,False,False],
      "DEF"   : ["pDef","gDef",0,1,1,False,False,False],
      "EQU"   : ["pEqu","gNil",0,1,1,False,False,False],
      "GTO"   : ["pGto","gGto",0,1,1,False,False,False],
      "VAL"   : ["pDef","gDef",0,1,1,False,False,False],
      "ORG"   : ["pOrg","gNil",0,1,1,False,False,False],
      "SET"   : ["pCondSet","gNil",0,1,1,False,False,False],
      "CLR"   : ["pCondClr","gNil",0,1,1,False,False,False],
      "AIF"   : ["pCondIfSet","gNil",0,1,1,False,False,True],
      "DIF"   : ["pCondIfDef","gNil",0,1,1,False,False,True],
      "EIF"   : ["pCondEndif","gNil",0,0,0,False,False,True],
      "ELS"   : ["pCondElse","gNil",0,0,0,False,False,True],
      "INC"   : ["pInc","gNil",0,1,1,False,False,False],
      "LNK"   : ["pInc","gNil",0,1,1,False,False,False],
      "HED"   : ["pHed","gHed",0,1,1,False,False,False],
      "LOC"   : ["pLoc","gGenZ",0,1,1,False,False,False],
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
       extendedChecks=False,  symNamLen=6,useHex=False, definedFlags=[], \
       globalSymbolFile="none"):
#
#      initialize opcodes
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
       self.__globVar__.condAssembly=clsConditionalAssembly(definedFlags)
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
      help="global symbol file. Use either the built-in symbol table names {\"85\",\"87\",\"75\",\"none\"} or specify a file name for a custom table (default: none)",default="none")
   argparser.add_argument("-r","--reference",type=int,default=1,\
      help="symbol reference 0:none, 1:short, 2:full (default:1)",\
      choices=[0,1,2])
   argparser.add_argument("-p","--pagesize",type=int,default=66, \
      help="lines per page (default: 66)",action=argPageSizeCheck)
   argparser.add_argument("-w","--width",type=int,default=80, \
      help="page width (default:80)",action=argWidthCheck)
   argparser.add_argument("-c","--check",help="activate additional checks", \
      action='store_true')
   argparser.add_argument("-d","--define",action='append',default=[],\
      help="define conditional flag with value True")
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
           definedFlags=args.define, \
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

