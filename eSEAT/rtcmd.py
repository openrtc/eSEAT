#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''

RtcSh
Copyright (C) 2018
    Isao Hara,AIST,Japan
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
#import utils

try:
  import readline
except:
  pass
  
import cmd

#########################
from RTC import *
import CosNaming 
from CorbaNaming import *
import SDOPackage
from omniORB import CORBA,URI,any
import string

#
#
class Rtc_Sh:
  def __init__(self, orb=None, server_name='localhost'):
    if orb is None:
      self.orb = CORBA.ORB_init(sys.argv)
    else:
      self.orb=orb
    self.name=server_name
    self.naming=CorbaNaming(self.orb, self.name)
    self.maxlen=20
    self.object_list={}
    self.current_ctx=""
    #self.getRTObjectList()

  def resolveRTObject(self, name):
    try:
      if name.count(".rtc") == 0 : name = name+".rtc"
      ref=self.naming.resolveStr(name)
      ref._non_existent()
      return ref._narrow(RTObject)
    except:
      #traceback.print_exc()
      return None

  def unbind(self, name):
    self.naming.unbind(name)
    print("Unbind :", name)
    return

  def clearObjectList(self):
    self.object_list={}

  def getRTObjectList(self, name_context=None, parent=""):
    res=[]
    if name_context is None:
      name_context = self.naming._rootContext
    binds, bind_i = name_context.list(self.maxlen)
    for bind in binds:
      res = res + self.resolveBindings(bind, name_context, parent)

    if bind_i :
      tl = bind_i.next_n(self.maxlen)
      while tl[0]:
        for bind in tl[1] :
           res = res + self.resolveBindings(bind, name_conext, parent)
        tl = bind_i.next_n(self.maxlen)
    return res

  def resolveBindings(self, bind, name_context, parent):
    res = []
    prefix=parent

    if parent :
      prefix += "/"

    name = prefix + URI.nameToString(bind.binding_name)
    if bind.binding_type == CosNaming.nobject:
      if bind.binding_name[0].kind == "rtc":
        obj = name_context.resolve(bind.binding_name)
        try:
          obj._non_existent()
          obj = obj._narrow(RTObject)
          res = [[name, obj]]
          self.object_list[name] = obj
        except:
          obj = None
          res = [[name, obj]]
      else:
        pass
        #self.object_list[name] = None
    else:
      ctx = name_context.resolve(bind.binding_name)
      ctx = ctx._narrow(CosNaming.NamingContext)
      parent = name
      res = self.getRTObjectList( ctx, parent)
    return res

  def refreshObjectList(self):
    self.object_list = {}
    return self.getRTObjectList()

  def getPorts(self, name):
    res=[]
    if name.count(".rtc") == 0 : name = name+".rtc"
    if not (name in self.object_list):
      self.refreshObjectList()

    if name in self.object_list:
      port_ref = self.object_list[name].get_ports()
      for p in port_ref:
        pp = p.get_port_profile()
        pprof =  nvlist2dict(pp.properties)
        if pp.interfaces:
          ifp=pp.interfaces[0]
          pprof['interface_name'] = ifp.instance_name
          pprof['interface_type_name'] = ifp.type_name
          pprof['interface_polarity'] = ifp.polarity
        res.append( (pp.name, pprof))
    else:
      print("No such RTC:", name)
    return res

  def getPortRef(self, name, port):
    res=[]
    if name in self.object_list:
      self.refreshObjectList()

    if name.count(".rtc") == 0 : name = name+".rtc"

    if name in self.object_list:
      port_ref = self.object_list[name].get_ports()
      for p in port_ref:
        pp = p.get_port_profile()
        if port == pp.name.split('.')[-1]:
          return p
    else:
      print("No such port:", name, ":", port)
    return None

  def getConnectors(self, name, port):
    port_ref=self.getPortRef(name, port)
    if port_ref:
      cons = port_ref.get_connector_profiles()
      return cons
    return None
 
  def getConnectionInfo(self, con):
    ports = [(con.ports[0].get_port_profile()).name, (con.ports[1].get_port_profile()).name]
    res={'name': con.name, 'ports': ports, 'id': con.connector_id }
    return res

  def getConnections(self, name, port):
    res = []
    cons = self.getConnectors(name, port)
    if cons:
      for c in cons:
        res.append(self.getConnectionInfo(c))
    return res

  def find_connection(self, portname1, portname2):
    try:
      name1, port1 = portname1.split(":")
      name2, port2 = portname2.split(":")

      p1=self.getPortRef(name1, port1)
      p2=self.getPortRef(name2, port2)

      cons  = self.getConnectors(name1, port1)
      cons2 = self.getConnectors(name2, port2)
      if cons and  cons2 :
        for c in cons:
          for c2 in cons2:
            if c.connector_id == c2.connector_id:
              return c
      return False
    except:
      traceback.print_exc()
      return None

  def connect(self, portname1, portname2, service=False):
    if service:
      con_prof = {'port.port_type':'CorbaPort' }
    else:
      con_prof={'dataport.dataflow_type':'push',
              'dataport.interface_type':'corba_cdr' ,
              'dataport.subscription_type':'flush'}

    chk = self.find_connection(portname1, portname2)
    if chk is None:
        return None
    if chk :
       print("Conntction exists:", chk.connector_id)
       return 
    try:
      name1, port1 = portname1.split(":")
      name2, port2 = portname2.split(":")
      p1=self.getPortRef(name1, port1)
      p2=self.getPortRef(name2, port2)
      if p1 and p2:
        name='_'.join([name1, port1, name2, port2])
        prof_req=ConnectorProfile(name, "", [p1, p2], dict2nvlist(con_prof))
        res, prof=p1.connect(prof_req)
      else:
        res="Error in connect"
    except:
      res="Error"
    print(res)
    return

  def disconnect(self, portname1, portname2):
    try:
      con=self.find_connection(portname1, portname2)
      if con is None or not con:
        print("No such connrction:", portname1, portname2)
       
      con.ports[0].disconnect(con.connector_id)
      print("Sucess to disconnect:", portname1, portname2)
    except:
      print("Fail to disconnect:", portname1, portname2)

  def getEC(self, name):
    obj=self.resolveRTObject(name)
    if obj :
      ec=obj.get_owned_contexts()[0]
      return ec
    else:
      return None
      
  def activate(self, name):
    res=None
    obj=self.resolveRTObject(name)
    if obj :
      ec=obj.get_owned_contexts()[0]
      res=ec.activate_component(obj)
    return res
      
  def deactivate(self, name):
    res=None
    obj=self.resolveRTObject(name)
    if obj :
      ec=obj.get_owned_contexts()[0]
      res=ec.deactivate_component(obj)
    return res

  def get_component_state(self, name):
    stat=None
    obj=self.resolveRTObject(name)
    if obj:
      ec=obj.get_owned_contexts()[0]
      stat=ec.get_component_state(obj)
    return stat

  def terminate(self, name):
    obj=self.resolveRTObject(name)
    if obj:
      obj.exit()
    return None

#
#
class RtCmd(cmd.Cmd):
  #intro="Welcome to RtCmd"
  prompt="=> "
  file=None

  def __init__(self, rtsh=None, once=False):
    cmd.Cmd.__init__(self)
    if rtsh is None:
      try:
        self.rtsh=Rtc_Sh()
        self.rtsh.getRTObjectList()
      except:
        print("Error: NameService not found.")
        os._exit(-1)
    else:
      self.rtsh=rtsh
    self.onecycle=once
    self.end=False

  def do_echo(self, arg):
    print("Echo:", arg)
    return self.onecycle

  def do_list(self, arg):
    num=0
    argv=arg.split()
    l_flag=False

    if len(argv) > 0:
      if argv[0] == '-r':
        self.rtsh.refreshRTObjectList()
      elif argv[0] == '-l':
        l_flag=True
      else:
        print("Invalid option")
  
    print("===== RTCs =====")
    res = self.rtsh.getRTObjectList()
    for n in res:
      num += 1
      if n[1]:
        stat=self.rtsh.get_component_state(n[0])
        if stat == ACTIVE_STATE:
          comp_name = n[0]+"*"
        else:
          comp_name = n[0]
         
        print(num, ":", comp_name)
        if l_flag:
          ports=self.rtsh.getPorts(n[0])
          for pp in ports:
            pname=pp[0].split('.')[1]
            cons=self.rtsh.getConnectors(n[0], pname)
            typ=pp[1]['port.port_type']
            if cons:
              con_str="\n        +- "+str([ c.name for c in cons])
            else:
              con_str=""

            if typ == "DataInPort":
              d_typ=pp[1]['dataport.data_type'].split(":")[1]
              port_str = pname+"("+d_typ+")"
              print("     <-", port_str, con_str)

            elif typ == "DataOutPort":
              d_typ=pp[1]['dataport.data_type'].split(":")[1]
              port_str = pname+"("+d_typ+")"
              print("     ->", port_str, con_str)

            elif typ == "CorbaPort":
              d_typ=pp[1]['interface_type_name']
              if_dir=pp[1]['interface_polarity']
              port_str = pname+"("+d_typ+")"
              if if_dir == PROVIDED:
                print("     =o", port_str, con_str)

              else:  # REQUIRED
                print("     =C", port_str, con_str)

            else:
              port_str = pname
              print("     --", port_str)

      else:
        print(num, ":[", n[0], "]")
    print("")
    return self.onecycle

  def compl_object_name(self, text, line, begind, endidx):
    names=list(self.rtsh.object_list.keys())
    if not text:
      completions=names[:]
    else:
      completions= [ n for n in names if n.startswith(text) ]
    return completions 

  def compl_port_name(self, text, line, begind, endidx):
    try:
      objname, pname=text.split(':',1)
      if objname:
        ports=self.rtsh.getPorts(objname)
        pnames=[]
        for pp in ports:
          pnames.append(pp[0].split('.')[1])
        if not pname:
          completions=pnames[:]
        else:
          completions= [ n for n in pnames if n.startswith(pname) ]
      else:
        completions=[]
    except:
      traceback.print_exc()
      completions=[]
    return [ objname+":"+p for p in completions]
    #return completions

  def do_get_ports(self, arg):
    num=0
    ports = self.rtsh.getPorts(arg)
    print("====== Ports(%s) ======" % arg)
    for pp in ports:
      num += 1
      print(num, ":", pp[0].split('.')[1])
      for k in pp[1]:
         print("   ", k,":", pp[1][k])
            
    print("")
    return self.onecycle

  def complete_get_ports(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_get_connectors(self, arg):
    try:
      name, port = arg.split(":")
      cons=self.rtsh.getConnectors(name, port)
      if cons is None:
        print("   No connectors")
      else:
        for con in cons:
          info=self.rtsh.getConnectionInfo(con)
          print("   ", info['name'],":", info['ports'][0],"==",info['ports'][1])
    except:
      print("Error in get_connectors:", arg)

  def complete_get_connectors(self, text, line, begind, endidx):
    args=line.split()
    if line[endidx-1] != ' ' and args[-1].find(':') > 0 :
      text=args[-1]
      return self.compl_port_name(text, line, begind, endidx)
    else:
      return self.compl_object_name(text, line, begind, endidx)

  def do_get_connection(self, arg):
    argv=arg.split()
    if len(argv) > 1:
      cons = self.rtsh.getConnections(argv[0], argv[1])
      num=0
      if cons:
        for x in cons:
          print(num, ":", cons)
          num += 1
      else:
        print("No connection")
    else:
      print("get_connection comp1:p comp2:p")
    return self.onecycle

  def complete_get_connection(self, text, line, begind, endidx):
    args=line.split()
    if line[endidx-1] != ' ' and args[-1].find(':') > 0 :
      text=args[-1]
      return self.compl_port_name(text, line, begind, endidx)
    else:
      return self.compl_object_name(text, line, begind, endidx)

  def do_disconnect(self, arg):
    argv=arg.split()
    if len(argv) > 1:
      self.rtsh.disconnect(argv[0], argv[1])
    else:
      print("disconnect comp1:p comp2:p")
    return self.onecycle

  def complete_disconnect(self, text, line, begind, endidx):
    args=line.split()
    if line[endidx-1] != ' ' and args[-1].find(':') > 0 :
      text=args[-1]
      return self.compl_port_name(text, line, begind, endidx)
    else:
      return self.compl_object_name(text, line, begind, endidx)

  def do_connect(self, arg):
    argv=arg.split()
    if len(argv) > 1:
      self.rtsh.connect(argv[0], argv[1])
    else:
      print("connect comp1:p comp2:p")
    return self.onecycle

  def complete_connect(self, text, line, begind, endidx):
    args=line.split()
    if line[endidx-1] != ' ' and args[-1].find(':') > 0 :
      text=args[-1]
      return self.compl_port_name(text, line, begind, endidx)
    else:
      return self.compl_object_name(text, line, begind, endidx)

  def do_activate(self, arg):
    argv=arg.split()
    for v in argv:
      self.rtsh.activate(v)
    return self.onecycle

  def complete_activate(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_deactivate(self, arg):
    argv=arg.split()
    for v in argv:
      self.rtsh.deactivate(v)
    return self.onecycle

  def complete_deactivate(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_get_state(self, arg):
    stat=self.rtsh.get_component_state(arg)
    print("State:", arg,":", stat)
    return self.onecycle

  def complete_get_state(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_terminate(self, arg):
    argv=arg.split()
    for v in argv:
      self.rtsh.terminate(v)
    return self.onecycle

  def complete_terminate(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_unbind(self, arg):
    argv=arg.split()
    for v in argv:
      self.rtsh.unbind(v)
    return self.onecycle

  def complete_unbind(self, text, line, begind, endidx):
    return self.compl_object_name(text, line, begind, endidx)

  def do_bye(self, arg):
    print('...BYE')
    self.close()
    self.end=True
    return True

  # ----- record and playback -----
  def do_record(self, arg):
    self.file = open(arg, 'w')

  def do_playback(self, arg):
    self.close()
    with open(arg) as f:
      self.cmdqueue.extend(f.read().splitlines())

  def precmd(self, line):
    #line = line.lower()
    if self.file and 'playback' not in line:
      print(line, file=self.file)
    return line

  def close(self):
    if self.file:
      self.file.close()
      self.file = None

  def emptyline(self):
    return

  def completenames(self, text, *ignored):
    dotext = 'do_'+text
    retval = [a[3:]+" " for a in self.get_names() if a.startswith(dotext)]
    return retval

def nvlist2dict(nvlist):
  res={}
  for v in nvlist:
    res[v.name] = v.value.value()
  return res

def dict2nvlist(dict) :
  import omniORB.any
  rslt = []
  for tmp in dict.keys() :
    rslt.append(SDOPackage.NameValue(tmp, omniORB.any.to_any(dict[tmp])))
  return rslt

def main():
  if len(sys.argv) > 1:
    return RtCmd().onecmd(" ".join(sys.argv[1:]))
  else:
    RtCmd().cmdloop(intro="Welcome to RtCmd")


#########################################################################
#
#  M A I N 
#
if __name__=='__main__':
    main()
