#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Seatml file parser for eSEAT (Extened Simple Event Action Transfer)

Copyright (C) 2009-2014
    Yosuke Matsusaka and Isao Hara
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST), Japan
    All rights reserved.
  Licensed under the MIT License (MIT)
  http://www.opensource.org/licenses/MIT
'''

############### import libraries
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

#
#
sys.path.append(os.path.abspath('./libs'))

#########
#  XML parse
from lxml import etree

#########
#  GUI etc.
import utils
from Tkinter import * 
from ScrolledText import * 

###############################################################
#
__version__ = "0.3"

#########################################################################
#
#  Class eSEAT Parser
#
class SEATML_Parser():
    def __init__(self, parent, xsd='seatml.xsd', logger=None):
        self.parent = parent
        self.componentName = "eSEAT"
        if logger:
            self._logger = parent._logger
        else:
            self._logger = None

        self.setXsd(xsd)
        self.include_rules = []
        self.seatml_base_dir = ""

    #
    #  set schema-file for seatml
    def setXsd(self, xsd, _dir=None):
        if _dir :
            self._basedir = _dir
        elif os.getenv('SEAT_ROOT') :
            self._basedir = os.getenv('SEAT_ROOT') 
        else :
            self._basedir = os.getcwd()
        xmlschema_doc = etree.parse(os.path.join(self._basedir, xsd))
        self._xmlschema = etree.XMLSchema(xmlschema_doc)

    #
    #   Logger
    def setParentLogger(self):
        self._logger = self.parent._logger

    def logInfo(self, msg):
        if self._logger :
            self._logger.info(msg)

    def logError(self, msg):
        if self._logger :
            self._logger.error(msg)

    #
    #    Create communication adaptor
    #
    def createAdaptor(self, tag):
        try:
            name = str(tag.get('name'))
            type = tag.get('type')
            self.logInfo(u"create adaptor: " + type + ": " + name)

            if type == 'rtcout' and 'createDataPort' in dir(self.parent) :
                self.parent.createDataPort(name, tag.get('datatype') ,'out')
            elif type == 'rtcin' and 'createDataPort' in dir(self.parent) :
                self.parent.createDataPort(name, tag.get('datatype') ,'in')
            elif type == 'web' :
                self.parent.createWebAdaptor(name, int(tag.get('port')), self.componentName, tag.get('host'))
            else:
                 self.parent.createSocketPort(name, tag.get('host'), int(tag.get('port')))
        except:
            self.logError(u"invalid parameters: " + type + ": " + name)
            return -1

        return 1

    #
    #   Sub parser
    #
    def parseCommands(self, r):
        commands = []
        #
        # <message>
        for c in r.findall('message'): # end message
            name     = c.get('sendto')
            if not name : name = c.get('host')
            encode   = c.get('encode')
            input_id = c.get('input')
            data     = c.text
            commands.append(['c', name, data, encode, input_id])
        #
        # <command>
        for c in r.findall('command'): # get commands
            name     = c.get('sendto')
            if not name : name = c.get('host')
            encode   = c.get('encode')
            input_id = c.get('input')
            data     = c.text
            commands.append(['c', name, data, encode, input_id])
        #
        # <statetransition>
        for c in r.findall('statetransition'): # get statetransition
            func = c.get('func')
            data = c.text
            commands.append(['t', func, data])
        #
        # <log>
        for c in r.findall('log'): #  logging
            data = c.text
            commands.append(['l', data])
        #
        # <shell>
        for c in r.findall('shell'): # get shell
            sendto = c.get('sendto')
            if not sendto : sendto = c.get('host')
            data = c.text
            commands.append(['x', sendto, data])
        #
        # <script>
        for c in r.findall('script'): # get script
            sendto  = c.get('sendto')
            if not sendto : sendto = c.get('host')
            fname = c.get('execfile')
            data = self.getScripts(c)
            commands.append(['s', sendto, data, fname])
        return commands

    def getScripts(self, tag):
        data = skipSps(tag.text)
        for ctag in tag.getchildren():
            data += skipSps(ctag.text)
        return data

    def procScript(self, tag, fname):
        txt = self.getScripts(tag)

        if fname : execfile(fname, globals())
        if txt : exec(txt, globals())

    def getAttribute(self, e, name, def_val=None):
        val = e.get(name)
        if def_val is None: return val
        if not val : val = def_val
        return val

    def getText(self, e):
        val = e.text
        if not val: val = ''
        return val

    def parseGui(self, name, e):
        if not isinstance(self.parent, eSEAT_Gui) : return
        commands = self.parseCommands(e)

        ################ GUI ###############
        #
        #  <label>
        if e.tag == 'label':
            self.parent.addLabel(name, self.getAttribute(e, 'text'), self.getAttribute(e, 'color'),
                    self.getAttribute(e, 'bg_color'), self.getAttribute(e, 'colspan', 1))
        #
        #  <brk>
        elif e.tag == 'brk':
            self.parent.addBreak(name)
        #
        #  <space>
        elif e.tag == 'space':
            self.parent.addSpace(name, self.getAttribute(e, 'length', 1))
        #
        #  <button>
        elif e.tag == 'button':
            key = self.getAttribute(e, 'label')
            self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.addButton(name, key, self.getAttribute(e, 'color'),
                 self.getAttribute(e, 'bg_color'), self.getAttribute(e, 'colspan', 1))

        #
        #  <input>
        elif e.tag == 'input':
            key = self.getAttribute(e, 'id')
            self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.addEntry(name, key, self.getAttribute(e, 'width', '20'),
                 self.getAttribute(e, 'colspan', 1), self.getText(e))
        #
        #  <text>
        elif e.tag == 'text':
            key = self.getAttribute(e, 'id')
            self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.addText(name, key, self.getAttribute(e, 'width', '20'),
                 self.getAttribute(e, 'height', '3'), self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1), self.getText(e))
        else:
           self.logError(u"Invalid tag found: " + unicode(e.tag))

    def loadRuleFile(self, name, f, sname=None):
        f = f.replace("\\", "\\\\")
        self.logInfo(u"load script file(loadRuleFile): " + f)

        try:
            doc = etree.parse(f)
        except etree.XMLSyntaxError, e:
            self.logError(u"invalid xml syntax(loadRuleFile): " + unicode(e))
            return 1
        except IOError, e:
            self.logError(u"unable to open file " + f + " (loadRuleFile): " + unicode(e))
            return 1

        try:
            self._xmlschema.assert_(doc)
        except AssertionError, b:
            self.logError(u"invalid script file: " + f + " (loadRuleFile): " + unicode(b))
            return 1

        for s in doc.findall('state'):
            if not sname or sname == s.get('name'):
                for e in list(s):
                    if e.tag == 'rule':
                        self.parseRule(name, e)
                return

        self.logError(u"no rule foud: " + f +":"+sname)

    #
    #   Parse <rule>tag 
    #
    def parseRule(self, name, e):
        if e.get('file'):
            loadfile = os.path.join(self.seatml_base_dir, e.get('file'))
            if loadfile in self.include_rules :
                self.logError(u"already included: " + e.get('file'))
                return
            self.include_rules.append(loadfile)
            try:
              fname, sname = e.get('file').split(':')
            except:
               fname = e.get('file')
               sname = None

            self.loadRuleFile(name, os.path.join(self.seatml_base_dir, fname), sname)
        else:
            commands = self.parseCommands(e)
            adaptor = e.get('source')
            #
            #  <key>
            keys = e.findall('key')
            if adaptor :
                kond = [None, "True"]
                #
                #  <cond>
                kn = e.find('cond')
                if kn is not None : kond = [kn.get("execfile"), kn.text]

                if keys :
                    for k in keys:
                        word = decompString([k.text])
                        #
                        #
                        for w in word:
                            self.parent.registerCommands(name+":"+adaptor+":"+w, commands)
                else :
                   #
                   #
                    self.parent.registerCommandArray(name+":"+adaptor+":ondata", [kond, commands])

            for k in keys:
                source = k.get('source')
                if source is None: source = "default" 
                word = decompString([k.text])
                #
                #
                for w in word:
                    self.parent.registerCommands(name+":"+source+":"+w, commands)

    #
    #   eSEAT Markup Language File loader
    #
    def load(self, f):
        self.setParentLogger()
        f = f.replace("\\", "\\\\")
        self.seatml_base_dir = os.path.dirname(f)
        
        self.logInfo(u"load script file: " + f)

        try:
            doc = etree.parse(f)
        except etree.XMLSyntaxError, e:
            self.logError(u"invalid xml syntax: " + unicode(e))
            return 1
        except IOError, e:
            self.logError(u"unable to open file " + f + ": " + unicode(e))
            return 1

        try:
            self._xmlschema.assert_(doc)
        except AssertionError, b:
            self.logError(u"invalid script file: " + f + ": " + unicode(b))
            return 1

        self.parent.items = {}

        ####
        # Top level tag
        #
        #  <general>
        for g in doc.findall('general'):
            if g.get('name') : self.componentName = g.get('name')

            for a in g.getchildren():
                #
                #  <adaptor><agent>
                if a.tag == 'adaptor' or a.tag == 'agent':
                    self.createAdaptor(a)
                #
                #  <script>
                elif a.tag == 'script':
                    self.procScript(a, a.get('execfile'))
        # 
        #  <state>
        for s in doc.findall('state'):
            name = s.get('name')
            self.parent.create_state(name)

            for e in list(s):
                #
                #  <onentry><onexit>
                if e.tag == 'onentry' or e.tag == 'onexit':
                    commands = self.parseCommands(e)
                    self.parent.registerCommands(name+":::"+e.tag , commands)
                #
                #  <rule>
                elif e.tag == 'rule':
                    self.include_rules = [ f.replace("\\\\", "\\")] 
                    self.parseRule(name, e)
                else:
                #
                # GUI tags
                    self.parseGui(name, e)

            self.parent.appendState(name)

        ############################################
        #  initialize
        #
        if self.parent.countStates() == 0:
            self.logError("no available state")
            return 1

        self.parent.initStartState("start")

        self.logInfo("loaded successfully")

        return 0

#
# Functions
#
#
# Parse Key String
# 
#
def decompString(strs):
    ret = []
    nstrs = strs
    while nstrs.__len__() > 0:
        nstrs2 = []
        for str in nstrs:
            if str.count('(') > 0 or str.count('[') > 0:
                nstrs2.extend(decompStringSub(str))
            else:
                ret.extend([str])
        nstrs = nstrs2
    return ret

def decompStringSub(str):
    ret = []
    bc = str.count('(')
    kc = str.count('[')
    if bc > 0:
        i = str.index('(')
        prestr = str[:i]
        substrs = []
        substr = ''
        level = 0
        i += 1
        while i < str.__len__():
            if str[i] == '(':
                level += 1
                substr += str[i]
            elif str[i] == ')':
                if level == 0:
                    substrs.extend([substr])
                    break
                else:
                    substr += str[i]
                level -= 1
            elif str[i] == '|':
                if level == 0:
                    substrs.extend([substr])
                    substr = ''
                else:
                    substr += str[i]
            else:
                substr += str[i]
            i += 1
        poststr = str[i+1:]
        for s in substrs:
            ret.extend([prestr+s+poststr])
    elif kc > 0:
        i = str.index('[')
        prestr = str[:i]
        substr = ''
        level = 0
        i += 1
        while i < str.__len__():
            if str[i] == '[':
                level += 1
            elif str[i] == ']':
                if level == 0:
                    break
                level -= 1
            substr += str[i]
            i += 1
        poststr = str[i+1:]
        ret.extend([prestr+poststr])
        ret.extend([prestr+substr+poststr])
    else:
        ret.extend([str])
    return ret

#
#
def convertDataType(dtype, data, code='utf-8'):
  if dtype == str:
     return data.encode(code)

  elif dtype == unicode:
     return unicode(data)

  elif dtype == int or dtype == float :
     return dtype(data)
  else:
     if type(data) == str :
       return eval(data)
     return data

#
# Component Name
def formatInstanceName(name):
   fullname=name.split('/')
   rtcname = fullname[len(fullname) -1 ]
   return rtcname.split('.')[0]

def countSp(s):
  c=0
  for x in s:
    if x != " " and x != "\n":
      return c
    c=c+1
  return c

#
#
#
def skipSps(txt):
  try:
    lines = txt.split("\n")
    c=0
    for x in lines :
      if x : break
      c=c+1
    skip = countSp(lines[c])
    res = ""
    for x in lines :
      if len( x ) >= skip : 
        res += x[skip:]+"\n"
  except:
    return txt
  return res

