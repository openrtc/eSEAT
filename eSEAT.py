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

########
#  for OpenRTM-aist
import OpenRTM_aist
import omniORB
from RTC  import *

########################################
#  eSEAT_Core
#
execfile('eSEAT_Core.py')

###############################################################
#
__version__ = "0.3"

#########################################################################
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

#########################################################################
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
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self,
                        info, cdrdata, instantiateDataType(self._type))
        self._obj.onData(self._name, data)

#########################################################################
#
#  Class eSEAT (RTC)
#
#
class eSEAT(OpenRTM_aist.DataFlowComponentBase, eSEAT_Gui, eSEAT_Core):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        eSEAT_Core.__init__(self)
        eSEAT_Gui.__init__(self)

        self.manager = None
        self.activated=False

    ##########################################################
    #  E v e n t   H a n d l e r 
    #  onInitialize
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
        if self.webServer :
            self.webServer.terminate()
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
                elif isinstance(data, str):
                    if data :
                        data2 = parseData(data)
                        if data2 :
                            self.processOnDataIn(name, data2)
                        else :
                            if not self.processResult(name, data) :
                                self.processOnDataIn(name, data)
                else:
                    self.processOnDataIn(name, data)
            except:
                self._logger.RTC_ERROR(traceback.format_exc())
        else:
            pass

    ##############################################
    #
    #  RTC state control funtion
    #
    def activate(self):
      execContexts = self.get_owned_contexts()
      execContexts[0].activate_component(self.getObjRef())

    def deactivate(self):
      execContexts = self.get_owned_contexts()
      execContexts[0].deactivate_component(self.getObjRef())

    ##########################################################
    # Create PORT
    #
    # Create the InPort of RTC
    #
    def createInPort(self, name, type=TimedString):
        self._logger.RTC_INFO("create inport: " + name)
        self._data[name] = instantiateDataType(type)
        self._port[name] = OpenRTM_aist.InPort(name, self._data[name])
        self._port[name].addConnectorDataListener(
                                  OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                               eSEATDataListener(name, type, self))
        self.registerInPort(name, self._port[name])

    #
    # Create the OutPort of RTC
    #
    def createOutPort(self, name, type=TimedString):
        self._logger.RTC_INFO("create outport: " + name)
        self._data[name] = instantiateDataType(type)
        self._port[name] = OpenRTM_aist.OutPort(name, self._data[name],
                                   OpenRTM_aist.RingBuffer(8))
        self.registerOutPort(name, self._port[name])

    #
    # Create and Register DataPort of RTC
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
    # Disconnect all connections
    #
    def disconnectAll(self):
      for p in self._port.keys():
          if isinstance(self._port[p], OpenRTM_aist.PortBase) :
              self._port[p].disconnect_all()

    #######################
    #  Get DataType
    #
    def getDataType(self, s):
        if len(s) == 0         : return (TimedString, 0)
        seq = False

        if s[-3:] == "Seq"     : seq = True

        dtype = str
        if s.count("WString")  : dtype = unicode
        elif s.count("String") : dtype = str
        elif s.count("Float")  : dtype = float
        elif s.count("Double") : dtype = float
        elif s.count("Short")  : dtype = int
        elif s.count("Long")   : dtype = int
        elif s.count("Octet")  : dtype = int
        elif s.count("Char")   : dtype = str
        elif s.count("Boolean"): dtype = int
        else                   : dtype = eval("%s" % s)

        return (eval("%s" % s), dtype, seq)

    ############ End of RTC functions


#########################################################################
#
# eSEAT Manager ( RTC manager )
#
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

    #
    #  Parse command line option...
    def parseArgs(self):
        global opts
        encoding = locale.getpreferredencoding()
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

        parser = utils.MyParser(version=__version__, usage="%prog [seatmlfile]",
                                description=__doc__)

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

        if opts.naming_format:
           sys.argv.remove('-n')
           sys.argv.remove(opts.naming_format)

        if len(args) == 0:
            parser.error("wrong number of arguments")
            sys.exit(1)
        
        return sys.argv

    #
    #  Initialize the eSEAT-RTC
    #
    def moduleInit(self, manager):
        profile = OpenRTM_aist.Properties(defaults_str=eseat_spec)
        manager.registerFactory(profile, eSEAT, OpenRTM_aist.Delete)
        self.comp = manager.createComponent("eSEAT")
        self.comp.manager = manager

        if self._scriptfile :
            ret = self.comp.loadSEATML(self._scriptfile)

    #
    #  Start Manager
    #
    def start(self):
        if isinstance(self.comp, eSEAT_Gui) and self.comp.hasGUI() :
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

#########################################################################
#   F U N C T I O N S
#
#  DataType for CORBA
#
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
        arg = []
        for i in  range(4, len(desc), 2):
            attr = desc[i]
            attr_type = desc[i+1]
            arg.append(instantiateDataType(attr_type))
        return desc[1](*arg)
    return None

#########################################################################
#
#  M A I N 
#
if __name__=='__main__':
    seatmgr = eSEATManager()
    seat = seatmgr.comp
    seatmgr.start()
    sys.exit(1)

