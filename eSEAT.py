#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''eSEAT (Extened Simple Event Action Transfer)

Copyright (C) 2009-2014
    Yosuke Matsusaka and Isao Hara
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the MIT License (MIT)
http://www.opensource.org/licenses/MIT
'''

import sys
import os
import getopt
import codecs
import locale
import time
import signal
import re
import traceback
import socket
import optparse
import threading
import subprocess
import OpenRTM_aist

import omniORB
from RTC  import *
from lxml import etree
from bs4  import BeautifulSoup

import utils
from Tkinter import * 
from ScrolledText import * 

__version__ = "0.2"

#
# Socket Adaptor: Communication Port for a raw socket connection
#
class SocketAdaptor(threading.Thread):
    def __init__(self, owner, name, host, port):
        threading.Thread.__init__(self)
        self.owner = owner
        self.name = name
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.mainloop = True
        self.start()

    #
    #  Background job ( message reciever )
    #
    def run(self):
        while self.mainloop:
            if self.connected == False:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    self.socket.settimeout(1)
                    self.connected = True
                except socket.error:
                    print "reconnect error"
                    time.sleep(1)
                except:
                    print traceback.format_exc()
            if self.connected == True:
                try:
                    data = self.socket.recv(1024)
                    if len(data) != 0:
                        self.owner.processResult(self.name, data)
                except socket.timeout:
                    pass
                except socket.error:
                    print traceback.format_exc()
                    self.socket.close()
                    self.connected = False
                except:
                    print traceback.format_exc()

    #
    #  Stop background job
    #
    def terminate(self):
        self.mainloop = False
        if self.connected == True:
            self.socket.close()
            self.connected = False
    #
    #  Send message
    #
    def send(self, name, msg):
        if self.connected == False:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.connected = True
                print "connect socket"
            except socket.error:
                print "cannot connect"

        if self.connected == True:
            try:
                self.socket.sendall(msg+"\n")
            except socket.error:
                print traceback.format_exc()
                self.socket.close()
                self.connected = False


#
#
#  Sprcification of eSEAT
#
eseat_spec = ["implementation_id", "eSEAT",
             "type_name",         "eSEAT",
             "description",       __doc__.encode('UTF-8'),
             "version",           __version__,
             "vendor",            "AIST",
             "category",          "OpenHRI",
             "activity_type",     "DataFlowComponent",
             "max_instance",      "1",
             "language",          "Python",
             "lang_type",         "script",
             "conf.default.scriptfile", "None",
             "conf.default.scorelimit", "0.0",
#             "conf.__widget__.scorelimit", "slider",
             "exec_cxt.periodic.rate", "1",
             ""]

#
# DataListener 
#   This class connected with DataInPort
#
class eSEATDataListener(OpenRTM_aist.ConnectorDataListenerT):
    def __init__(self, name, type, obj):
        self._name = name
        self._type = type
        self._obj = obj
    
    def __call__(self, info, cdrdata):
#        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self,
#		info, cdrdata, self._type(Time(0,0),None))
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self,
			info, cdrdata, instantiateDataType(self._type))
        self._obj.onData(self._name, data)

#
#  Class eSEAT Parser
#
class SEATML_Parser():
    def __init__(self, parent, xsd='seatml.xsd', logger=None):
        self.parent = parent
        if logger:	
            self._logger = parent._logger
        else:
            self._logger = None
		    
	self.setXsd(xsd)

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
            self._logger.RTC_INFO(msg)

    def logError(self, msg):
        if self._logger :
            self._logger.RTC_ERROR(msg)

    #
    #    Create communication adaptor
    #
    def createAdaptor(self, tag):
        try:
            name = str(tag.get('name'))
            type = tag.get('type')
            self.logInfo(u"create adaptor: " + type + ": " + name)

            if   type == 'rtcout':
                self.parent.createDataPort(name, tag.get('datatype') ,'out')
            elif type == 'rtcin' :
                self.parent.createDataPort(name, tag.get('datatype') ,'in')
            else:
                 self.parent.createSocketPort(name,
                                   tag.get('host'), int(tag.get('port')))

        except:
            self.logError(u"invalid parameters: " + type + ": " + name)
            return -1

        return 1

    #
    #   Sub parser
    #
    def parseCommands(self, r):
        commands = []
        for c in r.findall('message'): # get commands
            name = c.get('sendto')
            encode = c.get('encode')
            input_id = c.get('input')
            data = c.text
            commands.append(['c', name, data, encode, input_id])

        for c in r.findall('command'): # get commands
            name = c.get('host')
            encode = c.get('encode')
            input_id = c.get('input')
            data = c.text
            commands.append(['c', name, data, encode, input_id])

        for c in r.findall('statetransition'): # get statetransition
            func = c.get('func')
            data = c.text
            commands.append(['t', func, data])

        for c in r.findall('log'): # get statetransition
            data = c.text
            commands.append(['l', data])

        for c in r.findall('shell'): # get shell
            func = c.get('sendto')
            data = c.text
	    if not func :
              func = c.get('host')
            commands.append(['x', func, data])

        for c in r.findall('script'): # get script
            func = c.get('sendto')
	    fname = c.get('execfile')
	    if not func :
              func = c.get('host')
            data = c.text
            for cx in c.getchildren():
              data += cx.text
            commands.append(['s', func, data, fname])

        return commands

    #
    #   eSEAT Markup Language File loader
    #
    def load(self, f):
        self.setParentLogger()
        f = f.replace("\\", "\\\\")
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

        for g in doc.findall('general'):
            for a in g.getchildren():
                if a.tag == 'adaptor':
                    self.createAdaptor(a)
                elif a.tag == 'agent':
                    self.createAdaptor(a)
                elif a.tag == 'script':
                    filename = a.get('execfile')
                    txt = a.text
                    for cx in a.getchildren():
                        txt += cx.text
		    if filename : execfile(filename, globals())
		    if txt : exec(txt, globals())
	     
        for s in doc.findall('state'):
            name = s.get('name')
            self.parent.create_state(name)

            for e in list(s):
              if e.tag == 'onentry':
                commands = self.parseCommands(e)
		self.parent.registerCommands(name+":::entry" , commands)

              elif e.tag == 'onexit':
                commands = self.parseCommands(e)
		self.parent.registerCommands(name+":::exit" , commands)

              elif e.tag == 'rule':
                commands = self.parseCommands(e)
                adaptor = e.get('source')
                if adaptor :
                    kond = [None, "True"]
                    kn = e.find('cond')
                    if kn is not None : kond = [kn.get("execfile"), kn.text]

                    tag = name+":"+adaptor+":ondata"
                    self.parent.registerCommandArray(tag, [kond, commands])

                for k in e.findall('key'):
                    source = k.get('source')
                    word = decompString([k.text])
		    if source is None: source = "default" 
                    for w in word:
                        tag = name+":"+source+":"+w
                        self.parent.registerCommands(tag, commands)

              elif e.tag == 'button':
                bg = e.get('bg_color')
                fg = e.get('color')
                txt = e.get('label')

                cspan = e.get('colspan')
		if not cspan : cspan = 1

                commands = self.parseCommands(e)
                self.parent.registerCommands(name+":gui:"+txt, commands)
                self.parent.addButton(name, txt, fg, bg, cspan)

              elif e.tag == 'input':
                txt = e.get('id')

                w = e.get('width')
		if not w: w = '20'

                val = e.text
		if not val: val = ''

                cspan = e.get('colspan')
		if not cspan : cspan = 1

                commands = self.parseCommands(e)
                self.parent.registerCommands(name+":gui:"+txt, commands)
                self.parent.addEntry(name, txt, w, cspan, val)

              elif e.tag == 'text':
                txt = e.get('id')

                w = e.get('width')
		if not w: w = '20'

                h = e.get('height')
		if not h: h = '3'

                cspan = e.get('colspan')
		if not cspan : cspan = 1

                rspan = e.get('rowspan')
		if not rspan : rspan = 1

                val = e.text
		if not val: val = ''

                commands = self.parseCommands(e)
                self.parent.registerCommands(name+":gui:"+txt, commands)
                self.parent.addText(name, txt, w, h, cspan, rspan, val)

              elif e.tag == 'label':
                txt = e.get('text')
                bg = e.get('bg_color')
                fg = e.get('color')

                cspan = e.get('colspan')
		if not cspan : cspan = 1

                self.parent.addLabel(name, txt, fg, bg, cspan)

              elif e.tag == 'brk':
                self.parent.addBreak(name)

              elif e.tag == 'space':
                txt = e.get('length')
                if not txt : txt = '1'
                self.parent.addSpace(name, txt)

            self.parent.appendState(name)

        if self.parent.countStates() == 0:
            self.logError("no available state")
            return 1

        self.parent.initStartState("start")

        self.logInfo("loaded successfully")

        return 0

#
#  Class eSEAT
#
class eSEAT(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        if hasattr(sys, "frozen"):
            self._basedir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        else:
            self._basedir = os.path.dirname(__file__)

        self.parser = SEATML_Parser(self)
        self.manager = None
        self.states = []
	self.activated=False
        self.currentstate = "start"
	self.stext = {}
        self.keys = {}
        self.regkeys = {}
        self.adaptors = {}
        self.adaptortype = {}
        self.statestack = []
        self._data = {}
        self._port = {}
        self._scriptfile = ["None"]
        self._scorelimit = [0.0]
        self.init_state = None
        self.gui_items = {}
        self.frames = {}
        self.max_columns = 20
        self.items = {}
	self.inputvar = {}
	self.stext = {}
        self.buttons = {}
        self.labels = {}
        self.popen = []
        self.root = None

    ##########################################################
    #  E v e n t   H a n d l e r
    #  onActivated
    #
    def onInitialize(self):
        OpenRTM_aist.DataFlowComponentBase.onInitialize(self)
        self._logger = OpenRTM_aist.Manager.instance().getLogbuf(self._properties.getProperty("instance_name"))
        self._logger.RTC_INFO("eSEAT (Extended Simple Event Action Transfer) version " + __version__)
        self._logger.RTC_INFO("Copyright (C) 2009-2014 Yosuke Matsusaka and Isao Hara")
        self.bindParameter("scriptfile", self._scriptfile, "None")
        self.bindParameter("scorelimit", self._scorelimit, "0.0")

        return RTC_OK

    #
    # for RTC
    #  onActivated
    #
    def onActivated(self, ec_id):
        self.activated = True
        return RTC_OK


    #
    # for RTC
    #  onDeactivated
    #
    def onDeactivated(self, ec_id):
        self.activated = False
        return RTC_OK

    #
    # for RTC
    #  onFinalize
    #
    def onFinalize(self):
        OpenRTM_aist.DataFlowComponentBase.onFinalize(self)
        try:
            for a in self.adaptors.itervalues():
                if isinstance(a, SocketAdaptor):
                    a.terminate()
                    a.join()
        except:
            self._logger.RTC_ERROR(traceback.format_exc())

	if self.root : self.root.quit()
        return RTC_OK

    #
    # for RTC
    #  onShutdown
    #
    def onShutdown(self, ec_id):
        return RTC_OK
    #
    # for RTC
    #  onExecute
    #
    def onExecute(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onExecute(self, ec_id)
        return RTC_OK

    #
    # for RTC
    #  onData: this method called in comming data
    #
    def onData(self, name, data):
        if self.activated :
            try:
                if isinstance(data, TimedString):
                    data.data = data.data.decode('utf-8')
		    if not self.processResult(name, data.data) :
                        self.processOnDataIn(name, data)
                elif isinstance(data, TimedWString):
                    data.data = data.data
		    if not self.processResult(name, data.data) :
                        self.processOnDataIn(name, data)
                else:
                    self.processOnDataIn(name, data)
            except:
                self._logger.RTC_ERROR(traceback.format_exc())
        else:
            pass

    ##########################################################
    #
    # Create InPort
    #
    def createInPort(self, name, type=TimedString):
        self._logger.RTC_INFO("create inport: " + name)
        #self._data[name] = type(Time(0,0), None)
        self._data[name] = instantiateDataType(type)
        self._port[name] = OpenRTM_aist.InPort(name, self._data[name])
        self._port[name].addConnectorDataListener(
		   	       OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                               eSEATDataListener(name, type, self))
        self.registerInPort(name, self._port[name])

    #
    # Create OutPort
    #
    def createOutPort(self, name, type=TimedString):
        self._logger.RTC_INFO("create outport: " + name)
        #self._data[name] = type(Time(0,0), None)
        self._data[name] = instantiateDataType(type)
        self._port[name] = OpenRTM_aist.OutPort(name, self._data[name],
			           OpenRTM_aist.RingBuffer(8))
        self.registerOutPort(name, self._port[name])

    #
    # Create and Register DataPort
    #
    def createDataPort(self, name, dtype, inout):
        if inout == 'out':
            self.adaptortype[name] = self.getDataType(dtype)
            self.createOutPort(name, self.adaptortype[name][0])
            self.adaptors[name] = self

        elif inout == 'in':
            self.adaptortype[name] = self.getDataType(dtype)
            self.createInPort(name, self.adaptortype[name][0])
            self.adaptors[name] = self
        else:
            pass

    #
    # Create raw socket
    #
    def createSocketPort(self, name, host, port):
        self.adaptors[name] = SocketAdaptor(self, name, host, port)

    #
    # Create Port
    #
    def createAdaptor(self, tag):
        try:
            name = str(tag.get('name'))
            type = tag.get('type')
            self._logger.RTC_INFO(u"create adaptor: " + type + ": " + name)

            if type == 'rtcout':
                self.adaptortype[name] = self.getDataType(tag.get('datatype'))
                self.createOutPort(name, self.adaptortype[name][0])
                self.adaptors[name] = self

            elif type == 'rtcin':
                self.adaptortype[name] = self.getDataType(tag.get('datatype'))
                self.createInPort(name, self.adaptortype[name][0])
                self.adaptors[name] = self

            else:
                host = tag.get('host')
                port = int(tag.get('port'))
                self.adaptors[name] = SocketAdaptor(self, name, host, port)

        except:
            self._logger.RTC_ERROR(u"invalid parameters: " + type + ": " + name)


    #
    # Disconnect all connections
    #
    def disconnectAll(self):
      for p in self._port.keys():
	  if isinstance(self._port[p], OpenRTM_aist.PortBase) :
              self._port[p].disconnect_all()

    #
    #   Send Data 
    #
    def send(self, name, data, code='utf-8'):
        if isinstance(data, str) :
            self._logger.RTC_INFO("sending message %s (to %s)" % (data, name))
        else:
            self._logger.RTC_INFO("sending message to %s" % (name,))

#        print self.adaptortype[name]
        dtype = self.adaptortype[name][1]

        if self.adaptortype[name][2]:
            ndata = []
	    if type(data) == str :
              for d in data.split(","):
#                ndata.append(dtype(d))
                ndata.append( converDataType(dtype, d, code) )
              self._data[name].data = ndata
	    else:
              self._data[name] = data

        elif dtype == str:
            self._data[name].data = data.encode(code)

        elif dtype == unicode:
            #self._data[name].data = unicode(data.encode(code))
            self._logger.RTC_INFO("sending message to %s, %s" % (data,code))
            self._data[name].data = unicode(data)

        elif dtype == int or dtype == float :
            self._data[name].data = dtype(data)

        else:
            try:
                ndata = apply(dtype, eval(data))
                self._data[name] = ndata
            except:
                self._logger.RTC_ERROR( "ERROR in send: %s %s" % (name , data))

        try:
            self._port[name].write(self._data[name])
        except:
            self._logger.RTC_ERROR("Fail to sending message to %s" % (name,))

    #
    #  Main event process 
    #
    def processResult(self, name, s):
        try:
            s = unicode(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = unicode(s)

        self._logger.RTC_INFO("got input %s (%s)" % (s, name))
        cmds = None

        if s.count('<?xml') > 0:
            self.processJuliusResult(name, s)
        else:
            cmds = self.lookupWithDefault(self.currentstate, name, s)

        if not cmds:
            self._logger.RTC_INFO("no command found")
            return False

        for c in cmds:
            self.activateCommand(c, s)
        return True

    def processJuliusResult(self, host, s):
        doc = BeautifulSoup(s)
        for s in doc.findAll('data'):
            rank = int(s['rank'])
            score = float(s['score'])
            text = s['text']
            self._logger.RTC_INFO("#%i: %s (%f)" % (rank, text, score))
            if score < self._scorelimit[0]:
                self._logger.RTC_INFO("[rejected] score under limit")
                continue
            cmds = self.lookupWithDefault(self.currentstate, host, text)
            if not cmds:
                cmds = self.lookupWithDefault(self.currentstate, host, text)
            if cmds:
                break
            else:
                self._logger.RTC_INFO("[rejected] no matching phrases")

    def processOnDataIn(self, name, data):
        self._logger.RTC_INFO("got input from %s" %  (name,))
        cmds = self.lookupWithDefault(self.currentstate, name, "ondata")

        if not cmds:
            self._logger.RTC_INFO("no command found")
            return False

        for c in cmds:
	    kond = c[0]
	    globals()['rtc_in_data'] = data
	    if kond[0] :
                execfile(kond[0], globals())

            if eval(kond[1], globals()):
                for cmd in c[1]:
                    self.activateCommandEx(cmd, data)
        return True

    #
    #  Lookup Registered Commands
    #
    def lookupWithDefault(self, state, name, s):
        s=s.split(",")[0]
        self._logger.RTC_INFO('looking up...%s: %s' % (name,s,))
        cmds = self.lookupCommand(state, name, s)
        if not cmds:
            cmds = self.lookupCommand(state, 'default', s)
        if not cmds:
            cmds = self.lookupCommand('all', name, s)
        if not cmds:
            cmds = self.lookupCommand('all', 'default', s)
        return cmds

    def lookupCommand(self, state, name, s):
        cmds = []
        regkeys = []
        try:
            cmds = self.keys[state+":"+name+":"+s]
        except KeyError:
            try:
                regkeys = self.regkeys[state+":"+name]
            except KeyError:
                return None

            for r in regkeys:
                if r[0].match(s):
                    cmds = r[1]
                    break
            return None
        return cmds
        
    #
    # State Transition
    #
    def stateTransfer(self, newstate):
        try:
            for c in self.keys[self.currentstate+":::exit"]:
                self.activateCommand(c)
        except KeyError:
            pass
  
        try:
            self.prev_state=self.currentstate
            self.next_state=newstate
            self.root.event_generate("<<state_transfer>>", when="tail")
        except:
            pass

        self.currentstate = newstate

        try:
            for c in self.keys[self.currentstate+":::entry"]:
                self.activateCommand(c)
        except KeyError:
            pass

    #
    #  Execute <message>
    #
    def applyMessage(self, c):
        name = c[1]
        data = c[2]
        encoding = c[3]
        input_id = c[4]

        try:
            ad = self.adaptors[name]
            if input_id :
                data = self.inputvar[input_id].get()

            if not encoding :
                ad.send(name, data)
            else :
                ad.send(name, data, encoding)
                #ad.send(host, data.encode(c[3]))

        except KeyError:
            if name :
                self._logger.RTC_ERROR("no such adaptor:" + name)
            else :
                self._logger.RTC_ERROR("no such adaptor: None")

    #
    #  Execute <statetransition>
    #
    def applyTransition(self, c):
        func,data = c[1:]
        if (func == "push"):
            self.statestack.append(self.currentstate)
            self.stateTransfer(data)

        elif (func == "pop"):
            if self.statestack.__len__() == 0:
                self._logger.RTC_WARN("state buffer is empty")
                return
            self.stateTransfer(self.statestack.pop())

        else:
            self._logger.RTC_INFO("state transition from "+self.currentstate+" to "+data)

#            try:
#               self.hideFrame(self.currentstate)
#           except:
#               pass
            self.stateTransfer(data)

#           try:
#               self.showFrame(data)
#           except:
#               pass

    #
    #  Execute <log>
    #
    def applyLog(self, c):
        data = c[1]
        self._logger.RTC_INFO(data)

    #
    #  Execute <shell>
    #
    def applyShell(self, c):
        name ,data = c[1:]
        #res = os.system(data)
        res = subprocess.Popen(data, shell=True)
        self.popen.append(res)
        try:
            ad = self.adaptors[name]
            ad.send(name, res)
        except KeyError:
            if name :
               self._logger.RTC_ERROR("no such adaptor:" + name)
            else:
               self._logger.RTC_ERROR("no such adaptor: None")

    #
    #  Execute <script>
    #
    def applyScript(self, c, indata=None):
	name,data,fname = c[1:]

        globals()['rtc_result'] = None
        globals()['rtc_in_data'] = indata

	if fname : execfile(fname,globals())
	if data :
            exec(data,globals())
	rtc_result = globals()['rtc_result'] 

        if rtc_result == None :
#            self._logger.RTC_INFO("no result")
            pass
        else:
            try:
                ad = self.adaptors[name]
                ad.send(name, rtc_result)
            except KeyError:
                if name :
                   self._logger.RTC_ERROR("no such adaptor:" + name)
                else:
                   self._logger.RTC_ERROR("no such adaptor: None")

    #
    #  Activate Lookuped Commands
    #
    def activateCommand(self, c, data=None):
        if c[0] == 'c': self.applyMessage(c)
        elif c[0] == 'l': self.applyLog(c)
        elif c[0] == 'x': self.applyShell(c)
        elif c[0] == 's': self.applyScript(c, data)
        elif c[0] == 't': self.applyTransition(c)

    def activateCommandEx(self, c, data):
        if c[0] == 'c': c[3] = None
        self.activateCommand(c, data)

    #
    # Get state infomation
    #
    def getStates(self):
        return self.states

    def setStartState(self, name):
        self.startstate = name
        return

    def countStates(self):
        return len(self.states)

    def inStates(self, name):
        return ( self.states.count(name) > 0 )

    def appendState(self, name):
        self.states.extend([name])
        return

    def initStartState(self, name):
        self.startstate = None
	if self.states.count(name) > 0 :
            self.startstate = name
        else:
            self.startstate = self.states[0]
        self.stateTransfer(self.startstate)
        self._logger.RTC_INFO("current state " + self.currentstate)

    #
    #  Get DataType
    #
    def getDataType(self, s):
        if len(s) == 0:
            return (TimedString, 0)
        seq = False

        if s[-3:] == "Seq":
            seq = True
        dtype = str
        if s.count("WString"):
            dtype = unicode
        elif s.count("String"):
            dtype = str
        elif s.count("Float"):
            dtype = float
        elif s.count("Double"):
            dtype = float
        elif s.count("Short"):
            dtype = int
        elif s.count("Long"):
            dtype = int
        elif s.count("Octet"):
            dtype = int
        elif s.count("Char"):
            dtype = str
        elif s.count("Boolean"):
            dtype = int
        else:
            dtype = eval("%s" % s)

        return (eval("%s" % s), dtype, seq)

    #
    #  main SEATML loader
    #
    def loadSEATML(self, f):
        self._logger.RTC_INFO("Start loadSEATML:"+f)
        res = self.parser.load(f)
	if res == 1 : 
            self._logger.RTC_ERROR("===> SEATML Parser error")
	    if self.manager : self.manager.shutdown()
            sys.exit(1)


    def hasGUI(self):
        for x in self.items.keys():
            if len(self.items[x]) : return True
        return False

    #
    #  register commands into self.keys
    #
    def registerCommands(self, key, cmds):
        self._logger.RTC_INFO("register key="+key)
        self.keys[key] = cmds

    def appendCommands(self, key, cmds):
        self._logger.RTC_INFO(" append key="+key)
        self.keys[key].append(cmds) 

    def registerCommandArray(self, tag, cmds):
        if self.keys.keys().count(tag) == 0 :
            self.registerCommands(tag, [cmds])
        else :
            self.appendCommands(tag, cmds)

    #
    #  Callback function
    #
    def mkcallback(self, name):
        def callback(event=None):
           self.processResult("gui", name)
        return callback

    def mkinputcallback(self, name):
        def callback(event=None):
           self.processResult("gui", name)
        return callback

    #
    #
    #
    def create_state(self, name):
        self.items[name] = []
        if self.init_state == None:
            self.init_state = name

        return 
    #
    #  Create GUI items
    #
    def newFrame(self, name):
        self.frames[name] = Frame(self.root)
        return self.frames[name]

    def setTitle(self, name):
	if self.root : self.root.title(name)

    #  Called by SEATML Parser
    def addButton(self, name, txt, fg, bg, cspan):
        self.items[name].append(['button', txt, fg, bg, cspan])

    def addEntry(self, name, txt, w, cspan, val=''):
        self.items[name].append(['entry', txt, w, cspan, val])

    def addText(self, name, txt, w, h, cspan, rspan, val=""):
        self.items[name].append(['text', txt, w, h, cspan, rspan, val])

    def addLabel(self, name, txt, fg, bg, cspan):
        self.items[name].append(['label', txt, fg, bg, cspan])

    def addBreak(self, name):
        self.items[name].append(['br', "BR"])

    def addSpace(self, name,n):
        self.items[name].append(['space', n])

    ## Create Button Item
    def createButtonItem(self, frame, sname, name, fg="#000000", bg="#cccccc", cspan=1):
        btn = Button(frame, text=name, command=self.mkcallback(name) , bg=bg, fg=fg)
	self.buttons[sname+":"+name] = btn
        return [btn, cspan]

    ## Create Entry Item
    def createEntryItem(self, frame, sname, name, eid, w, cspan=1, val=''):
        var=StringVar()
	var.set(val.strip())
	self.inputvar[sname+":"+eid] = var
        enty = Entry(frame, textvariable=var, width=int(w))
        self.bind_commands_to_entry(enty, name, eid)

        return [enty, cspan]

    def bind_commands_to_entry(self, enty, name, eid):
	key = name+":gui:"+eid
	if self.keys[key] :
            self._logger.RTC_INFO("Register Entry callback")
            enty.bind('<Return>', self.mkinputcallback(eid))
        return 

    def getEntry(self, eid):
        try:
            return self.inputvar[eid].get()
	except:
            return ""

    def setEntry(self, eid, txt=""):
        try:
            return self.inputvar[eid].set(txt)
	except:
            return ""


    ## Create Text Item
    def createTextItem(self, frame, sname, name, eid, w, h, cspan=1, rspan=1, txt=""):
        stxt = ScrolledText(frame, width=int(w), height=int(h))
        stxt.insert(END, txt.strip())
        stxt.tag_config("csel", background="blue",foreground="white")
	self.stext[sname+":"+eid] = stxt
	key = name+":gui:"+eid

	return [stxt, cspan, rspan]

    def getText(self, eid):
        try:
            return self.stext[eid].get(1.0,END)
	except:
            return ""

    def unsetSelText(self, eid):
        try:
	    txt=self.stext[eid]
	    rng=txt.tag_ranges("csel")
            txt.tag_remove("csel", rng[0], rng[1])
	except:
            pass

    def getSelText(self, eid):
        try:
	    txt=self.stext[eid]
	    rng=txt.tag_ranges("csel")
            return txt.get(rng[0], rng[1])
	except:
            return "" 

    def nextSelText(self, eid):
        try:
	    txt=self.stext[eid]
	    rng=txt.tag_ranges("csel")
	    nl=int(txt.index(rng[0]).split(".")[0]) + 1
            if nl > self.getLastIndex(eid) : return nl-1
            self.setSelText(eid, nl)
            return nl 
	except:
            return 0 

    def prevSelText(self, eid):
        try:
	    txt=self.stext[eid]
	    rng=txt.tag_ranges("csel")
	    nl=int(txt.index(rng[0]).split(".")[0]) - 1
            self.setSelText(eid, nl)
            return nl 
	except:
            return 0 

    def getSelTextLine(self, eid):
        try:
	    txt=self.stext[eid]
	    rng=txt.tag_ranges("csel")
	    nl=int(txt.index(rng[0]).split(".")[0])
            return nl 
	except:
            return 0 

    def setSelText(self, eid, n=1):
        try:
            spos='%d.0' % (n)
            epos='%d.0' % (n+1)
            self.unsetSelText(eid)
            self.stext[eid].tag_add("csel", spos, epos)
            self.setCurrentIndex(eid, n)
	except:
            pass

    def getNthLine(self, eid, n=1):
        try:
            spos='%d.0' % (n)
            epos='%d.0' % (n+1)
            return self.stext[eid].get(spos,epos)
	except:
            return ""

    def getLastLine(self, eid, n=1):
        try:
            spos=self.stext[eid].index('end-%dl' % (n))
            epos=self.stext[eid].index('end-%dl' % (n-1))
            return self.stext[eid].get(spos,epos)
	except:
            return ""

    def getLastIndex(self, eid):
        try:
            return int(self.stext[eid].index('end-1c').split('.')[0])
	except:
            return 1

    def getCurrentIndex(self, eid):
        try:
            return int(self.stext[eid].index('insert').split('.')[0])
	except:
            return 0

    def setCurrentIndex(self, eid, n=1):
        try:
            self.stext[eid].mark_set('insert', "%d.0" % (n))
            return n
	except:
            return 0

    def appendText(self, eid, txt=""):
        try:
            val= self.stext[eid].insert(END, txt)
            self.stext[eid].see(END)
            return val
	except:
            return ""

    def insertText(self, eid, pos, txt=""):
        try:
            val= self.stext[eid].insert(pos, txt)
            self.stext[eid].see(pos)
            return val
	except:
            return ""

    def clearText(self, eid):
        try:
            return self.stext[eid].delete(1.0,END)
	except:
            return ""
   
    def setButtonConfig(self, eid, **cfg):
        try:
            self.buttons[eid].config(**cfg)
	except:
	    print "ERROR"
            pass

    def setLabelConfig(self, eid, **cfg):
        try:
            self.labels[eid].configure(**cfg)
	except:
	    print "ERROR"
            pass

    ## Create Label Item
    def createLabelItem(self, frame, sname, name, fg="#ffffff", bg="#444444", cspan=1):
        if not fg: fg="#ffffff"
        if not bg: bg="#444444"
        lbl = Label(frame, text=name, bg=bg, fg=fg )
	self.labels[sname+":"+name] = lbl
        return [lbl, cspan]

    ## Layout GUI items
    def packItems(self, name):
        n=self.max_columns
        if self.gui_items[name] :
           i=0
           j=1
           for itm in self.gui_items[name] :
             if ( i % self.max_columns ) == 0:
               j += 1

             if itm == "BR":
               j += 1
               i = 0

             elif itm == "SP":
               i += 1

             else :
               if type(itm) == list:
	          itm[0].grid(row=j, column=i, columnspan=itm[1], sticky=W+E)
		  i = i+itm[1] 
               else :
                  itm.grid(row=j, column=i, sticky=W + E)
                  i = i+1
               i = i % self.max_columns

    ## Display/Hide GUI Window
    def showFrame(self, name):
        if self.frames[name] :
#           self.frames[name].place(relx=0.0, rely=0, relwidth=1, relheight=1)
           self.frames[name].pack()

    def hideFrame(self, name):
        if self.frames[name] :
           self.frames[name].pack_forget()
#           self.frames[name].place_forget()

    ## Create and layout GUI items
    def createGuiPanel(self, name):
        if name:
           items = self.items[name]
           self.gui_items[name] = []

           for itm in items:
             if itm[0] == 'br':
               self.gui_items[name].append( "BR" )

             elif itm[0] == 'space':
               for i in range( int(itm[1] )):
                 self.gui_items[name].append( "SP" )

             elif itm[0] == 'button':
               self.gui_items[name].append(
		       self.createButtonItem(self.frames[name], name,
                                   itm[1], itm[2], itm[3], int(itm[4]))
		       )

             elif itm[0] == 'entry':
               self.gui_items[name].append(
		       self.createEntryItem(self.frames[name], name,
		       		name, itm[1], itm[2], int(itm[3]), itm[4])
		       )

             elif itm[0] == 'text':
               self.gui_items[name].append(
		       self.createTextItem(self.frames[name],name,
			       name, itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]), itm[6])
		       )

             elif itm[0] == 'label':
               self.gui_items[name].append(
		       self.createLabelItem(self.frames[name], name,
                                           itm[1], itm[2], itm[3], int(itm[4]))
		       )
             else:
#               self.gui_items[name].append( itm[0] )
               pass

           self.packItems(name)

        return 0

    def stateChanged(self, event=None, *args):
        try:
           self.hideFrame(self.prev_state)
           self.showFrame(self.next_state)
        except:
           pass

    def getSubprocessList(self):
        res=[]
        newlst=[]
        for p in self.popen:
            p.poll()
            if p.returncode == None:
                res.append(p.pid)
                newlst.append(p)
        self.popen = newlst
        return res

    def killSubprocess(self, pid=None):
        for p in self.popen:
            p.poll()
            if pid == None or p.pid == pid :
                p.terminate()
        return 


class eSEATManager:
    def __init__(self, mlfile=None):

        if mlfile is None:
           argv = self.parseArgs()
	else:
           argv = [mlfile]

        self.comp = None
        self.manager = OpenRTM_aist.Manager.init(argv)

        if opts.naming_format:
            self.manager._config.setProperty("naming.formats", opts.naming_format)

        self.manager.setModuleInitProc(self.moduleInit)
        self.manager.activateManager()

        instance_name = self.comp.getProperties().getProperty("naming.names")
	instance_name = formatInstanceName(instance_name)

        self.comp.setInstanceName(instance_name)

    def parseArgs(self):
        global opts
        encoding = locale.getpreferredencoding()
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

        parser = utils.MyParser(version=__version__, usage="%prog [seatmlfile]",
                                description=__doc__)

        #utils.addmanageropts(parser)
        #parser.add_option('-g', '--gui', dest='guimode', action="store_true",
        #                  default=False,
        #                  help='show file open dialog in GUI')

        parser.add_option('-f', '--config-file', dest='config_file', type="string",
			 help='apply configuration file')

        parser.add_option('-n', '--name', dest='naming_format', type="string",
                          help='set naming format' )

        try:
            opts, args = parser.parse_args()
        except optparse.OptionError, e:
            print >>sys.stderr, 'OptionError:', e
            sys.exit(1)

        self._scriptfile = None
        if(len(args) > 0):
            self._scriptfile = args[0]

#        if opts.guimode == True:
#            sel = utils.askopenfilenames(title="select script files")
#            if sel is not None:
#                args.extend(sel)
    
        if opts.naming_format:
           sys.argv.remove('-n')
           sys.argv.remove(opts.naming_format)

        if len(args) == 0:
            parser.error("wrong number of arguments")
            sys.exit(1)
	
	return sys.argv


    def start(self):
        if self.comp.hasGUI() :
            self.manager.runManager(True)

            # GUI part
            self.comp.root = Tk()
            for st in self.comp.states:
                self.comp.newFrame(st)
                self.comp.createGuiPanel(st)

            self.comp.showFrame(self.comp.init_state)
            self.comp.frames[self.comp.init_state].pack()

            self.comp.root.bind("<<state_transfer>>", self.comp.stateChanged)
            self.comp.setTitle(self.comp.getInstanceName())
            self.comp.root.mainloop()

            self.comp.disconnectAll()

            # Shutdown Component
	    try:
               self.manager.shutdown()
	    except:
	       pass 

            sys.exit(1)
        else:
            self.manager.runManager()


    def moduleInit(self, manager):
        profile = OpenRTM_aist.Properties(defaults_str=eseat_spec)
        manager.registerFactory(profile, eSEAT, OpenRTM_aist.Delete)
        self.comp = manager.createComponent("eSEAT")
        self.comp.manager = manager

        if self._scriptfile :
            ret = self.comp.loadSEATML(self._scriptfile)

#
# Parse Key String
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

def converDataType(dtype, data, code='utf-8'):
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

def formatInstanceName(name):
   fullname=name.split('/')
   rtcname = fullname[len(fullname) -1 ]
   return rtcname.split('.')[0]

def instantiateDataType(dtype):
   if isinstance(dtype, int) : desc = [dtype]
   elif isinstance(dtype, tuple) : desc = dtype
   else : 
     desc=omniORB.findType(dtype._NP_RepositoryId) 

   if desc[0] in [omniORB.tcInternal.tv_alias ]: return instantiateDataType(desc[2])

   if desc[0] in [omniORB.tcInternal.tv_short, 
                  omniORB.tcInternal.tv_long, 
                  omniORB.tcInternal.tv_ushort, 
                  omniORB.tcInternal.tv_ulong,
                  omniORB.tcInternal.tv_boolean,
                  omniORB.tcInternal.tv_char,
                  omniORB.tcInternal.tv_octet,
                  omniORB.tcInternal.tv_longlong,
                  omniORB.tcInternal.tv_enum
		 ]: return 0

   if desc[0] in [omniORB.tcInternal.tv_float, 
                  omniORB.tcInternal.tv_double,
                  omniORB.tcInternal.tv_longdouble
                 ]: return 0.0

   if desc[0] in [omniORB.tcInternal.tv_sequence, 
                  omniORB.tcInternal.tv_array,
                 ]: return []


   if desc[0] in [omniORB.tcInternal.tv_string ]: return ""
   if desc[0] in [omniORB.tcInternal.tv_wstring,
                  omniORB.tcInternal.tv_wchar
		   ]: return u""

   if desc[0] == omniORB.tcInternal.tv_struct:
     arg=[]
     for i in  range(4, len(desc), 2):
       attr=desc[i]
       attr_type=desc[i+1]
       arg.append(instantiateDataType(attr_type))
     return desc[1](*arg)
   return None

def main(ssml_file=None):
    seatmgr = eSEATManager(ssml_file)
    seatmgr.start()
    return 0

if __name__=='__main__':
    seatmgr = eSEATManager()
    seat = seatmgr.comp
    seatmgr.start()
    sys.exit(1)

