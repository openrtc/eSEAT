#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Task and TaskGroup for eSEAT (Extened Simple Event Action Transfer)

Copyright (C) 2017
    Isao Hara
    Robot Innovation Rearch Center,
    National Institute of Advanced Industrial Science and Technology (AIST), Japan
    All rights reserved.
  Licensed under the MIT License (MIT)
  http://www.opensource.org/licenses/MIT
'''

############### import libraries
from __future__ import print_function
import sys
import os
import subprocess
from collections import OrderedDict

from . import utils
import re
import traceback

from .core import getGlobals, setGlobals
'''
State:
  - name(string), rules([TaskGroup,]), onentry(TaskGroup), onexit(TaskGroup)

TaskGroup: <-- <rule>
  - keys([string,]), patterns([reg,]), taskseq([Task,])

 Task: <- <message>, <shell>, <script>, <log>, <statetransition>
   +- TaskMessage: <message>
        - sendto, encode, input
   +- TaskShell: <shell>
        - sendto
   +- TaskScript: <sciptt>
        - execfile, sendto
   +- TaskLog: <log>
        - 
   +- TaskStateTransision: <statetransition>
        - func[push, pop]

'''
###########################################
#
#  Class Task for eSEAT
#
class Task():
    def __init__(self, rtc):
        self.seat = rtc
        self._logger = rtc._logger
        self.condition = True
        
    def execute(self,data):
        return True

    def error(self, msg, val):
        if not val: val="None"
        self._logger.error(msg +": "+ val)
        self._logger.error( traceback.format_exc() )
        return

    def checkCondition(self):
        return True
#
#
class TaskMessage(Task):
    def __init__(self, rtc, sndto, data, encode, input_id):
        Task.__init__(self, rtc)
        self.sendto=sndto
        self.data = data
        self.encoding = encode
        self.input_id=input_id
        
        return

    def execute(self, s):
        data = self.data
        try:
            ad = self.seat.adaptors[self.sendto]
            if self.input_id :
                if self.input_id in self.seat.inputvar :
                    data = self.seat.inputvar[self.input_id].get()
                elif self.input_id in self.seat.stext :
                    data = self.seat.getLastLine(self.input_id, 1)
            #
            #  Call 'send' method of Adaptor
            #
            if not self.encoding :
                ad.send(self.sendto, data)
            else :
                ad.send(self.sendto, data, self.encoding)
            return True

        except KeyError:
            self.error("no such adaptor", self.sendto)
            return False
        return True
#
#
class TaskShell(Task):
    def __init__(self, rtc, sendto, data):
        Task.__init__(self, rtc)
        self.sendto = sendto
        self.data = data
        return

    def execute(self, data):
        #
        # execute shell command with subprocess
        res = subprocess.Popen(self.data, shell=True)
        self.popen.append(res)
        #
        #  Call 'send' method of Adaptor
        try:
            ad = self.seat.adaptors[self.sendto]
            ad.send(self.sendto, res)
        except KeyError:
            self.error("no such adaptor", self.sendto)
        return True
#
#
class TaskScript(Task):
    def __init__(self, rtc, sendto, data, fname, imports=None):
        Task.__init__(self, rtc)
        self.sendto = sendto
        self.data = data
        self.fname = fname
        self.imports = imports

        return

    def execute(self, data):
        retval = True
        setGlobals('rtc_result', None)
        setGlobals('rtc_in_data', data)
        setGlobals('web_in_data', data)
        setGlobals('__retval__', retval)
        #
        #   execute script or script file
        if self.imports:
            import_str="import "+self.imports
            exec(import_str, getGlobals())

        if self.fname :
            ffname = utils.findfile(self.fname)
            if ffname :
                utils.exec_script_file(ffname, getGlobals())
        try:
            if self.data :
                exec(self.data, getGlobals())
                retval=getGlobals()['__retval__']
        except:
            self.error("Error in script", self.data)
            return False
        # 
        #  Call 'send' method of Adaptor to send the result...
        rtc_result = getGlobals()['rtc_result'] 
        if rtc_result != None and retval:
            try:
                if self.sendto :
                    ad = self.seat.adaptors[self.sendto]
                    ad.send(self.sendto, rtc_result)
            except KeyError:
                self.error("no such adaptor:" + self.sendto)
        return rtc_result
#
#
class TaskLog(Task):
    def __init__(self, rtc, data):
        Task.__init__(self, rtc)
        self.info = data
        return
    def execute(self, data):
        self._logger.info(self.info)
        return True
#
#
class TaskStatetransition(Task):
    def __init__(self, rtc, func, data):
        Task.__init__(self, rtc)
        self.func = func
        self.data = data
        return

    def execute(self, d):
        try:
            if (self.func == "push"):
                self.seat.statestack.append(self.seat.currentstate)
                self.seat.stateTransfer(self.data)

            elif (self.func == "pop"):
                if self.seat.statestack.__len__() == 0:
                    self._logger.warn("state buffer is empty")
                    return False
                self.seat.stateTransfer(self.seat.statestack.pop())
            else:
                self._logger.info("state transition from "+self.seat.currentstate+" to "+self.data)
                self.seat.stateTransfer(self.data)
            return False
        except:
            self.error("Error in state transision", self.data)
            return False

#############################
#  TaskGroup Class for eSEAT:
#      TaskGroup neary equal State....
#
class TaskGroup():
    def __init__(self):
        self.taskseq=[]
        self.keys=[]
        self.patterns=[]
        self.timeout = -1
        self.condition = True
        self.pre_script = None

    def execute(self, data=None):
        if self.checkCondition():
            for cmd in self.taskseq:
                if cmd.checkCondition() :
                    retval = cmd.execute(data)
                    if not retval: return retval
        return True

    def executeEx(self, data=None):
        retval=True
        if self.checkCondition():
            for cmd in self.taskseq:
                if cmd.checkCondition() :
                    if isinstance(cmd, TaskMessage):  cmd.encoding = None
                    retval = cmd.execute(data)
        return retval

    def setCondition(self, cond_str):
        self.condition=cond_str

    def checkCondition(self):
        if isinstance(self.condition, str): cond = eval(self.condition.strip(), getGlobals())
        else: cond = self.condition
        return cond

    def addTask(self, task):
        self.taskseq.append(task)

    def clearTasks(self):
        self.taskseq=[]

    def addPattern(self, pat):
        self.patterns.append(re.compile(pat))

    def addKey(self, key):
        self.keys.append(key)

    def match(self, msg):
        for x in self.keys:
            if x == msg : return True
        for x in self.patterns:
            if x.match(msg) : return True
        return False
    
    def execute_pre_script(self):
        if self.pre_script :
            ffname = utils.findfile(self.pre_script)
            if ffname :
                utils.exec_script_file(ffname, getGlobals())
                
#####################
#  State
class State():
    def __init__(self, name):
        self.name = name
        self.onentry = None
        self.onexit = None
        self.onexec = None
        self.ontimeout = None
        self.onactivated = None
        self.ondeactivated = None
        self.keys = []
        self.rules = OrderedDict()

    def updateKeys(self):
        self.keys = self.rules.keys()
        return

    def registerRule(self, key, tasks):
        self.rules[key] = tasks
        self.updateKeys()

    def registerRuleArray(self, key, tasks):
        if key in self.rules :
            self.rules[key].append(tasks)
        else:
            self.rules[key] = [tasks]
            self.updateKeys()

    def removeRule(self, key):
        try:
            del self.rules[key]
        except:
            pass
        self.updateKeys()
        return 

    def matchkey(self, port, word):
        for x in self.keys:
            if x[0] == port and x[1] == word:
                return self.rules[x]

        for x in self.keys:
            if x[0] == port and re.match(x[1], word) is not None:
                return self.rules[x]
        return None

    def searchkey(self, port, word):
        for x in self.keys:
            if x[0] == port and x[1] == word:
                return self.rules[x]

        for x in self.keys:
            if x[0] == port and re.search(x[1], word) is not None:
                return self.rules[x]
        return None

    def has_rule(self, port, word):
        return (port, word) in self.rules
