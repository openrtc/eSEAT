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
import sys
import os
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

########
#  for OpenRTM-aist
import OpenRTM_aist
import omniORB
from RTC  import *

#######
# XML Parser
from bs4  import BeautifulSoup

#########
#  GUI etc.
import utils
from Tkinter import * 
from ScrolledText import * 

#########
#  WebAdaptor
from SocketAdaptor import * 

#########
#  WebAdaptor
from WebAdaptor import * 

###############################################################
#
#  execute seatml parser files
#
execfile('SeatmlParser.py', globals())

#########################################################################
#
#  Class eSEAT_Core
#
class eSEAT_Core:
    def __init__(self):
        if hasattr(sys, "frozen"):
            self._basedir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        else:
            self._basedir = os.path.dirname(__file__)
        self.parser = SEATML_Parser(self)
        self.states = []
        self.keys = {}
        self.regkeys = {}
        self.statestack = []
        self.currentstate = "start"
        self.adaptors = {}
        self.adaptortype = {}

        self._data = {}
        self._port = {}
        self.popen = []

        self.init_state = None
        self._scriptfile = ["None"]
        self._scorelimit = [0.0]
        self.webServer = None
        self.root = None

    ##### Other Adaptors
    #
    # Create the Raw Socket
    #
    def createSocketPort(self, name, host, port):
        self.adaptors[name] = SocketAdaptor(self, name, host, port)

    #
    # Create the Web Server Port
    #
    def createWebAdaptor(self, name, port, index, whost=""):
        if self.webServer  is None:
            self.adaptors[name] = WebSocketServer(CometReader(self), name, "", port, index)
            self.adaptors[name].start()
            self.webServer = self.adaptors[name]
            whosts = whost.split(',')
            for x in whosts:
              if x :
                self.webServer.appendWhiteList(x.strip())
        else:
            self._logger.RTC_INFO(u"Failed to create Webadaptor:" + name + " already exists")

    ###########################
    # Send Data 
    #
    def send(self, name, data, code='utf-8'):
        if isinstance(data, str) :
            self._logger.RTC_INFO("sending message %s (to %s)" % (data, name))
        else:
            self._logger.RTC_INFO("sending message to %s" % (name,))

        dtype = self.adaptortype[name][1]

        if self.adaptortype[name][2]:
            ndata = []
            if type(data) == str :
              for d in data.split(","):
                ndata.append( convertDataType(dtype, d, code) )
              self._data[name].data = ndata
            else:
              self._data[name] = data

        elif dtype == str:
            self._data[name].data = data.encode(code)

        elif dtype == unicode:
            self._logger.RTC_INFO("sending message to %s, %s" % (data,code))
            self._data[name].data = unicode(data)

        elif dtype == int or dtype == float :
            self._data[name].data = dtype(data)

        else:
            try:
                if type(data) == str :
                  self._data[name] = apply(dtype, eval(data))
                else:
                  self._data[name] = data
            except:
                self._logger.RTC_ERROR( "ERROR in send: %s %s" % (name , data))

        try:
            self._port[name].write(self._data[name])
        except:
            self._logger.RTC_ERROR("Fail to sending message to %s" % (name,))

    ##################################
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
            cmds = self.processJuliusResult(name, s)
        else:
            cmds = self.lookupWithDefault(self.currentstate, name, s)

        if not cmds:
            self._logger.RTC_INFO("no command found")
            return False

        #
        #
        for c in cmds:
            self.activateCommand(c, s)
        return True

    #
    # Event process for Julius
    def processJuliusResult(self, name, s):
        doc = BeautifulSoup(s)

        for s in doc.findAll('data'):
            rank = int(s['rank'])
            score = float(s['score'])
            text = s['text']
            self._logger.RTC_INFO("#%i: %s (%f)" % (rank, text, score))

            if score < self._scorelimit[0]:
                self._logger.RTC_INFO("[rejected] score under limit")
                continue

            cmds = self.lookupWithDefault(self.currentstate, name, text)
            if cmds:
                return cmds
            else:
                self._logger.RTC_INFO("[rejected] no matching phrases")
        return None

    #
    #  Event process for data-in-event
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

    #
    #
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

    #############################
    #  For STATE of eSEAT
    #
    #  Get state infomation
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
    #
    def create_state(self, name):
        self.items[name] = []
        if self.init_state == None:
            self.init_state = name
        return 

    ###############################################
    # State Transition for eSEAT
    #
    def stateTransfer(self, newstate):
        try:
            for c in self.keys[self.currentstate+":::onexit"]:
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
            for c in self.keys[self.currentstate+":::onentry"]:
                self.activateCommand(c)
        except KeyError:
            pass

    ############ T A G Operations
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
                if self.inputvar.has_key(input_id) :
                    data = self.inputvar[input_id].get()
                elif self.stext.has_key(input_id) :
                    data = self.getLastLine(input_id, 1)

            #
            #  Call 'send' method of Adaptor
            #
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
            self.stateTransfer(data)

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
        #
        # execute shell command with subprocess
        res = subprocess.Popen(data, shell=True)
        self.popen.append(res)

        #
        #  Call 'send' method of Adaptor
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
        globals()['web_in_data'] = indata

        #
        #   execute script or script file
        if fname : execfile(fname,globals())
        try:
          if data :
            exec(data, globals())
        except:
          print data
          #self._logger.RTC_ERROR("Fail to execute script:" + name)
   
        # 
        #  Call 'send' method of Adaptor to send the result...
        rtc_result = globals()['rtc_result'] 
        if rtc_result == None :
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

    ########################
    #
    #  Activate Lookuped Commands
    #
    def activateCommand(self, c, data=None):
        if   c[0] == 'c': self.applyMessage(c)
        elif c[0] == 'l': self.applyLog(c)
        elif c[0] == 'x': self.applyShell(c)
        elif c[0] == 's': self.applyScript(c, data)
        elif c[0] == 't': self.applyTransition(c)

    #
    #
    def activateCommandEx(self, c, data):
        if c[0] == 'c': c[3] = None
        self.activateCommand(c, data)


    ##############################
    #  main SEATML loader
    #
    def loadSEATML(self, f):
        self._logger.RTC_INFO("Start loadSEATML:"+f)
        res = self.parser.load(f)
        if res == 1 : 
            self._logger.RTC_ERROR("===> SEATML Parser error")
            if self.manager : self.manager.shutdown()
            sys.exit(1)

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

    ##############################################
    #  Callback function for WebAdaptor
    #
    def callComet(self):
      res = ""

      return res

    ################################################ 
    #
    #  Sub-process
    #
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

###########################################################
#   eSEAT_Gui
#
#
class eSEAT_Gui:
    def __init__(self):
        self.gui_items = {}
        self.frames = {}
        self.max_columns = 20
        self.items = {}
        self.inputvar = {}
        self.stext = {}
        self.buttons = {}
        self.labels = {}

    ###################### GUI part ################
    def hasGUI(self):
        for x in self.items.keys():
            if len(self.items[x]) : return True
        return False

    #########################################
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

    #############################
    #  Create GUI items
    #
    #  Create Frame
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

    #############  CREATE GUI ITEMS ##############
    ## Create Button Item
    def createButtonItem(self, frame, sname, name, fg="#000000", bg="#cccccc", cspan=1):
        btn = Button(frame, text=name, command=self.mkcallback(name) , bg=bg, fg=fg)
        self.buttons[sname+":"+name] = btn
        return [btn, cspan]
    
    def setButtonConfig(self, eid, **cfg):
        try:
            self.buttons[eid].config(**cfg)
        except:
            print "ERROR"
            pass

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
   
    ## Create Label Item
    def createLabelItem(self, frame, sname, name, fg="#ffffff", bg="#444444", cspan=1):
        if not fg: fg="#ffffff"
        if not bg: bg="#444444"
        lbl = Label(frame, text=name, bg=bg, fg=fg )
        self.labels[sname+":"+name] = lbl
        return [lbl, cspan]

    def setLabelConfig(self, eid, **cfg):
        try:
            self.labels[eid].configure(**cfg)
        except:
            print "ERROR"
            pass

    #########  LAYOUT ITEMS ON A FRAME ############
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
                       self.createEntryItem(self.frames[name], name, name,
                                       itm[1], itm[2], int(itm[3]), itm[4])
                       )

               elif itm[0] == 'text':
                   self.gui_items[name].append(
                       self.createTextItem(self.frames[name],name, name,
                                itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]), itm[6])
                       )

               elif itm[0] == 'label':
                   self.gui_items[name].append(
                       self.createLabelItem(self.frames[name], name,
                                itm[1], itm[2], itm[3], int(itm[4]))
                       )
               else:
                   pass

           self.packItems(name)

        return 0

    ##
    ## Change the view of GUI with state transition
    def stateChanged(self, event=None, *args):
        try:
           self.hideFrame(self.prev_state)
           self.showFrame(self.next_state)
        except:
           pass

    ## Display/Hide GUI Window
    def showFrame(self, name):
        if self.frames[name] :
           self.frames[name].pack()

    def hideFrame(self, name):
        if self.frames[name] :
           self.frames[name].pack_forget()
    #
    ############### End of GUI part ################
