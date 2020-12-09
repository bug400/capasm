#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Helper script to start an entry point of the CAPASM software suite
# from package directory. 
#
#
# Note: this script must not be moved out of this directory
#
import sys
import os
PYTHON_REQUIRED_MAJOR=3
PYTHON_REQUIRED_MINOR=6

from capasm import capasm, caplif, caplex, capglo, caprom, capconv, ncas
entryPointDict= { "capasm": capasm,
                  "caplex": caplex,
                  "caplif": caplif,
                  "capglo": capglo,
                  "caprom": caprom,
                  "capconv":capconv,
                  "ncas": ncas,
                }
def usage():
   print("Usage:")
   print("python startup.py <progname> parameters ...")
   print("where <progname> is one of:",end="")
   for e in entryPointDict.keys():
       print(" "+e,end="")
   print("")
   print("")
#
# check Python version, we need at least version 3.6
#
if sys.version_info < ( PYTHON_REQUIRED_MAJOR, PYTHON_REQUIRED_MINOR):
    # python too old, kill the script
    sys.exit("This script requires Python "+str(PYTHON_REQUIRED_MAJOR)+"."+str(PYTHON_REQUIRED_MINOR)+" or newer!")
#
# append this local package dir to the Python library path
#
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#
# check the number of parameters
#
if len(sys.argv)<=1:
   usage()
else:
   progName=sys.argv[1]
#  del sys.argv[1]
   sys.argv=sys.argv[1:]
#  try:
   if True:
      entryPointDict[progName]()
#  except KeyError:
#     usage()
