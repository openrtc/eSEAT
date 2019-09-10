#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-

import sys
import string
import time
import new

try:
  import RTC
  import OpenRTM_aist
except:
  pass

class rtService(object):
  def __init__(self):
    self.class_name='rtService'
    return

  def new_method(self, name, func):
    val="self."+name+"=new.instancemethod("+func+", self,"+self.class_name+")"
    exec(val)

  def new_class(self, mod_name, if_name, gl=globals()):
    cmd  ="import "+mod_name+", "+mod_name+"__POA\n"
    cmd +="class "+if_name+"_impl("+mod_name+"__POA."+if_name+",rtService):\n"
    cmd +="  def __init__(self):\n"
    cmd +="    self.class_name='"+if_name+"_impl'\n"
    cmd +="    return\n"
    exec(cmd, gl)

genClass=rtService()
