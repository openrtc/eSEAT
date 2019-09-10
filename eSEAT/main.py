#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''eSEAT (Extened Simple Event Action Transfer)

Copyright (C) 2009-2014
    Yosuke Matsusaka and Isao Hara
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST), Japan
    All rights reserved.
  Licensed under the MIT License (MIT)
  http://www.opensource.org/licenses/MIT
'''

############### import libraries
from __future__ import print_function
import sys
import os
import getopt
import codecs
import locale
import time
import signal
import re
import traceback
import optparse
import threading
import subprocess

try:
  import utils
  from viewer import OutViewer
except:
  from . import utils
  from .viewer import OutViewer


if os.getenv('SEAT_ROOT') :
  rootdir=os.getenv('SEAT_ROOT')
else:
  rootdir='/usr/local/eSEAT/'

sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir,'libs'))
sys.path.append(os.path.join(rootdir,'3rd_party'))

opts = None

#
#
########
#  for OpenRTM-aist
try:
  import RtcAdaptor
except:
  try:
    from . import RtcAdaptor
  except:
    RtcAdaptor=None

try:
  from core import main_node
except:
  from .core import main_node

###############################################################
#
__version__ = "2.5"

#
#
def main(mlfile=None, daemon=False):
  try:
    if RtcAdaptor:
      RtcAdaptor.main_rtm(mlfile, daemon)
    else:
      main_node(mlfile,daemon)
  except:
     pass


#########################################################################
#
#  M A I N 
#
if __name__=='__main__':
  main()
