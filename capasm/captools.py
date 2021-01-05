#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This module contains the following tools for the CAPASM assembler:
# - static methods to support regression testing
# - capglo utilty to create global symbol class files from text files
# - caplif utility to put assembled lex files into an import lif image file
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
# 18.05.2020 jsi:
# - start change log
# 19.05.2020 jsi
# - added clsSymClassGenerator class
# - added capglo entry point
# - removed main entry point
# 22.05.2020 jsi
# - raise custom exception on fatal error
# 29.05.2020 jsi
# - much refactoring
# - regression test utilities rewritten
# - removed mklex75 entry point
# - added caplex and caplif entry points and the corresponding classes
# 29.06.2020 jsi
# - added caprom tool
# 04.07.2020 jsi
# - fix rom number checking
# 26.07.2020 jsi
# - catch I/O errors in caplglo generate method
# 27.07.2020 jsi
# - added capconv tool
#
import sys, argparse,os, codecs,re,contextlib
from pathlib import Path
from itertools import groupby
from .capcommon import capasmError, clsLineScanner, parseFunc, CAPASM_VERSION,clsDateTime

#
# silently remove files, continue if they do not exist
#
def silentRemove(*args):
   for fileName in args:
      with contextlib.suppress(FileNotFoundError):
         os.remove(fileName)
   return False
#
# AsmSourceFileConverter class -----------------------------------------
# This class converts a tokenized Series 80 assembler source file 
# which was for example extracted from a lif image file with "hpdir -extract"
# or "lifget -r" to an ascii file. The input file format (HP-85 or
# HP-87 style is auto detected
#
class clsAsmSourceFileConverter(object):

   def __init__(self):
      super().__init__()
      self.__outFile__=None
#
#  output comment
#
   def printComment(self,d):
      self.__outFile__.write("! ")
      for c in d:
         self.__outFile__.write(chr(c))
#
#  output label or blanks
#   
   def printLabel(self,d,labelLength):
      for i in range(0,labelLength):
         if d is None:
            self.__outFile__.write(" ")
         else:
            self.__outFile__.write(chr(d[i]))
      self.__outFile__.write(" ")
#
#  process opcode, operands and trailing comment
#
   def printOpcodeAndOperand(self,d):
      operand=""
      for i in range(0,3):
         operand+=chr(d[i])
      d=d[3:]
      if operand in ["SBB","SBM","CMB","CMM","ANM","ADB","ADM", \
         "PUB","PUM","POB","POM","LDB","LDM","STB","STM"]:
         if chr(d[0]) in ["D","I"]:
            operand+=chr(d[0])
            d=d[1:]
         else:
            operand+=" "
      else:
         operand+=" "
      i=4
      self.__outFile__.write(operand)
      self.__outFile__.write(" ")
      for c in d:
         if c== 0xFE:
            for j in range(i,20):
                self.__outFile__.write(" ")
            self.__outFile__.write(" ! ")
            continue
         if c==0xFF:
            continue
         self.__outFile__.write(chr(c))
         i+=1

#
   def convert(self,inputFileName,outputFileName):
      print("")
      print("Converting file "+inputFileName+" to "+outputFileName)
      try: 
         infile=open(inputFileName,"rb")
         asmBytes=infile.read()
         infile.close()
      except OSError:
         raise capasmError("cannot open/read input file")
     
      try: 
         self.__outFile__=open(outputFileName,"w")
      except OSError:
         raise capasmError("cannot create output file")
#
#     detect file type and skip header
#
      k=len(asmBytes)
      count=0
      if asmBytes[6]==0x20:
         is85=True
         i=24
      elif asmBytes[6]==0x10 or asmBytes[6]==0x50:
         is85=False
         i=32
      else:
         raise capasmError("Illegal input file")
#
#     process records
#   
      try:
         while i < k:
#
#        line number, HP87 has one more digit
#
            if not is85:
               labelLength=8
               h=asmBytes[i]
               if h==10:
                  break
               lineNumber="{:1x}{:02x}{:02x} ".format(asmBytes[i],\
                  asmBytes[i+1],asmBytes[i+2])
               i+=1
            else:
               labelLength=6
               if asmBytes[i]==0x99 and asmBytes[i+1]==0xA9:
                  break
               lineNumber="{:02x}{:02x} ".format(asmBytes[i+1],asmBytes[i])
            i+=2
            count+=1
#
#        store tokenized assembler statement in d
#
            l=asmBytes[i]
            i+=1
            d=bytearray(0)
            self.__outFile__.write(lineNumber)
            for j in range (0,l):
               d.append(asmBytes[i])
               i+=1
            if d[-1]!=0x0E:
               raise capasmError("Illegal End byte detected")
            d=d[0:-1]
#
#        comment line
#
            if d[0]==0xFE:
               self.printComment(d[1:-1])
               self.__outFile__.write("\n")
               continue
#
#        label
#
            if d[0]==0xFF:
               d=d[1:]
               self.printLabel(d,labelLength)
               d=d[labelLength:]
            else:
               self.printLabel(None,labelLength)
#
#        opcode, operands and trailing comment
#
            self.printOpcodeAndOperand(d)
            self.__outFile__.write("\n")
         self.__outFile__.close()
      except OSError:
         raise capasmError("cannot write to output file")
      print("{:d} assembler source lines written to file {:s}".format(count,\
            outputFileName))
      return False

#
# SymbolFileConverter class ---------------------------------------------
# This class converts a Series 80 binary global symbols file 
# which was for example extracted from a lif image file with "hpdir -extract"
# or "lifget -r" to an ascii file
#
class clsSymbolFileConverter(object):

   def __init__(self):
      super().__init__()
#
#  conversion method
#  The binary input file has a fixed record length of 256 bytes. Each
#  global symbol has an entry of 11 bytes length. An entry may span
#  a record boundary. A zero length record marks end of file.
#
   def convert(self,inputFileName,outputFileName):

      tdict= {0: "EQU", 1: "DAD", 2:"DAD"}
      print("")
      print("Converting file "+inputFileName+" to "+outputFileName)
      try: 
         infile=open(inputFileName,"rb")
         gloBytes=infile.read()
         infile.close()
      except OSError:
         raise capasmError("cannot open/read input file")
     
      try: 
         outfile=open(outputFileName,"w")
      except OSError:
         raise capasmError("cannot create output file")

      i=0
      count=0
      try:
         while True:
            header=gloBytes[i]
#
#           check header byte 0xDF: normal entry, 0xCF: entry spans two records
#
            if not header in [0xDF, 0xCF]:
               raise capasmError("illegal input file")
            i+=1
#
#           get length, if zero length then exit loop
#
            length=gloBytes[i]
            if (length==0):
               break
            i+=1
#
#           extract bytes of entry
#
            d=bytearray(0)
#
#           if the entry spans two records, skip the header at the
#           beginning of the second line
#
            for j in range (0,length):
               d.append(gloBytes[i])
               i+=1
               if i % 256 == 0:
                  i+=3
#
#           get type of symbol
#
            typ=gloBytes[i]
#
#           extract symbol name
#
            symName=""
            ci=length-3
            while d[ci]!=0:
               symName+=chr(d[ci])
               ci-=1
#
#           get symbol value
#
            symValue=d[-2]*256+d[-1]
            d=None
            outfile.write("{:8s} {:3s} {:o}\n".format(symName,tdict[typ],\
              symValue))
            i+=1
            count+=1
         outfile.close()
      except OSError:
         raise capasmError("cannot write to output file")
      print("{:d} symbols generated in file {:s}".format(count,outputFileName))
      return False
#
#
# SymCassGenerator class -------------------------------------------------
#
# An object of this class reads a global symbol file which must match
# the syntax rules of the CAPASM assembler. Only comments, DAD (or ADDR) and EQU
# statements are allowed in this file.
#
# The object generates a Python script which a static class "globalSymbols"
# to access global symbols for a specific machine. At the moment CAPASM 
# supports the script file names globals75.py, globals85.py, globals87.py. 
# The -m option of the assembler controls which file is used for the assembly.
#
# The program checks for duplicate global symbol definitions which exist
# in the file globals75.txt. At the moment duplicate definitions overwrite 
# an existing definition. The reason for duplicateentries is under 
# investigation.
#
class clsSymClassGenerator(object):

   SYM_DAD=0
   SYM_EQU=1

   def __init__(self):
      super().__init__()

#
#  generate method:
#  convert file with name inputFileName to a python file with a global
#  symbol class definition which has the name outputFileName
#
#  Returns:
#     False: everything o.k.
#     True: errors or duplicates
#  Raises capasmError on i/o error
#
   def generate(self,inputFileName,outputFileName,labelLen=8,style="capasm"):

      if style== "ncas":
         labelLen=32
         lineScanner=clsLineScanner("*",";","'`^"+'"')
         parseFunc.DELIMITER="'"+'"'
         parseFunc.LABELMATCHSTRING=\
          "[A-Za-z][A-Za-z0-9_$\+\-\.#/?\(\!\&)=:<>\|@*^]{0,"
      else:
         lineScanner=clsLineScanner("!","!",'"')
         parseFunc.DELIMITER='"'
         parseFunc.LABELMATCHSTRING="[(^0-9)(\x20-\x7A|\|)][\x20-\x7A|\|]{0,"
      symDict= { }
      duplicates=0
      errors=0
      hasErrors=False
      print("")
      print("Processing file "+inputFileName)
      try: 
         infile=codecs.open(inputFileName,"r",encoding="ISO-8859-1",\
           errors="ignore")
      except OSError:
         raise capasmError("cannot open input file")
     
      try: 
         outfile=open(outputFileName,"w")
      except OSError:
         raise capasmError("cannot create output file")
#
#        Write global symbol class definition
#
      try:
         outfile.write("#!/usr/bin/python3\n# -*- coding: utf-8 -*-\n")
         outfile.write("#\n# Global symbols from file "+inputFileName+"\n")
         outfile.write("# Autogenerated file, do not modify!\n")
         outfile.write("#\n")
         outfile.write("class globalSymbols():\n")
         outfile.write("\n")
         outfile.write("   symbols= {\n")
#
#        Process lines
#
         lineCount=0
         while True:
            line=infile.readline()
            if not line:
               break
            line=line.strip("\r\n")
            lineCount+=1
#
#        Scan line, we get a list of token:
#        - lineNumber (from source code file, if any, ignored here)
#        - label
#        - opcode
#        - list of operands which should consist only of the symbol value 
#
            scannedLine=lineScanner.scanLine(line)
            lineNumber=str(lineCount)
#
#        Empty line
#
            if scannedLine[1]==None:
               continue
#
#        Comment
#
            symbolName=scannedLine[1].string
            if symbolName[0]=="*" or symbolName=="!":
               continue
#
#        Check symbol name
#
            if parseFunc.parseLabel(symbolName,labelLen) is None:
               print("Line: "+lineNumber+": "+line)
               print("illegal symbol")
               errors+=1
               continue
#
#        Check opcode, only "EQU" and "DAD" are allowed
#
            if scannedLine[2] is None:
               print("Line: "+lineNumber+": "+line)
               print("missing opcode")
               errors+=1
               continue
            opCode= scannedLine[2].string
            if opCode== "EQU":
               opTyp=clsSymClassGenerator.SYM_EQU
            elif opCode == "DAD" or opCode == "ADDR":
               opTyp=clsSymClassGenerator.SYM_DAD
            else:
               print("Line: "+lineNumber+": "+line)
               print("illegal opcode")
               errors+=1
               continue
#
#        Check value which must be a valid number
#
            if len(scannedLine[3])!=1:
               print("Line: "+lineNumber+": "+line)
               print("illegal label value")
               errors+=1
               continue
            value=scannedLine[3][0].string
            intValue=parseFunc.parseNumber(value)
            if intValue==None:
               print("Line: "+lineNumber+": "+line)
               print("illegal label value")
               errors+=1
               continue
            if intValue > 0xFFFF:
               print("Line: "+lineNumber+": "+line)
               print("illegal label value")
               errors+=1
               continue
#
#        Check and print duplicates
#
            if symbolName in symDict.keys():
               print("Line: "+lineNumber+": "+line)
               ret=symDict[symbolName]
               print("symbol redefined, first definition was at line: "+ \
                  ret[0]+" opcode: "+ret[1]+" value: "+ret[2])
               outfile.write('      "'+symbolName+'" : ['+str(opTyp)+ \
                    ","+str(intValue)+"],\n")
               duplicates+=1
            else:
               symDict[symbolName]=[lineNumber,opCode,value]
               outfile.write('      "'+symbolName+'" : ['+str(opTyp)+ \
                       ","+str(intValue)+"],\n")
#
#     All input line processed, write access method
#
         infile.close()
         outfile.write("   }\n")
         outfile.write("   @staticmethod\n")
         outfile.write("   def get(name):\n")
         outfile.write("      if name[0]=='=':\n")
         outfile.write("         name=name[1:]\n")
         outfile.write("      if name in globalSymbols.symbols.keys():\n")
         outfile.write("         return globalSymbols.symbols[name]\n")
         outfile.write("      else:\n")
         outfile.write("         return None\n")
         outfile.write("\n")
         outfile.close()
      except OSError:
         raise capasmError("I/O Error while converting global symbols file")
      print("Errors {:d}, duplicate entries {:d} ".format(errors,duplicates))
#
#     return error condition
#
      hasErrors=(errors!=0) or (duplicates!=0)
      return hasErrors
#
# Static classes for the comparision of files
# Returns: [l1, l2, diffs]
# l1: length of file 1
# l2: length of file 2
# diffs: list of differences, each member is a list of [pos, num] where
#        pos: byte position of difference
#        num: number of consecutive bytes that are different
#
# return None on file i/o error
#
#
class fileDiff(object):

   @staticmethod
   def compareBin(fileName1, fileName2):
      try:
         name=fileName1
         f=open(name,"rb")
         f1=f.read()
         f.close()
         name=fileName2
         f=open(name,"rb")
         f2=f.read()
         f.close()
         l1=len(f1)
         l2=len(f2)
         diffs = [(next(g), len(list(g))+1)
               for k, g in groupby(range(min(len(f1), len(f2))), \
                  key=lambda i: f1[i] != f2[i]) if k]
      except (OSError,FileNotFoundError):
         print("Can not read binary file: "+name)
         return None
      return l1,l2,diffs

   @staticmethod
   def compareAsc(fileName1, fileName2):
      try:
         name=fileName1
         f=open(name,"r")
         f1=[]
         while True:
            l=f.readline()
            if not l:
               break
            f1.append(l.strip("\r\n"))
         f.close()
         name=fileName2
         f=open(name,"r")
         f2=[]
         while True:
            l=f.readline()
            if not l:
               break
            f2.append(l.strip("\r\n"))
         f.close()
         l1=len(f1)
         l2=len(f2)
         diffs = [(next(g), len(list(g))+1)
               for k, g in groupby(range(min(len(f1), len(f2))), \
                  key=lambda i: f1[i] != f2[i]) if k]
      except (OSError,FileNotFoundError):
         print("Can not read ascii file: "+name)
         return None
      return l1,l2,diffs
      
   @staticmethod
   def testBinFile(fileName1,fileName2):
      ret=fileDiff.compareBin(fileName1,fileName2)
      if ret is None:
         return True
      ret=fileDiff.postProc(fileName1, fileName2,ret)
      return ret
   
   @staticmethod
   def testAscFile(fileName1, fileName2):
      ret=fileDiff.compareAsc(fileName1,fileName2)
      if ret is None:
         return True
      ret=fileDiff.postProc(fileName1, fileName2,ret)
      return ret
      
   @staticmethod
   def postProc(fileName1,fileName2,ret):
      notIdentical=False
      l1,l2,diffs=ret
      if l1 !=l2:
         notIdentical=True
         print(fileName1+"!="+fileName2+", file length differs: "\
                +str(l1)+"!="+str(l2))
   
      if len(diffs)!=0:
         notIdentical= True
         print(fileName1+"!="+fileName2+": compare failed at pos: ",end="")
         print (diffs)
      return notIdentical

#
# LIF item classes ----------------------------------------------------------
#
# This classes generate various items we need to create the structure of
# LIF files and volumes
#
# Base class for all LIF items
#
class clsBinaryItem(object):
   def __init__(self):
      super().__init__()
      self.__objectCode__= None
#
#  get bytes of item
#
   def getBytes(self):
      return self.__objectCode__

#
# get byte length of item
#
   def getLen(self):
      return len(self.__objectCode__)
#
# LIF item: file content ------------------------------------------------
#
class clsObjectFile(clsBinaryItem):

   def __init__(self,filename):
      super().__init__()
      try:
         f=open(filename,"rb")
         self.__objectCode__=f.read()
         f.close()
      except OSError:
         raise capasmError("Can not read binary object file")
#
# LIF item: volume header, always 512 bytes long ------------------------
#
class clsVolumeHeader(clsBinaryItem):

   def __init__(self):
      super().__init__()
      self.__dt__=clsDateTime()

   def create(self,length,machine,isRegressionTest):
#
#     for the HP75 we create a standard Volume header with 2 sectors
#
      if machine=="75":
         self.__objectCode__=bytearray(512)
         self.__objectCode__[11]=2         # start of directory
#
#     for Series80 we create a 256 byte sector, because
#     the HP-85 emulator requires that for upload files
      else:
         self.__objectCode__=bytearray(256)
         self.__objectCode__[11]=2         # start of directory
      self.__objectCode__[0]=0x80       # LIF volume identifier
      labelName="HFSLIF"                # Volumen label, always HFSLIF
      i=2
      for c in labelName:        
         self.__objectCode__[i]=ord(c)
         i+=1
      self.__objectCode__[12]=0x10      # HP-3000 LIF identifier 
      self.__objectCode__[19]=0x01      # one sector in directory
      self.__objectCode__[21]=0x01      # LIF version number
#
#     Volume size
#
      self.__objectCode__[27]=0x01      # tracks per surface
      self.__objectCode__[31]=0x01      # number of surfaces
      length+=+512+255              # calculate length of volume in blocks
      self.__objectCode__[32]=0 
      self.__objectCode__[33]= (length >> 24) & 0xFF
      self.__objectCode__[34]= (length >> 16) & 0xFF
      self.__objectCode__[35]= (length >> 8) & 0xFF
#
#     Date and Time
#
      if not isRegressionTest:
         self.__objectCode__[36]=self.__dt__.bcdYear
         self.__objectCode__[37]=self.__dt__.bcdMonth
         self.__objectCode__[38]=self.__dt__.bcdDay
         self.__objectCode__[39]=self.__dt__.bcdHour
         self.__objectCode__[40]=self.__dt__.bcdMin
         self.__objectCode__[41]=self.__dt__.bcdSec

#
# LIF item: directory entry, always 32 bytes long -------------------------
#
class clsDirEntry(clsBinaryItem):

   def __init__(self):
      super().__init__()
      self.__dt__=clsDateTime()

   def createFileEntry(self,length,machine,filename,lexOnly,isRegressionTest):
      origLength=length
      self.__objectCode__=bytearray(32)
      i=0
      for c in filename:        # LIF file name
         self.__objectCode__[i]=ord(c)
         i+=1
      self.__objectCode__[8]=0x20   # pad file name
      self.__objectCode__[9]=0x20
      if machine =="75":              # file type for HP-75: LEX75
         self.__objectCode__[10]=0xE0
         self.__objectCode__[11]=0x89
      else:                           # file type for Series 80: BPGM binary P.
         self.__objectCode__[10]=0xE0
         self.__objectCode__[11]=0x08

      if not lexOnly:
         self.__objectCode__[15]=3     # start at sector 3

      length+=255               # calculate length in blocks
      self.__objectCode__[16]=0 
      self.__objectCode__[17]= (length >> 24) & 0xFF
      self.__objectCode__[18]= (length >> 16) & 0xFF
      self.__objectCode__[19]= (length >> 8) & 0xFF
      if not isRegressionTest:
         self.__objectCode__[20]=self.__dt__.bcdYear
         self.__objectCode__[21]=self.__dt__.bcdMonth
         self.__objectCode__[22]=self.__dt__.bcdDay
         self.__objectCode__[23]=self.__dt__.bcdHour
         self.__objectCode__[24]=self.__dt__.bcdMin
         self.__objectCode__[25]=self.__dt__.bcdSec
      self.__objectCode__[26]=0x80  # Implementing bytes
      self.__objectCode__[27]=0x01
      if machine =="75":            # HP-75 Password
         self.__objectCode__[28]=0x20  
         self.__objectCode__[29]=0x20
         self.__objectCode__[30]=0x20
         self.__objectCode__[31]=0x20
      else:                         # Series 80 file and block length
         self.__objectCode__[28]=origLength & 0xFF
         self.__objectCode__[29]=(origLength >> 8) & 0xFF
         self.__objectCode__[30]=0x00
         self.__objectCode__[31]=0x01

#
#  this creates an empty directory entry, file type is 0xFFFD
#
   def createNullEntry(self):
      self.__objectCode__=bytearray(32)
      self.__objectCode__[10]=0xFF
      self.__objectCode__[11]=0xFF
      
#
#  LIF item: HP-75 RAM file system header --------------------------------
#
#  This header must be prepended to the file content.
#  Series 80 computers do not need that because they start with a NAM header
#
class clsFileHeader(clsBinaryItem):

   def __init__(self):
      super().__init__()

   def create(self,length,filename):
      self.__objectCode__=bytearray(18)
      length=length+18          # length of file including header
      low= length & 0xFF
      high= length >> 8
      self.__objectCode__[2]=low
      self.__objectCode__[3]=high
      self.__objectCode__[4]=0x8D   # access bits, fake
      self.__objectCode__[5]=0x4C   # "L"
      self.__objectCode__[6]=0xC7   # date and time faked
      self.__objectCode__[7]=0xBA
      self.__objectCode__[8]=0x7F
      self.__objectCode__[9]=0xA0
      i=10
      for c in filename:
         self.__objectCode__[i]=ord(c)
         i+=1
#
# Check the filename which is used in the LIF directory entry
#
def makeLifFileName(fName,machine):
   fName=fName.upper()
   if len(fName)> 8:
      raise capasmError("LIF filename: "+fName+" exceeds 8 characters")
   if machine=="75":
      match=re.fullmatch("[A-Z][A-Z0-9]*",fName)
   else:
      match=re.fullmatch("[A-Z][A-Z0-9_]*",fName) # allow underscores here
   if not match:
      raise capasmError("illegal LIF file name: "+fName)
   fName=fName.ljust(8)
   return fName
#
# LIF LEX and Image creator class ----------------------------------------
#
class clsLifCreator(object):

   def __init__(self):
      super().__init__()
#
#  create LIF LEX files (lexOnly= True) from binary input file
#  - or -
#  create LIF import image (lexOnly=False) from binary input file
#
#  Returns:
#     True: everything o.k.
#  Raises capasmError on i/o error or if the LIF directory file name is
#  illegal
#
   def create(self,binFileName,machine,outputFileName="",lifFileName="",
              lexOnly=False):
#
#     check if we run in regression test mode
#
      isRegressionTest=False
      if os.getenv("CAPASMREGRESSIONTEST"):
         isRegressionTest=True
#
#     build name of file image or lex file if not specified
#
      if outputFileName=="":
         if lexOnly:
            outputFileName=Path(binFileName).with_suffix(".lex").name
         else:
            outputFileName=Path(binFileName).with_suffix(".dat").name
#
#     build the file name for the LIF directory entry, if not specified
#
      if lifFileName=="":
         if machine == "75":
            fname=Path(binFileName).stem
         else:
            fname="WS_FILE"
      else:
         fname=lifFileName
      lifFileName=makeLifFileName(fname,machine)
#
#     read object file into memory
#
      objectFile=clsObjectFile(binFileName)
#
#     create the RAM file header for the HP-75
#
      fileLength=objectFile.getLen()
      if machine == "75":
         fileHeader=clsFileHeader()
         fileHeader.create(fileLength,lifFileName)
         fileLength+=18
#
#     create directory Entry
#
      dirEntry=clsDirEntry()
      dirEntry.createFileEntry(fileLength,machine,lifFileName, \
                      lexOnly,isRegressionTest)
#
#     create LIF volume header
#
      volHeader=clsVolumeHeader()
      volHeader.create(fileLength, machine, isRegressionTest)
#
#     write LIF image or LEX file
#
      try:
         imgFile=open(outputFileName,"wb")
#
#     if LEX file: write only the directory header
#
         if lexOnly:
            imgFile.write(dirEntry.getBytes())
         else:
#
#     if LIF image file, write volume header and directory
#
            imgFile.write(volHeader.getBytes())
            imgFile.write(dirEntry.getBytes())
            dirEntry.createNullEntry()
            for i in range(0,7):
               imgFile.write(dirEntry.getBytes())
#
#     HP-75 only: write RAM file header
#
         if machine == "75":
            imgFile.write(fileHeader.getBytes())
#
#     write file content
#
         imgFile.write(objectFile.getBytes())
#
#        fill up remaining bytes in sector
#   
         rem=256-(fileLength % 256)
         imgFile.write(bytearray(rem))
         imgFile.close()
      except OSError:
         raise capasmError("cannot write lif image file")
         
      if lexOnly:
         print("LEX file "+outputFileName+" created")
      else:
         print("LIF image file "+outputFileName+" created which contains: " \
          + lifFileName+" (LEX"+machine+")")
#
#     we return always false here, because all error conditions raise
#     an exception
#
      return False
#
# ROM file creator class ----------------------------------------
#
class clsRomCreator(object):

   def __init__(self):
      super().__init__()
#
#  create LIF import image (lexOnly=False) from binary input file
#
#  Returns:
#     True: everything o.k.
#  Raises capasmError on i/o error or if the ROM size is too small
#
   def create(self,binFileName,romFileName="",romSize=2):
#
#     check if we run in regression test mode
#
      isRegressionTest=False
      if os.getenv("CAPASMREGRESSIONTEST"):
         isRegressionTest=True
#
#     build name of file image or lex file if not specified
#
      if romFileName=="":
         romFileName=Path(binFileName).with_suffix(".rom").name
#
#     read object file into memory, check rom number and rom size
#
      romSize=romSize*1024
      rom75=False
      objectFile=clsObjectFile(binFileName)
      code=bytearray(objectFile.getBytes())
#
#     HP-75 has always ROM number 0xE3 and the HP-85 style complementary no
#
      if code[0]==0xE3 and code[1]==0x1C:
         rom75=True
         if romSize < len(code)+2:
            raise capasmError("ROM size too small")
         print("creating HP-75 ROM file ",romFileName)
#
#     determine if we have a HP-85 or HP-87 file
#
      else:
         romNo=code[0]
         checkRomNo= ~ romNo &0xFF
         if checkRomNo== code[1]:
            print("creating HP-85 ROM file ",romFileName)
         elif checkRomNo+1 == code[1]:
            print("creating HP-87 ROM file ",romFileName)
         else:
            raise capasmError("Invalid ROM number")
         if romSize < len(code)+4:
            raise capasmError("ROM size too small")
#
#     fill code to length of rom
#
      fill=romSize - len(code)
      for i in range(0,fill):
         code.append(0)
#
#     HP-75 check sum
#
      if rom75:
         c=0
         i=0
         while(i<len(code)):
            c+=code[i]
            while c> 255:
               c+=1
               c-= 256
            i+=1
         cInv= ~c &0xFF
         code[-1]=cInv
      else:
#
#     determine secondary checksum, thanks to Philippe (hp80series@groups.io)
#
         t=0
         i=0
         while(i< len(code)-4):
            c1=code[i]
            i+=1
            c2=code[i]
            i+=1
            w = (c1 & 0xff) + ((c2 & 0xff)<<8)
            for j in range (0,16):
               r26 = t & 0xff
               r27 = t>>8
               r45 = r27
               r27 = (r27<<4) & 0xff
               r26 = ((r26<<1) & 0xff) | (w & 1)
               w = w>>1
               r45 = r45 ^ r26
               r45 = r45 ^ r27
               if (r45 & 1):
                   r45 = (r45 + 0x80) & 0xff
               t = ((t<<1) & 0xffff) | (r45 >>7)
         code[-4]=(t & 0xFF)
         code[-3]=((t>>8) & 0xFF)
#
#     determine primary checksum, thanks to Philippe (hp80series@groups.io)
#
         t=0
         i=0
         while(i< len(code)-2):
            c1=code[i]
            i+=1
            c2=code[i]
            i+=1
            t = t + (c1 & 0xff) + ((c2 & 0xff)<<8)
         s = ((t>>16) + (t & 0xffff)) & 0xffff
         t = s>>8
         s = s & 0xff
         code[-2]=(255-s)
         code[-1]=(255-t)
#
#     write rom file
#
      try:
         romFile=open(romFileName,"wb")
         romFile.write(code)
         romFile.close()
      except OSError:
         raise capasmError("cannot write rom file")
      return False
#
# entry point caplif ------------------------------------------------------
# put assembled binary file to an import LIF image file
#
def caplif():        # pragma: no cover
#
#  command line arguments processing
#
   argparser=argparse.ArgumentParser(description=\
   "Utility to put an assembled binary file into an import LIF image file",\
   epilog="See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   argparser.add_argument("binfile",help="binary object code file (required)")
   argparser.add_argument("-m","--machine",choices=['75','85','87'], \
      help="Machine type (default=85)",default='85')
   argparser.add_argument("-l","--lifimagefilename", help=\
     "name of the Upload LIF image file (default: objectfile name with suffix .dat)",\
      default="")
   argparser.add_argument("-f","--filename", \
      help="name of the LIF directory entry (default: WS_FILE for Series 80, deduced from object file name for HP-75)",\
      default="")
   args= argparser.parse_args()

   l=clsLifCreator()
   try:
      l.create(args.binfile,args.machine,args.lifimagefilename,args.filename,
               False)
   except capasmError as e:
      print(e.msg+" -- program terminated")
      sys.exit(1)
#
# entry point caplex ------------------------------------------------------
# convert assembled binary file to a LIF file of type LEX75 or BPGM80
#
def caplex():        # pragma: no cover
#
#  command line arguments processing
#
   argparser=argparse.ArgumentParser(description=\
   "Utility to convert an assembled binary file into a LIF file of type LEX75 or BPGM80",\
   epilog="See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   argparser.add_argument("binfile",help="binary object code file (required)")
   argparser.add_argument("-m","--machine",choices=['75','85','87'], \
      help="Machine type (default:85)",default='85')
   argparser.add_argument("-l","--lexfilename",help=\
     "name of the LIF output file (default: objectfile name with suffix .lex)",\
      default="")
   argparser.add_argument("-f","--filename", help=\
      "file name in the LIF header (default: deduced from objectfilename)",\
       default="")
   args= argparser.parse_args()

   l=clsLifCreator()
   try:
      l.create(args.binfile,args.machine,args.lexfilename,args.filename,
               True)
   except capasmError as e:
      print(e.msg+" -- program terminated")
      sys.exit(1)
#
# entry point capglo -------------------------------------------------------
# convert a list of input files  to a python files with a global
# symbol class definition which have the name of the input file with
# the suffix ".py"
#
def capglo():         # pragma: no cover

   p=argparse.ArgumentParser(description=\
   "Utility to convert global HP-85/HP-87/HP-75 symbol files for the capasm assembler",\
   epilog="See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   p.add_argument('inputfiles',nargs='+',help="list of gobal symbol assembler files (one argument required)")
   p.add_argument("-s","--style",help="Source style (capasm/ncas), default=capasm",default="capasm",choices=["capasm","ncas"])
   args=p.parse_args()

   gen=clsSymClassGenerator()
   hasErrors=False
   labelLen=6
   style=args.style
   for inputFileName in args.inputfiles:
      outputFileName=Path(inputFileName).with_suffix(".py").name
      try:
         hasErrors!=gen.generate(inputFileName,outputFileName,labelLen,style)
      except capasmError as e:
         print(e.msg+" -- program terminated")
         hasErrors=True
         break
   if hasErrors: 
     sys.exit(1)
#
# entry point caprom -------------------------------------------------------
#
# convert an assembled binary file to a Series 80 ROM file with checksums
#

def caprom():         # pragma: no cover

   argparser=argparse.ArgumentParser(description=\
   "Utility to convert an assembled binary file to a Series 80 ROM file",\
   epilog="See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   argparser.add_argument("binfile",help="binary object code file (required)")
   argparser.add_argument("-r","--romfilename",help=\
     "name of the LIF output file (default: objectfile name with suffix .lex)",\
      default="")
   argparser.add_argument("-s","--romsize",choices=[2,4,8,16,32],type=int, \
      help="ROM size in KB (default:2)",default=2)
   args= argparser.parse_args()

   l=clsRomCreator()
   try:
      l.create(args.binfile,args.romfilename,args.romsize)
   except capasmError as e:
      print(e.msg+" -- program terminated")
      sys.exit(1)
#
# entry point capconv -------------------------------------------------------
# convert a binary Series 80 global symbols file to an ascii file with
# DAD or EQU symbol definitions
#
def capconv():         # pragma: no cover

   p=argparse.ArgumentParser(description=\
   "Utility to convert binary HP-85/HP-87/HP-75 symbol files to ascii files",\
   epilog="See https://github.com/bug400/capasm for details. "+CAPASM_VERSION)
   p.add_argument('inputfiles',nargs='+',help="list of gobal symbol assembler files (one argument required)")
   p.add_argument("-t","--type",required=True,help="what to convert", \
      choices=["asm","glo"])
   args=p.parse_args()

   if args.type=="glo":
      conv=clsSymbolFileConverter()
      suffix=".glo"
   else:
      conv=clsAsmSourceFileConverter()
      suffix=".asm"
   hasErrors=False
   for inputFileName in args.inputfiles:
      outputFileName=Path(inputFileName).with_suffix(suffix).name
      try:
         hasErrors!=conv.convert(inputFileName,outputFileName)
      except capasmError as e:
         print(e.msg+" -- program terminated")
         hasErrors=True
         break
   if hasErrors: 
     sys.exit(1)
#
