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
from __future__ import print_function
import sys
import os

###########################################
#  XML parse
from lxml import etree
#import xml.etree.ElementTree as etree

###########################################
# utils
try:
  import utils
  import core as eSEAT_Core
  import Task
except:
  from . import utils
  from . import core as eSEAT_Core
  from . import Task

if sys.version_info.major > 2:
    def unicode(s):
        return str(s)

###########################################
#
#  Class eSEAT Parser
#
class SEATML_Parser():
    def __init__(self, parent, xsd='seatml.xsd', logger=None):
        self.parent = parent
        self.componentName = "eSEAT"
        self._xmlschema = None
        if logger:
            self._logger = parent._logger
        else:
            self._logger = None

        xsd_file = utils.findfile(xsd)

        if xsd_file:
            self.setXsd(xsd_file)
            print ("XSD file '"+xsd+"' = '"+xsd_file+"'.")
        else:
            #print ("Warining:XSD file '"+xsd+"' not found.")
            pass

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
    #  Create communication adaptor
    #
    def createAdaptor(self, tag):
        try:
            name = str(tag.get('name'))
            type = tag.get('type')
            return self.parent.createAdaptor(self.componentName, tag, eSEAT_Core.getGlobals())
        except:
            self.logError(u"invalid parameters(1): " + type + ": " + name)
            return -1

        return 1

    #
    #   Sub parser <message><command><statetransition><log><shell><script>
    #
    def parseCommands(self, r):
        tasks=Task.TaskGroup()

        for c in r.getchildren():
        #
        # <message>
            if c.tag == 'message': # end message
                sendto     = c.get('sendto')
                if not sendto : sendto = c.get('host')
                task = Task.TaskMessage(self.parent, sendto, c.text, c.get('encode'), c.get('input'))
                tasks.addTask(task)
        #
        # <statetransition>
            elif c.tag == 'statetransition': # get statetransition
                task = Task.TaskStatetransition(self.parent, c.get('func'), c.text)
                tasks.addTask(task)
        #
        # <log>
            elif c.tag == 'log': #  logging
                task = Task.TaskLog(self.parent, c.text)
                tasks.addTask(task)
        #
        # <shell>
            elif c.tag == 'shell': # get shell
                sendto = c.get('sendto')
                if not sendto : sendto = c.get('host')
                task = Task.TaskShell(self.parent, sendto, c.text)
                tasks.addTask(task)
        #
        # <script>
            elif c.tag == 'script': # get script
                sendto  = c.get('sendto')
                if not sendto : sendto = c.get('host')
                task = Task.TaskScript(self.parent, sendto,
                    self.getScripts(c), c.get('execfile'), c.get('import'))
                tasks.addTask(task)
        return tasks

    #
    #   delete spaces at the begining of the lines for python script
    #
    def getScripts(self, tag):
        data = skipSps(tag.text)
        for ctag in tag.getchildren():
            data += skipSps(ctag.text)
        return data

    #
    # execute the python script
    #
    def procScript(self, tag, fname, imports):
        if imports :
            import_str="import "+imports
            exec(import_str, eSEAT_Core.getGlobals())

        txt = self.getScripts(tag)
        if fname :
            ffname = utils.findfile(fname)
            if ffname :
                utils.exec_script_file(ffname, eSEAT_Core.getGlobals())
        if txt :
            #sys.path.append('.')
            exec(txt, eSEAT_Core.getGlobals())

    #
    # get attribute of the tag. If the attribute isnot found, set default value
    #
    def getAttribute(self, e, name, def_val=None):
        val = e.get(name)
        if def_val is None: return val
        if not val : val = def_val
        return val
    #
    #  get text of the tag
    #
    def getText(self, e):
        val = e.text
        if not val: val = ''
        return val

    #
    #  Sub parser for GUI items
    #
    def parseGui(self, name, e):
        if not isinstance(self.parent, eSEAT_Core.eSEAT_Gui) : return
        commands = self.parseCommands(e)

        #
        #  <label>
        if e.tag == 'label':
            self.parent.addLabel(name, self.getAttribute(e, 'text'),
                   self.getAttribute(e, 'color'),
                   self.getAttribute(e, 'bg_color'),
                   self.getAttribute(e, 'colspan', 1), 
                   self.getAttribute(e, 'rowspan', 1),
                   self.getAttribute(e, 'frame', ''),
                   self.getAttribute(e, 'args', '')
                   )
        #
        #  <brk>
        elif e.tag == 'brk':
            self.parent.addBreak(name, self.getAttribute(e, 'frame', ''))
        #
        #  <space>
        elif e.tag == 'space':
            self.parent.addSpace(name, self.getAttribute(e, 'length', 1),
                            self.getAttribute(e, 'frame', ''))
        #
        #  <frame>
        elif e.tag == 'frame':
            key = self.getAttribute(e, 'name')
            self.parent.addFrame(name, key, 
                self.getAttribute(e, 'height'), self.getAttribute(e, 'width'),
                self.getAttribute(e, 'relief', 'flat'), 
                self.getAttribute(e, 'color'), self.getAttribute(e, 'bg_color'),
                self.getAttribute(e, 'colspan', 1),
                self.getAttribute(e, 'rowspan', 1),
                self.getAttribute(e, 'frame', '')
                )

        #
        #  <labelframe>
        elif e.tag == 'labelframe':
            key = self.getAttribute(e, 'label')
            self.parent.addLabelframe(name, key,
                self.getAttribute(e, 'height'), self.getAttribute(e, 'width'),
                self.getAttribute(e, 'labelanchor', 'nw'),
                self.getAttribute(e, 'relief', 'groove'), 
                self.getAttribute(e, 'color'), self.getAttribute(e, 'bg_color'),
                self.getAttribute(e, 'colspan', 1),
                self.getAttribute(e, 'rowspan', 1),
                self.getAttribute(e, 'frame', '')
                )

        #
        #  <button>
        elif e.tag == 'button':
            key = self.getAttribute(e, 'label')
            #self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.states[name].registerRule(('gui', key), commands)
            self.parent.addButton(name, key, self.getAttribute(e, 'color'),
                 self.getAttribute(e, 'bg_color'),
                 self.getAttribute(e, 'width'),
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )

        #
        #  <input>
        elif e.tag == 'input':
            key = self.getAttribute(e, 'id')
            #self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.states[name].registerRule(('gui', key), commands)
            self.parent.addEntry(name, key, self.getAttribute(e, 'width', '20'),
                 self.getText(e),
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <text>
        elif e.tag == 'text':
            key = self.getAttribute(e, 'id')
            #self.parent.registerCommands(name+":gui:"+key, commands)
            self.parent.states[name].registerRule(('gui', key), commands)
            self.parent.addText(name, key, self.getAttribute(e, 'width', '20'),
                 self.getAttribute(e, 'height', '3'),
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1), self.getText(e), 
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <combobox>
        elif e.tag == 'combobox':
            key = self.getAttribute(e, 'id')
            self.parent.states[name].registerRule(('gui', key), commands)
            self.parent.addCombobox(name, key, self.getAttribute(e, 'values'),
                 self.getAttribute(e,'default', ''),
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <checkbutton>
        elif e.tag == 'checkbutton':
            key = self.getAttribute(e, 'name')
            self.parent.states[name].registerRule(('gui', key), commands)
            self.parent.addCheckbutton(name, key,
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <listbox>
        elif e.tag == 'listbox':
            key = self.getAttribute(e, 'name')
            self.parent.states[name].registerRule(('gui', key), commands)
            txtlist = self.getAttribute(e, 'values')
            height = self.getAttribute(e, 'height', len(txtlist.split(',')))
            self.parent.addListbox(name, key, txtlist, height,
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <radiobutton>
        elif e.tag == 'radiobutton':
            key = self.getAttribute(e, 'label')
            self.parent.states[name].registerRule(('gui', key), commands)
            var=self.getAttribute(e, 'variable')
            val=self.getAttribute(e, 'value')
            self.parent.addRadiobutton(name, key, var, val,
                 self.getAttribute(e, 'colspan', 1),
                 self.getAttribute(e, 'rowspan', 1),
                 self.getAttribute(e, 'frame', '')
                 )
        #
        #  <scale>
        elif e.tag == 'scale':
            key = self.getAttribute(e, 'name')
            self.parent.states[name].registerRule(('gui', key), commands)
            frm=self.getAttribute(e, 'from', 0)
            to=self.getAttribute(e, 'to', 10)
            res=self.getAttribute(e, 'resolution', 1)
            ori=self.getAttribute(e, 'orientation', 'horizontal')

            self.parent.addScale(name, key, frm, to, res, ori, 
                self.getAttribute(e, 'colspan', 1),
                self.getAttribute(e, 'rowspan', 1),
                self.getAttribute(e, 'frame', '')
                )
        #
        #
        elif e.tag == etree.Comment:
           pass
        #
        #  Others
        else:
           self.logError("Invalid tag found: " + unicode(e.tag))

    #
    #  load rules from external seatml file
    #
    def loadRuleFile(self, name, f, sname=None):
        f = f.replace("\\", "\\\\")
        self.logInfo("load script file(loadRuleFile): " + f)

        try:
            doc = etree.parse(f)
        except etree.XMLSyntaxError as e:
            self.logError("invalid xml syntax(loadRuleFile): " + unicode(e))
            return 1
        except IOError as e:
            self.logError("unable to open file " + f + " (loadRuleFile): " + unicode(e))
            return 1

        try:
            if self._xmlschema :
                self._xmlschema.assert_(doc)
        except AssertionError as b:
            self.logError("invalid script file: " + f + " (loadRuleFile): " + unicode(b))
            return 1

        for s in doc.findall('state'):
            if not sname or sname == s.get('name'):
                for e in list(s):
                    if e.tag == 'rule':
                        self.parseRule(name, e)
                return

        self.logError("no rule foud: " + f +":"+unicode(sname))

    #
    #   Sub parser for <rule>tag 
    #
    def parseRule(self, name, e):
        #
        # Check attribute 'file'
        if e.get('file'):
            loadfile = os.path.join(self.seatml_base_dir, e.get('file'))
            if loadfile in self.include_rules :
                self.logError("already included: " + e.get('file'))
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
                kond = None
                #
                #  <cond>
                knd = e.find('cond')
                if knd is not None :
                    commands.pre_script = knd.get("execfile")
                    #print (knd.get("execfile"))
                    #print (commands.pre_script)
                    commands.condition = knd.text

                if keys :
                    for k in keys:
                        word = decompString([k.text])

                        for w in word:
                            self.parent.states[name].registerRule((adaptor, w), commands)
                else :
                    self.parent.states[name].registerRuleArray((adaptor, 'ondata'), commands)

            for k in keys:
                source = k.get('source')
                if source is None: source = "default" 
                word = decompString([k.text])

                for w in word:
                    self.parent.states[name].registerRule((source, w), commands)

    #
    #   Sub parser for <exec>tag 
    #
    def parseExec(self, name, e):
        commands = self.parseCommands(e)
        self.parent.states[name].onexec = commands
        self.logInfo("register <onexec> on " + name)
        return commands

    #
    #   Sub parser for <activated>tag 
    #
    def parseActivated(self, e):
        commands = self.parseCommands(e)
        self.parent.states['all'].onactivated = commands
        self.logInfo("register <onactivated> on all")
        return commands

    #
    #   Sub parser for <deactivated>tag 
    #
    def parseDeactivated(self, name, e):
        commands = self.parseCommands(e)
        self.parent.states[name].ondeactivated = commands
        self.logInfo("register <ondeactivaetd> on " + name)
        return commands

    #
    #   Sub parser for <exec>tag 
    #
    def parseTimeout(self, name, e):
        tout = e.get('timeout')
        commands = self.parseCommands(e)
        commands.timeout = float(tout)
        self.parent.states[name].ontimeout = commands
        self.logInfo("register <ontimeout> on " + name)
        return commands

    #######################################################
    #   eSEAT Markup Language File loader
    #
    def load(self, f):
        self.setParentLogger()
        f = f.replace("\\", "\\\\")
        self.seatml_base_dir = os.path.dirname(f)
        
        self.logInfo("load script file: " + f)

        try:
            doc = etree.parse(f)
        except etree.XMLSyntaxError as e:
            self.logError("invalid xml syntax: " + unicode(e))
            return 1
        except IOError as e:
            self.logError("unable to open file " + f + ": " + unicode(e))
            return 1


        try:
            if self._xmlschema :
                self._xmlschema.assert_(doc)
        except AssertionError as b:
            self.logError("invalid script file: " + f + ": " + unicode(b))
            return 1

        self.parent.items = {}

        ####
        # Top level tag
        #
        #  <general>
        g=doc.find('general')
        #for g in doc.findall('general'):
        if g is not None:
            self.parent.create_state('all')
            sys.path.append('.')
            sys.path.append('rtm')

            if g.get('name') :
                self.componentName = g.get('name')
                if self.componentName: self.parent.name=self.componentName
                self.parent.setInstanceName(self.componentName)

            if g.get('anonymous') :
                self.parent.ros_anonymous=g.get('anonymous')

            if g.get('rate') :
                self.parent.rate_hz=g.get('rate')

            for a in g.getchildren():
                #
                #  <adaptor>
                if a.tag == 'adaptor':
                    self.createAdaptor(a)
                #
                #  <script>
                elif  a.tag == 'script':
                    self.procScript(a, a.get('execfile'), a.get('import'))
                #
                #  <onexec>
                elif a.tag == 'onexec':
                    self.parseExec('all', a)
                #
                #  <onactivated>
                elif a.tag == 'onactivated':
                    self.parseActivated(a)
                #
                #  <ondeactivated>
                elif a.tag == 'ondeactivated':
                    self.parseDeactivated('all', a)
                #
                #  <var>
                elif a.tag == 'var':
                    eSEAT_Core.setGlobals(g.get('name'), g.get('value'))
                #
                #  <timoute>
                elif a.tag == 'ontimeout':
                    self.parseTimeout('all', a)

                else:
                    pass
        else:
            print('Error in seatml file') 
            return -1
        # 
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
                    if e.tag == 'onentry': 
                        self.parent.states[name].onentry = commands
                    if e.tag == 'onexit': 
                        self.parent.states[name].onexit = commands
                #
                #  <timoute>
                elif e.tag == 'ontimeout':
                    self.parseTimeout(name, e)
                #
                #  <onexec>
                elif e.tag == 'onexec':
                    self.parseExec(name, e)
                #
                #  <ondeactivated>
                elif e.tag == 'ondeactivated':
                    self.parseDeactivated(name, e)
                #
                #  <rule>
                elif e.tag == 'rule':
                    self.include_rules = [ f.replace("\\\\", "\\")] 
                    self.parseRule(name, e)

                elif e.tag == etree.Comment:
                    pass

                else:
                #
                # GUI tags
                    self.parseGui(name, e)

            #self.parent.appendState(name)

        ############################################
        #  initialize
        #
        if self.parent.countStates() == 0:
            self.logError("no available state")
            return 1

        self.parent.initStartState("start")
        self.logInfo("loaded successfully")

        return 0

#############################################
# Functions
#
#
# Parse Key String: already not needed
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
#  Convert datatype
#
def convertDataType(dtype, data, code='utf-8'):
  if dtype == str:
    if sys.version_info.major == 2:
        return data.encode(code)
    else:
        return data

  elif sys.version_info.major == 2 and dtype == unicode:
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

#
#  Count spaces at the begining of the line
#
def countSp(s):
  c=0
  for x in s:
    if x != " " and x != "\n":
      return c
    c=c+1
  return c

#
#  Remove spaces at the begining of the lines
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

