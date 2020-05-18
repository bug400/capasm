#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Helper script to start capasm from package directory
#
import sys
import os
PYTHON_REQUIRED_MAJOR=3
PYTHON_REQUIRED_MINOR=6

if sys.version_info < ( PYTHON_REQUIRED_MAJOR, PYTHON_REQUIRED_MINOR):
    # python too old, kill the script
    sys.exit("This script requires Python "+str(PYTHON_REQUIRED_MAJOR)+"."+str(PYTHON_REQUIRED_MINOR)+" or newer!")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from capasm import mklex75
mklex75()
