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
import string

import threading

import traceback
import subprocess

import time
import yaml

from collections import OrderedDict

########
# XML Parser of Julius result
from bs4  import BeautifulSoup

#########
#  GUI etc.
try:
    from Tkinter import * 
    import ttk
    from ScrolledText import ScrolledText 
except:
    from tkinter import *
    import tkinter.ttk as ttk
    from tkinter.scrolledtext import ScrolledText
 
###################################################3
#
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

try:
    import OpenRTM_aist
    import omniORB
    from RTC import * 
    from RtcAdator import instantiateDataType 
except:
    pass

try:
    from RtcAdator import instantiateDataType 
except:
    try:
        from .RtcAdator import instantiateDataType 
    except:
        pass
###############################################################
#  Global Variables
#
__version__ = "3.0"

def getGlobals():
    return globals()

def setGlobals(name, val):
    globals()[name] = val

if sys.version_info.major > 2:
    def unicode(s):
        return str(s)

#########
#  SocketAdaptor
try:
  from SocketAdaptor import SocketAdaptor 
  from WebAdaptor import WebSocketServer,CometReader,parseQueryString
  from Task import State, TaskGroup
except:
  from .SocketAdaptor import SocketAdaptor 
  from .WebAdaptor import WebSocketServer,CometReader,parseQueryString
  from .Task import State, TaskGroup

####### for ROS
try:
  from RosAdaptor import *
  __ros_version__=getRosVersion()
except:
  try:
    from .RosAdaptor import *
    __ros_version__=getRosVersion()
  except:
    __ros_version__=None
    #traceback.print_exc()


###############################################################
#
#  execute seatml parser files
#
try:
  from SeatmlParser import SEATML_Parser,convertDataType
except:
  from .SeatmlParser import SEATML_Parser,convertDataType

###############################################################
#
# Dummy logger
#
class SeatLogger:
    #
    #
    def __init__(self, name, flag=True):
        self._name = name
        self._flag = flag
    #
    #
    def setFlag(self, b):
        self._flag = b
    #
    #
    def info(self, msg):
        if self._flag :
            print ("INFO:"+self._name+" "+msg)
    #
    #
    def error(self, msg):
        print ("ERROR:"+self._name+" "+msg, file=sys.stderr)
    #
    #
    def warn(self, msg):
        print ("WARN:"+self._name+" "+msg, file=sys.stderr)


###############################################################
#  Class eSEAT_Core
#
class eSEAT_Core:
    #
    #
    def __init__(self):
        if hasattr(sys, "frozen"):
            self._basedir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        else:
            self._basedir = os.path.dirname(__file__)
        self.parser = SEATML_Parser(self)
        self.states = OrderedDict()
        #self.keys = {}
        self.regkeys = {}
        self.statestack = []
        self.currentstate = "start"
        self.adaptors = {}
        self.adaptortype = {}

        self.ros_server = {}
        self.ros_client = {}
        self.ros_action_server = {}
        self.ros_action_client = {}

        self._data = {}
        self._port = {}
        self.popen = []

        self.init_state = None
        self._scriptfile = ["None"]
        self._scorelimit = [0.0]
        self.webServer = None
        self.root = None

        self.seat_mgr=None

        self.last_on_data = 0

        self._logger = SeatLogger("eSEAT")

        setGlobals('seat', self)

        self.name="eSEAT"
        self.ros_node=None
        self.ros_anonymous=False

        self.interval=1
        self.send_with_thread=0.001

    #
    #
    def exit_comp(self):
        for adp in self.adaptors:
           if self.adaptors[adp] != self:
               self.adaptors[adp].terminate()
        return

    def setLogFlag(self, flg):
        self._logger.setFlag(flg)

    ##### Other Adaptors
    #
    # Create the Raw Socket
    #
    def createSocketPort(self, name, host, port):
        self.adaptors[name] = SocketAdaptor(self, name, host, port)

    #
    # Create the Web Server Port
    #
    def createWebAdaptor(self, name, port, index, whost="", dirname="html"):
        if self.webServer  is None:
            comet_reader=CometReader(self,dirname)
            self.adaptors[name] = WebSocketServer(comet_reader,
                                          name, "", port, index)

            if whost :
                whosts = whost.split(',')
                for x in whosts:
                    if x :
                        self.webServer.appendWhiteList(x.strip())

            self.webServer = self.adaptors[name]

            if self.adaptors[name].bind_res != 1 :
                print ("=== Bind ERROR ===")
                #os._exit(1)
                return

            self.adaptors[name].start()

        else:
            self._logger.info(u"Failed to create Webadaptor:" + name + " already exists")

    #
    #
    #   for ROS Pub/Sub
    def initRosNode(self):
      if __ros_version__  > 0:
        self.ros_node=initRosNode(self.name, self.ros_anonymous)
      else:
        print("Unsupport ROS")

    #
    #
    def createRosPublisher(self, name, datatype, size=1, nodelay=False):
      if __ros_version__ > 0:
        self.initRosNode()
        if self.ros_node:
          self.adaptors[name]=RosAdaptor(name, 'Publisher', self)
          self.adaptors[name].createPublisher(name, datatype, size, nodelay)

    #
    #
    def ros_publish(self, name, val):
      try:
        self.adaptors[name].publish(val)
      except:
        print("Fail to ros_publish %s" % name)

    #
    #
    def createRosSubscriber(self, name, datatype, callback):
      if __ros_version__ > 0:
        self.initRosNode()
        if self.ros_node:
          self.adaptors[name]=RosAdaptor(name, 'Subscriber', self)
          if not callback:
            callback=lambda x: eSEAT_Core.onData(self,name, x)
          elif type(callback) == str:
            callback=eval(callback)

          self.adaptors[name].createSubscriber(name, datatype, callback)

    #
    # for Ros Service
    def createRosServer(self, name, srv_name, srv_type, srv_impl, fname):
      if __ros_version__ > 0:
        self.initRosNode()

        if srv_name is None:
          srv_name=name
          name=name+"_ros_server"

        self.adaptors[name]=RosAdaptor(name, 'Server', self)
        self.adaptors[name].createServer(srv_name, srv_type, srv_impl, fname) 
        self.ros_server[srv_name]=self.adaptors[name]
    #
    #     
    def createRosClient(self, name, srv_name, srv_type):
      if __ros_version__ > 0:
        self.initRosNode()

        if srv_name is None:
          srv_name=name
          name=name+"_ros_client"

        self.adaptors[name]=RosAdaptor(name, 'Client', self)
        self.adaptors[name].createClient(srv_name, srv_type) 
        self.ros_client[srv_name]=self.adaptors[name]
    #
    #
    def callRosService(self, name, *args):
        try:
          return self.ros_client[name].callRosService(name, *args)
        except:
          traceback.print_exc()
          print("Error in callRosService %s" % name)
          return None
          
    #
    # for Ros Service
    def createRosActionServer(self, name, act_id, act_type, act_cb, fname):
      if __ros_version__ > 0:
        self.initRosNode()

        if act_id is None:
          act_id=name
          name=name+"_act_server"

        self.adaptors[name]=RosAdaptor(name, 'ActionServer', self)
        self.adaptors[name].createActionServer(act_id, act_type, act_cb, fname) 
        self.ros_action_server[act_id]=self.adaptors[name]
    #
    #     
    def createRosActionClient(self, name, act_id, act_type):
      if __ros_version__ > 0:
        self.initRosNode()

        if act_id is None:
          act_id=name
          name=name+"_act_client"

        self.adaptors[name]=RosAdaptor(name, 'ActionClient', self)
        self.adaptors[name].createActionClient(act_id, act_type) 
        self.ros_action_client[act_id]=self.adaptors[name]
    #
    #
    def getRosActionServer(self, name):
      try:
        return self.ros_action_server[name]
      except:
        return None
    #
    #
    def getRosActionClient(self, name):
      try:
        return self.ros_action_client[name]
      except:
        return None
    #
    #  ros_spin
    def startRosService(self):
        if self.ros_node:
          startRosService()

    #
    #
    def get_caller_id(self):
      if __ros_version__ == 1:
        return rospy.get_caller_id()
      elif __ros_version__ == 2:
        return ""
      return None

    #
    #
    def newData(self, name):
      try:
        if __ros_version__ > 0 and isinstance(self.adaptors[name], RosAdaptor):
          return self.adaptors[name].newMessage()
        else:
          return ""
      except:
        return ""

    #
    #  Create Adaptor called by SEATML_Parser
    #
    def createAdaptor(self, compname, tag, env=globals()):
        try:
            name = str(tag.get('name'))
            type = tag.get('type')
            self._logger.info(u"createAdaptor: " + type + ": " + name)

            if type == 'web' :
                dirname = tag.get('document_root')
                if not dirname: dirname = tag.get('dir')
                if dirname:
                    self.createWebAdaptor(name, int(tag.get('port')), compname, tag.get('host'), dirname)
                else:
                    self.createWebAdaptor(name, int(tag.get('port')), compname, tag.get('host'))

            elif type == 'socket' :
                self.createSocketPort(name, tag.get('host'), int(tag.get('port')))

            elif type == 'ros_pub' :
                size_str=tag.get('size')
                if size_str:
                   size=int(size_str)
                else:
                   size=1
                delay_str=tag.get('nodelay')
                if delay_str:   
                    self.createRosPublisher(name, tag.get('datatype'), size, True)
                else:
                    self.createRosPublisher(name, tag.get('datatype'), size)

            elif type == 'ros_sub' :
                fname=tag.get('file')
                if fname:
                  utils.exec_script_file(fname, globals())
                self.createRosSubscriber(name, tag.get('datatype'),tag.get('callback'))

            elif type == 'ros_server' :
                fname=tag.get('file')
                srv_name=tag.get('service')
                srv_type=tag.get('service_type')
                srv_impl=tag.get('impl')
                self.createRosServer(name, srv_name, srv_type, srv_impl, fname)

            elif type == 'ros_client' :
                srv_name=tag.get('service')
                srv_type=tag.get('service_type')
                self.createRosClient(name, srv_name, srv_type)

            elif type == 'ros_action_server' :
                fname=tag.get('file')
                act_id=tag.get('action_id')
                act_type=tag.get('action_type')
                act_cb=tag.get('callback')
                self.createRosActionServer(name, act_id, act_type, act_cb, fname)

            elif type == 'ros_action_client' :
                act_id=tag.get('action_id')
                act_type=tag.get('action_type')
                self.createRosActionClient(name, act_id, act_type)

            else:
                self._logger.warn(u"invalid type: " + type + ": " + name)
                return -1
        except:
            self._logger.error(u"invalid parameters: " + type + ": " + name)
            traceback.print_exc()
            return -1

        return 1

    def send(self, name, data, code='utf-8'):
        self._logger.error(u"eSEAT_core.send is not implemented")
        return
    #
    #
    def sendto(self, name, data):
        if name in self.adaptors :
            self.adaptors[name].send(name, data)

    #
    #
    def set_result(self, val):
        getGlobals()['__retval__'] = True
        getGlobals()['rtc_result'] = val
    #
    #
    def get_in_data(self):
        return getGlobals()['rtc_in_data']
    #
    #
    def get_web_data(self):
        return getGlobals()['rtc_web_data']

    ##################################
    #  Event processes 
    #
    #  onData: this method called in comming data
    #
    def onData(self, name, data):
        self.resetTimer()
        try:
            if isinstance(data, str):
                if data :
                    data2 = parseQueryString(data)
                    if data2 :
                        self.processOnDataIn(name, data2)
                    else :
                        self.processResult(name, data)
                        self.processOnDataIn(name, data)
            elif __ros_version__ and  isinstance(data, std_msgs.String):
                self.processResult(name, data.data)
                self.processOnDataIn(name, data.data)
            else:
                self.processOnDataIn(name, data)
        except:
            self._logger.error(traceback.format_exc())

    #
    #
    def onCall(self, name, data, key="oncall"):
        self.resetTimer()
        try:
            return self.processOnDataIn(name, data, key)
        except:
            self._logger.error(traceback.format_exc())
        return None
    #
    #
    def onCallback(self, name, *data, **kwarg):
        self.resetTimer()
        try:
            if 'key' in kwarg:
               key=kwarg['key']
            else:
               key="callback"
            return self.processOnDataIn(name, data, key)
        except:
            self._logger.error(traceback.format_exc())
        return None

    ############################################
    #   main event process 
    #
    def processResult(self, name, s):
        if sys.version_info.major == 2:
            try:
                s = unicode(s)
            except UnicodeDecodeError:
                s = str(s).encode('string_escape')
                s = unicode(s)
        else:
            pass
            
        self._logger.info("got input %s (%s)" % (s, name))
        cmds = None

        if s.count('<?xml') > 0:
            cmds = self.processJuliusResult(name, s)
        else:
            cmds = self.lookupWithDefault(self.currentstate, name, s)

        if not cmds:
            self._logger.info("no command found")
            return False
        #
        #
        cmds.execute(s)
        self.resetTimer()
        return True

    #####################################
    # process for the cyclic execution
    #
    def processExec(self, sname=None, flag=False):
        if sname is None : sname = self.currentstate
        cmds = self.states[sname].onexec

        if not cmds :
            if flag :
                self._logger.info("no command found")
            return False

        cmds.execute('')
        return True

    #####################################
    # process for onActivated
    #
    def processActivated(self, flag=False):
        cmds = self.states['all'].onactivated

        if not cmds :
            if flag :
                self._logger.info("no command found")
            return False
        cmds.execute('')
        return True

    #####################################
    # process for onDectivated
    #
    def processDeactivated(self, sname=None, flag=False):
        if sname is None : sname = self.currentstate
        cmds = self.states[sname].ondeactivated

        if not cmds :
            if flag :
                self._logger.info("no command found")
            return False
        cmds.execute('')
        return True


    ##############################
    # process for timeout
    #
    def processTimeout(self, sname=None, flag=False):
        if sname is None : sname = self.currentstate
        cmds = self.states[sname].ontimeout

        if not cmds:
            cmds = self.states['all'].ontimeout

        if not cmds :
            if flag :
                self._logger.info("no command found")
            return False
        #
        cmds.execute('')

        if sname == self.currentstate:
            self.setTimeout(cmds.timeout)

        self.resetTimer()
        return True
    #
    #
    def resetTimer(self):
        self.last_on_data = time.time()
    #
    #
    def setTimeout(self, sec):
        self._on_timeout = sec
    #
    #
    def isTimeout(self):
       return ( self._on_timeout > 0 and time.time() - self.last_on_data >= self._on_timeout )

    #################################
    # Event process for Julius
    #
    def processJuliusResult(self, name, s):
        doc = BeautifulSoup(s)

        for s in doc.findAll('data'):
            rank = int(s['rank'])
            score = float(s['score'])
            text = s['text']
            self._logger.info("#%i: %s (%f)" % (rank, text, score))

            if score < self._scorelimit[0]:
                self._logger.info("[rejected] score under limit")
                continue

            cmds = self.lookupWithDefault(self.currentstate, name, text)
            if cmds:
                setGlobals('julius_result',  {'rank': rank, 'score': score, 'text': text, 'stext': text.split(' ')})
                return cmds
            else:
                self._logger.info("[rejected] no matching phrases")
        return None

    ######################################
    #  Event process for data-in-event
    #
    def initDataIn(self, data):
        setGlobals('seat', self)
        setGlobals('seat_mgr', self.seat_mgr)
        setGlobals('rtc_in_data', data)
        setGlobals('seat_argv', data)
        setGlobals('julius_result', None)
        return
    #
    #
    def processOnDataIn(self, name, data, key="ondata"):
        self._logger.info("got input from %s" %  (name,))
        cmds = self.lookupWithDefault(self.currentstate, name, key)

        if not cmds:
            self._logger.info("no command found")
            return False

        res=True
        if type(cmds) is list:
          for cmd in cmds:
            self.initDataIn(data)
            cmd.execute_pre_script()
            res = cmd.executeEx(data)
        else:
          self.initDataIn(data)
          cmds.execute_pre_script()
          res = cmds.executeEx(data)

        return res
  
    ################################################################
    #  Lookup Registered Commands with default
    #
    def lookupWithDefault(self, state, name, s, flag=True):
        s=s.split(",")[0]
        if flag:
            self._logger.info('looking up...%s: %s' % (name,s,))
        cmds = self.lookupCommand(state, name, s)

        if not cmds:
            cmds = self.lookupCommand(state, 'default', s)

        if not cmds:
            cmds = self.lookupCommand('all', name, s)

        if not cmds:
            cmds = self.lookupCommand('all', 'default', s)

        return cmds

    #
    #  Lookup Registered Commands
    #
    def lookupCommand(self, state, name, s):
        try:
            cmds = self.states[state].matchkey(name, s)
        except:
            cmds = None
        return cmds
        
    #############################
    #  For STATE of eSEAT
    #
    #  Get state infomation
    #
    def getStates(self):
        return self.states

    #
    # set the begining state
    #
    def setStartState(self, name):
        self.startstate = name
        return

    #
    #  Count the number of states 
    #
    def countStates(self):
        return (len(self.states) - 1)

    #
    #  check the named state
    #
    def inStates(self, name):
        return name in self.states

    #
    #  append the named state
    #
    #def appendState(self, name):
    #    self.states.extend([name])
    #    return

    #
    #  initilaize the begining state
    #
    def initStartState(self, name):
        self.startstate = None

        if name in self.states :
            self.startstate = name
        else:
            try:
              self.startstate = self.states.keys()[1]
            except:
              self.startstate = list(self.states.keys())[1]

        self.stateTransfer(self.startstate)
        self._logger.info("current state " + self.currentstate)
    #
    # create the named state
    #
    def create_state(self, name):
        self.items[name] = []
        if not (name in self.states):
            self.states[name] = State(name)
        if self.init_state == None or self.init_state == 'all':
            self.init_state = name
        return 

    ###############################################
    # State Transition for eSEAT
    #
    def stateTransfer(self, newstate):
        try:
            tasks = self.states[self.currentstate].onexit
            if tasks:
                tasks.execute()
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
            #cmds = self.lookupWithDefault(newstate, '', 'ontimeout', False)

            cmds = self.states[self.currentstate].ontimeout
            if not cmds:
                cmds = self.states['all'].ontimeout

            if cmds:
                self.setTimeout(cmds.timeout)

            tasks = self.states[self.currentstate].onentry
            if tasks:
                tasks.execute()
        except KeyError:
            pass


    ##############################
    #  main SEATML loader
    #
    def loadSEATML(self, f):
        self._logger.info("Start loadSEATML:"+f)
        res = self.parser.load(f)
        if res == 1 : 
            self._logger.error("===> SEATML Parser error")
            if self.manager : self.manager.shutdown()
            #sys.exit(1)
        return res


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
    #
    #
    def killSubprocess(self, pid=None):
        for p in self.popen:
            p.poll()
            if pid == None or p.pid == pid :
                p.terminate()
        return 
    #
    # Finalize
    #
    def finalizeSEAT(self):
        for a in self.adaptors.itervalues():
            if isinstance(a, SocketAdaptor):
                a.terminate()
                a.join()
            elif isinstance(a, WebSocketServer):
                a.terminate()
        if self.root : self.root.quit()
        return 
    #
    #
    def loginfo(self, msg):
        self._logger.info(msg)

#  End of eSEAT_Core
###########################################################
###########################################################
#   eSEAT_Gui
#
class eSEAT_Gui:
    def __init__(self):
        self.root = None
        self.gui_items = {}
        self.frames = {}
        self.max_columns = 20
        self.items = {}
        self.inputvar = {}
        self.stext = {}
        self.buttons = {}
        self.comboboxes = {}
        self.checks = {}
        self.check_objs = {}
        self.scales = {}
        self.radio_vals = {}
        self.radiobuttons = {}
        self.listboxes = {}
        self.labels = {}

    #
    #  check the GUI items
    #
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
    #
    #
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
    #
    #
    def setTitle(self, name):
        if self.root : self.root.title(name)

    #  Called by SEATML Parser
    def addFrame(self, name, txt, h, w, relief, fg, bg, cspan=1, rspan=1, frame=''):
        self.items[name].append(['frame', txt, h, w, relief, fg, bg, cspan, rspan, frame])

    def addLabelframe(self, name, txt, h, w, labelanchor, relief, fg, bg, cspan=1, rspan=1, frame=''):
        self.items[name].append(['labelframe', txt, h, w, labelanchor, relief, fg, bg, cspan, rspan, frame])

    def addButton(self, name, txt, fg, bg, w, cspan=1, rspan=1, frame=''):
        self.items[name].append(['button', txt, fg, bg, w, cspan, rspan, frame])

    def addEntry(self, name, txt, w, val='', cspan=1, rspan=1, frame=''):
        self.items[name].append(['entry', txt, w, val, cspan, rspan, frame])

    def addText(self, name, txt, w, h, cspan=1, rspan=1, val="", frame=''):
        self.items[name].append(['text', txt, w, h, cspan, rspan, val, frame])

    def addLabel(self, name, txt, fg, bg, cspan=1, rspan=1, frame='', oarg=''):
        self.items[name].append(['label', txt, fg, bg, cspan, rspan, oarg, frame])

    def addCombobox(self, name, txt, txtlist, val, cspan=1, rspan=1, frame=''):
        self.items[name].append(['combobox', txt, txtlist, val, cspan, rspan, frame])

    def addCheckbutton(self, name, txt, cspan=1, rspan=1, frame=''):
        self.items[name].append(['checkbutton', txt, cspan, rspan, frame])

    def addScale(self, name, txt, frm, to, res, ori, cspan=1, rspan=1, frame=''):
        self.items[name].append(['scale', txt, frm, to, res, ori, cspan, rspan, frame])

    def addListbox(self, name, txt, txtlist, height, cspan=1, rspan=1, frame=''):
        self.items[name].append(['listbox', txt, txtlist, height, cspan, rspan, frame])

    def addRadiobutton(self, name, txt, var, val, cspan=1, rspan=1, frame=''):
        self.items[name].append(['radiobutton', txt, var, val, cspan, rspan, frame])

    def addBreak(self, name, frame=''):
        self.items[name].append(['br', "BR", frame])

    def addSpace(self, name,n, frame=''):
        self.items[name].append(['space', n, frame])

    ###################  CREATE GUI ITEMS ####################
    ################# F R A M E ###################
    def createFrameItem(self, frame, sname, name, h, w, r, fg="#000000", bg="#cccccc", cspan=1, rspan=1):
        if not h: h=0
        if not w: w=0
        frm = Frame(frame, height=int(h), width=int(w), relief=r, bg=bg, fg=fg)
        self.frames[sname+":"+name] = frm

        return [frm, cspan, rspan]

    ################# L A B E L F R A M E ###################
    def createLabelFrameItem(self, frame, sname, name, h, w, anchor, r, fg="#000000", bg="#cccccc", cspan=1, rspan=1):
        if not h: h=0
        if not w: w=0
        frm = LabelFrame(frame, text=name, height=int(h), width=int(w), 
                          labelanchor=anchor, relief=r, bg=bg, fg=fg)
        self.frames[sname+":"+name] = frm

        return [frm, cspan, rspan]


    #################  B U T T O N ################### 
    ## Create Button Ite
    def createButtonItem(self, frame, sname, name, fg="#000000", bg="#cccccc", w=None, cspan=1, rspan=1):
        if w :
            btn = Button(frame, text=name, command=self.mkcallback(name) , bg=bg, fg=fg, width=int(w))
        else:
            btn = Button(frame, text=name, command=self.mkcallback(name) , bg=bg, fg=fg)
        self.buttons[sname+":"+name] = btn

        return [btn, cspan, rspan]
    
    def setButtonConfig(self, eid, **cfg):
        try:
            self.buttons[eid].config(**cfg)
        except:
            print ("ERROR in ButtonConfig")
            pass

    #################  L I N E I N P U T ################### 
    ## Create Entry Item
    def createEntryItem(self, frame, sname, name, eid, w, val='', cspan=1, rspan=1):
        var=StringVar()
        var.set(val.strip())
        self.inputvar[sname+":"+eid] = var
        enty = Entry(frame, textvariable=var, width=int(w))
        self.bind_commands_to_entry(enty, name, eid)

        return [enty, cspan, rspan]

    def bind_commands_to_entry(self, entry, name, eid):
        key = name+":gui:"+eid
        #if self.keys[key] :
        if self.states[name].has_rule('gui', eid) :
            self._logger.info("Register Entry callback")
            entry.bind('<Return>', self.mkinputcallback(eid))
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

    #################  T E X T A R E A ################### 
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

    #################  C O M B O B O X ################### 
    ## Create Combobox Item
    def createComboboxItem(self, frame, sname, name, nameList, val="", cspan=1, rspan=1):
        cbox = ttk.Combobox(frame, textvariable=StringVar())
        func=self.mkcallback(name)
        cbox.bind('<<ComboboxSelected>>',func)
        cbox.bind('<Return>', func)
        nlist=nameList.split(',')
        cbox['values']=nlist
        cbox.set(val)
        self.comboboxes[sname+":"+name] = cbox

        return [cbox, cspan, rspan]
    
    def getComboboxValue(self, eid):
        try:
            val= self.comboboxes[eid].get()
            return val
        except:
            return ""

    ################# C H E C K B U T T O N ################### 
    ## Create Checkbutton Item
    def createCheckButtonItem(self, frame, sname, name, cspan=1, rspan=1):
        chk=BooleanVar()
        func=self.mkcallback(name)
        cbtn=Checkbutton(frame, text=name, variable=chk, command=func)
        self.check_objs[sname+":"+name]=cbtn
        self.checks[sname+":"+name]=chk
        rspan=1

        return [cbtn, cspan, rspan]
    
    def getCheckValue(self, eid):
        try:
            val= self.checks[eid].get()
            return val
        except:
            return ""

    ################# L I S T B O X ################### 
    ## Create Listbox Item
    def createListboxItem(self, frame, sname, name, txtlist, height, cspan=1, rspan=1):
        func=self.mkcallback(name)
        lbox=Listbox(frame, height=height)
        for x in txtlist.split(','):
            lbox.insert(END, x)
        lbox.bind('<<ListboxSelect>>', func)
        self.listboxes[sname+":"+name]=lbox

        return [lbox, cspan, rspan]

    def getListboxValue(self, eid):
        try:
            val= self.listboxes[eid].get(ACTIVE)
            return val
        except:
            return ""

    
    ################# S C A L E ################### 
    ## Create Scale Item
    def createScaleItem(self, frame, sname, name, frm, to, res, ori, cspan=1, rspan=1):
        func=self.mkcallback(name)
        scale=Scale(frame, label=name, orient=ori, from_=frm, to=to, resolution=res,
                     command=func)
        self.scales[sname+":"+name]=scale

        return [scale, cspan, rspan]

    def getScaleValue(self, eid):
        try:
            val= self.scales[eid].get()
            return val
        except:
            return ""

    def setScaleValue(self, eid, val):
        try:
            self.scales[eid].set(val)
            return val
        except:
            return ""
    
    ################# R A D I O B U T T O N ################### 
    ## Create Radiobutton Item
    def createRadiobuttonItem(self, frame, sname, name, var, val, cspan=1, rspan=1):
        key=sname+":"+name

        if not (var in self.radio_vals) :
          self.radio_vals[var]=StringVar()

        func=self.mkcallback(name)
        rbtn=Radiobutton(frame, text=name, value=val,
               variable=self.radio_vals[var], command=func)
        self.radiobuttons[key]=rbtn

        return [rbtn, cspan, rspan]
    
    def getRadioValue(self, var):
        try:
            val= self.radio_vals[var].get()
            return val
        except:
            return ""

    #################  L A B E L ################### 
    ## Create Label Item
    def createLabelItem(self, frame, sname, name, fg="#ffffff", bg="#444444", cspan=1, rspan=1, args=''):
        if not fg: fg="#ffffff"
        if not bg: bg="#444444"
        #lbl = Label(frame, text=name, bg=bg, fg=fg )
        lbl=eval("Label(frame, text=name, bg=bg, fg=fg,"+args+")")
        self.labels[sname+":"+name] = lbl
        return [lbl, cspan, rspan]

    def setLabelConfig(self, eid, **cfg):
        try:
            self.labels[eid].configure(**cfg)
        except:
            print ("ERROR in setLabelConfig")
            pass

    def getFrameName(self, itm, name):
        try:
          if itm[0] == "BR":
            if itm[1] : return name+":"+itm[1]
            return itm[1]
          elif itm[0] == "SP":
            if itm[2] : return name+":"+itm[2]
            return itm[2]
          else:
            master=itm[0].master 
            keys = [ k for k,v in self.frames.items() if v == master]
            if len(keys) == 1:
              return keys[0]
            else:
              return ''
        except:
          return ''

    #########  LAYOUT ITEMS ON A FRAME ############
    ## Layout GUI items
    def packItems(self, name):
      try:
        i={}
        j={}
        n=self.max_columns
        if self.gui_items[name] :
            for n in self.frames.keys():
              i[n]=0
              j[n]=0

            for itm in self.gui_items[name] :
                fn=self.getFrameName(itm, name)
                if not fn : fn=name

                if ( i[fn] % self.max_columns ) == 0:
                    j[fn] += 1

                if itm == "BR":
                    j[fn] += 1
                    i[fn] = 0

                elif itm == "SP":
                    i[fn] += 1

                elif type(itm) == list and itm[0] == "BR":
                    j[fn] += 1
                    i[fn] = 0

                elif type(itm) == list and itm[0] == "SP":
                    i[fn] += itm[1]

                else :
                   if type(itm) == list:
                       itm[0].grid(row=j[fn], column=i[fn], columnspan=itm[1], rowspan=itm[2], sticky=W+E)
                       i[fn] = i[fn] + itm[1] 
                   else :
                       itm.grid(row=j[fn], column=i[fn], sticky=W + E)
                       i[fn] = i[fn] + 1

                   i[fn] = i[fn] % self.max_columns
      except:
        print("Error in packing:", self.frames)
        #traceback.print_exc()

    ## Create and layout GUI items
    def createGuiPanel(self, name):
        if name:
           items = self.items[name]
           self.gui_items[name] = []

           for itm in items:
               fname=name+":"+itm[-1]
               if fname in self.frames:
                   target_frame=self.frames[fname]               
               else:
                   target_frame=self.frames[name]               

               if itm[0] == 'br':
                   self.gui_items[name].append( ["BR", itm[-1]] )

               elif itm[0] == 'space':
                   #for i in range( int(itm[1] )):
                   #    self.gui_items[name].append( ["SP", 1, ''] )
                   self.gui_items[name].append( ["SP", int(itm[1]), itm[-1]] )

               elif itm[0] == 'frame':
                   self.gui_items[name].append(
                       self.createFrameItem(target_frame, name,
                           itm[1], itm[2], itm[3], itm[4], itm[5], 
                           itm[6], int(itm[7]), int(itm[8]))
                       )

               elif itm[0] == 'labelframe':
                   self.gui_items[name].append(
                       self.createLabelFrameItem(target_frame, name,
                           itm[1], itm[2], itm[3], itm[4], itm[5], 
                           itm[6], itm[7], int(itm[8]), int(itm[9]))
                       )

               elif itm[0] == 'button':
                   self.gui_items[name].append(
                       self.createButtonItem(target_frame, name,
                                itm[1], itm[2], itm[3], itm[4], int(itm[5]), int(itm[6]))
                       )

               elif itm[0] == 'entry':
                   self.gui_items[name].append(
                       self.createEntryItem(target_frame, name, name,
                                       itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]))
                       )

               elif itm[0] == 'text':
                   self.gui_items[name].append(
                       self.createTextItem(target_frame,name, name,
                                itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]), itm[6])
                       )

               elif itm[0] == 'label':
                   self.gui_items[name].append(
                       self.createLabelItem(target_frame, name,
                              itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]),itm[6])
                       )
               elif itm[0] == 'combobox':
                   self.gui_items[name].append(
                       self.createComboboxItem(target_frame, name,
                                itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]))
                       )

               elif itm[0] == 'checkbutton':
                   self.gui_items[name].append(
                       self.createCheckButtonItem(target_frame, name,
                                itm[1], int(itm[2]), int(itm[3]))
                       )

               elif itm[0] == 'listbox':
                   self.gui_items[name].append(
                       self.createListboxItem(target_frame, name,
                                itm[1], itm[2], int(itm[3]), int(itm[4]), int(itm[5]))
                       )

               elif itm[0] == 'radiobutton':
                   self.gui_items[name].append(
                       self.createRadiobuttonItem(target_frame, name,
                                itm[1], itm[2], itm[3], int(itm[4]), int(itm[5]))
                       )

               elif itm[0] == 'scale':
                   self.gui_items[name].append(
                       self.createScaleItem(target_frame, name,
                                itm[1], float(itm[2]), float(itm[3]), float(itm[4]),
                                itm[5], int(itm[6]), int(itm[7]))
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
    #   Event loop for GUI
    #
    def startGuiLoop(self, viewer):
        try:
          self.root = Tk()
        except:
          return 1

        if self.hasGUI() : 
            for st in self.states:
                self.newFrame(st)
                self.createGuiPanel(st)

            self.showFrame(self.init_state)
            self.frames[self.init_state].pack()

            self.root.bind("<<state_transfer>>", self.stateChanged)
            self.setTitle(self.getInstanceName())

        if viewer:
            viewer.createViewer(self.root, self.hasGUI())

        self.root.mainloop()
        return 0

#   End of eSEAT_Gui
###########################################################
#
class eSEAT_Node(eSEAT_Core, eSEAT_Gui):
    def __init__(self, infoflag=False):
        eSEAT_Core.__init__(self) 
        eSEAT_Gui.__init__(self) 
        self.manager=None
        self.activated=True
        self._on_timeout = -1
        self._last_process_time=time.time()
        self.rate_hz=0
        self.intval=1.0
        self.rate=None
        self.setRate(1)

        self.setLogFlag(infoflag)
    #
    #
    def exit(self, flag=False):
        try:
            if self.root : self.root.quit()
            if not flag : self.manager.exit()
        except:
            pass

        return True
    #
    #
    def setRate(self, hz):
        try:
          self.rate_hz=hz
          self.intval = 1.0/float(hz)

          if self.ros_node:
            self.rate=createRate(self.rate_hz)
          else:
            self.rate=None
        except:
          self.rate=None
    #
    #      
    def sleep(self):
        if self.rate:
            self.rate.sleep()
        else:
            val=time.time() - self._last_process_time
            if val > self.intval:
              time.sleep(0)
            else:
              time.sleep(self.intval - val)
            self._last_process_time=time.time()
    # 
    #
    def get_time(self):
        try:
            return rospy.get_time()
        except:
            return time.time()
    #
    #
    def setInstanceName(self,name):
        self.name=name
        return True
    #
    #
    def getInstanceName(self):
        return self.name
    #
    #
    def onInitialize(self):
        return True

    #########################
    #  onActivated
    #
    def onActivated(self, ec_id):
        self.activated = True
        self.processActivated()
        self.resetTimer()
        #print (self.currentstate)
        return True

    #
    #  onDeactivated
    #
    def onDeactivated(self, ec_id):
        self.processDeactivated()
        self.processDeactivated('all')
        self.activated = False
        return True

    #
    #  onFinalize
    #
    def onFinalize(self):
        try:
            self.finalizeSEAT()
        except:
            pass
        return True

    #
    #  onShutdown
    #
    def onShutdown(self, ec_id):
        return True

    #
    #  onExecute
    #
    def onExecute(self, ec_id):
        if self.isTimeout() :
            res=self.processTimeout()
            if res :
                return True
            else:
                self._on_timeout = -1
        self.processExec()
        self.processExec('all')

        self.sleep()

        return True

#
#  eSEAT_Manager
class eSEAT_Node_Manager:
    def __init__(self, mlfile=None):
        self.comp = None
        self.run_as_daemon = False
        self.naming_format = ""
        self.viewer = None
        self.loop_flag = True
        self.main_thread=None
        self.stop_event=threading.Event()
        self.logflag=False

        if mlfile is None:
            opts, argv = self.parseArgs()
            if argv == -1:
                raise Exception("Error in __init__")
        else:
            opts, argv = self.parseArgs(False)
            self._scriptfile = mlfile

        if opts:
            self.run_as_daemon = opts.run_as_daemon
            self.naming_format = opts.naming_format
            self.logflag = opts.logflag

        if self.run_as_daemon :
            daemonize()

        self.comp=eSEAT_Node(self.logflag)
        self.comp.name=self.naming_format
        self.comp.manager=self

        #
        # Gui stdout
        if opts and opts.run_out_viewer:
            self.viewer = OutViewer()

    #
    #  Parse command line option...
    def parseArgs(self, flag=True):
        encoding = locale.getpreferredencoding()
        #sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
        #sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

        parser = utils.MyParser(version=__version__, usage="%prog [seatmlfile]",
                                description=__doc__)

        parser.add_option('-f', '--config-file', dest='config_file', type="string",
                            help='apply configuration file')

        parser.add_option('-n', '--name', dest='naming_format', type="string",
                            help='set naming format' )

        parser.add_option('-d', '--daemon', dest='run_as_daemon', action="store_true",
                            help='run as daemon' )

        parser.add_option('-v', '--viewer', dest='run_out_viewer', action="store_true",
                            help='create output window' )

        parser.add_option('-l', '--loginfo', dest='logflag', action="store_true",
                            help='display logger INFO' )

        try:
            opts, args = parser.parse_args()
        except (optparse.OptionError, e):
            print('OptionError:', e, file=sys.stderr)
            #sys.exit(1)
            return [None, -1]

        self._scriptfile = None
        if(len(args) > 0):
            self._scriptfile = args[0]

        if opts.naming_format:
           sys.argv.remove('-n')
           sys.argv.remove(opts.naming_format)

        if opts.run_as_daemon:
           sys.argv.remove('-d')

        if opts.run_out_viewer:
           sys.argv.remove('-v')

        if opts.logflag:
           sys.argv.remove('-l')

        if len(args) == 0 and flag:
            parser.error("wrong number of arguments")
            #sys.exit(1)
            return [None, -1]
        
        return [opts, sys.argv]

    #  Initialize the eSEAT-RTC
    #
    def initModule(self):
        if self._scriptfile :
            ret = self.comp.loadSEATML(self._scriptfile)
            if ret : raise Exception("Error in moduleInit")

    #
    #  Start Manager
    #
    def start(self):
        self.comp.setRate(self.comp.rate_hz)
        self.comp.startRosService()

        if (isinstance(self.comp, eSEAT_Gui) and self.comp.hasGUI() ) or self.viewer :
            #print("==== start with GUI ====")
            self.startLoop(True)

            # GUI part
            res = self.comp.startGuiLoop(self.viewer)
            if res == 0:
              self.exit()
            else:
              os._exit(1)
        else:
            #print("==== start ====")
            self.startLoop()

    #
    #
    def exit(self):
        try:
            self.stop()
            self.comp.exit_comp()
            self.comp.exit(True)
        except:
            pass
           
        if self.run_as_daemon:
          os._exit(1)
        else:
          try:
            sys.exit(0)
          except:
            pass
    #
    #
    def shutdown(self):
        self.exit()
    #
    #
    def stop(self):
        self.stop_event.set()
        if self.main_thread:
            self.main_thread.join()
    #
    #
    def mainloop(self):
        if self.comp :
            self.comp.resetTimer()
            while not self.stop_event.is_set():
                self.comp.onExecute(0)

        return True
    #
    #
    def startLoop(self, flag=False):
        if flag :
            self.main_thread = threading.Thread(target=self.mainloop)
            self.main_thread.start()
        else:
            self.mainloop()
#
#
#
def daemonize():
  try:
    pid=os.fork()
  except:
    print( "ERROR in fork1" )

  if pid > 0:
    os._exit(0)

  try:
    os.setsid()
  except:
    print( "ERROR in setsid" )

  try:
    pid=os.fork()
  except:
    print( "ERROR in fork2" )
  if pid > 0:
    os._exit(0)

#
#
def main_node(mlfile=None, daemon=False):
    try:
        import signal

        def sig_handler(signum, frame):
          seatmgr.exit() 

        signal.signal(signal.SIGINT, sig_handler)        
        if daemon : daemonize()

        seatmgr = eSEAT_Node_Manager(mlfile)
        seatmgr.initModule()
        seatmgr.start()
    except:
        traceback.print_exc()
        pass

    print ( "...Terminate." )

    seatmgr.exit()
