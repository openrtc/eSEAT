#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-

import sys
import string
import time

import RTC
import SimpleService, SimpleService__POA
import OpenRTM_aist

# functor class to print sequence data
class seq_print:
  def __init__(self):
    self._cnt = 0
    return

  def __call__(self, val):
    print self._cnt, ": ", val
    self._cnt += 1
    return


# Class implementing IDL interface MyService(MyService.idl)
class MyServiceSVC_impl(SimpleService__POA.MyService):
  def __init__(self):
    self._echoList = []
    self._valueList = []
    self._value = 0
    return

  def __del__(self):
    pass

  def echo(self, msg):
    OpenRTM_aist.CORBA_SeqUtil.push_back(self._echoList, msg)
    print "MyService::echo() was called."
    for i in range(10):
      print "Message: ", msg
      time.sleep(1)
    print "MyService::echo() was finished."
    return msg

  def get_echo_history(self):
    print "MyService::get_echo_history() was called."
    OpenRTM_aist.CORBA_SeqUtil.for_each(self._echoList, seq_print())
    return self._echoList

  def set_value(self, value):
    OpenRTM_aist.CORBA_SeqUtil.push_back(self._valueList, value)
    self._value = value
    print "MyService::set_value() was called."
    print "Current value: ", self._value
    return

  def get_value(self):
    print "MyService::get_value() was called."
    print "Current value: ", self._value
    return float(self._value)

  def get_value_history(self):
    print "MyService::get_value_history() was called."
    OpenRTM_aist.CORBA_SeqUtil.for_each(self._valueList, seq_print())

    return self._valueList

