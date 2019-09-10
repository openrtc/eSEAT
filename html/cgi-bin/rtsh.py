#! /usr/bin/python

import cgi
import subprocess
import sys
import os
import json
from rtutil import *

demo_mode = True

#########################


if __name__ == '__main__':
  try:
    #form = cgi.FieldStorage()
    form = eval(sys.argv[1])
    cmd = form['cmd']
  except:
    if len(sys.argv) > 1 :
      cmd = sys.argv[1]
    else:
      cmd = 'help'

  result = ""

  if cmd == 'rtact' :
    name = getValue(form, 'name1', 1)
    code, result = activateComponent(name)

  elif cmd == 'rtdeact' :
    name = getValue(form, 'name1', 1)
    code, result = deactivateComponent(name)

  elif cmd == 'rtreset' :
    name = getValue(form, 'name1', 1)
    code, result = resetComponent(name)

  elif cmd == 'rtstate' :
    name = getValue(form, 'name1', 1)
    code, result = getComponentState(name)

  elif cmd == 'rtexit' :
    name = getValue(form, 'name1', 1)
    code, result = exitComponent(name)
  elif cmd == 'delzombie' :
    hosts = getValue(form, 'hosts', 1)
    result = deleteZombieComponents(hosts)

  elif cmd == 'rtlist' or cmd == 'rtls' :
    host = getValue(form, 'host', 1)
    result = getComponentList(host)

  elif cmd == 'rtcat2' :
    cwd = getValue(form, 'cwd', 1)
    name = getValue(form, 'name', 2)
    print  >> sys.stderr, cwd, name
    result = ""
    result = catComponent2(cwd, name)
    result = json.dumps(result)

  elif cmd == 'rtcat' :
    name = getValue(form, 'name', 1 )
    print >> sys.stderr, "rtcat "+name
    result = catComponent(name)
    result = json.dumps(result)

  elif cmd == 'rtinfo' :
    name = getValue(form, 'name', 1 )
    result = catComponentInfo(name)
    result = json.dumps(result)

  elif cmd == 'rtconinfo' :
    name1 = getValue(form, 'name1', 1 )
    name2 = getValue(form, 'name2', 2 )
    result = getConnectionInfo(name1, name2)
    result = json.dumps(result)

  elif cmd == 'rtcon' :
    name1 = getValue(form, 'name1', 1)
    name2 = getValue(form, 'name2', 2)
    code, result = connectPorts(name1, name2)

  elif cmd == 'rtdis' :
    name1 = getValue(form, 'name1', 1)
    name2 = getValue(form, 'name2', 2)
    code, result = disconnectPorts(name1, name2)

  elif cmd == 'rtconf_list' :
    name = getValue(form, 'name', 1)
    result = getRtcConfigurationList(name)
    result = json.dumps(result)

  elif cmd == 'rtconf_get' :
    name = getValue(form, 'name', 1)
    conf = getValue(form, 'conf', 2)
    result = getRtcConfiguration(name, conf)

  elif cmd == 'rtconf_set' :
    name = getValue(form, 'name', 1)
    conf = getValue(form, 'conf', 2)
    value = getValue(form, 'value', 3)
    setname = getValue(form, 'setname', 4)

    result = setRtcConfiguration(name, conf, value, setname)

  elif cmd == 'rtconf_getSet' :
    name = getValue(form, 'name', 1)
    result = getRtcConfigurationSet(name)

  elif cmd == 'rtconf_getActSet' :
    name = getValue(form, 'name', 1)
    result = getActiveRtcConfigurationSet(name)

  elif cmd == 'rtconf_act' :
    name = getValue(form, 'name', 1)
    conf = getValue(form, 'conf', 2)
   
    result = activateRtcConfigurationSet(name, conf)

  elif cmd == 'rtcProfileList' :
    dirname='rtsprofiles'
    result = getRtcProfileList(dirname)

  elif cmd == 'getRtcProfile' :
    fname = getValue(form, 'name', 1)
    result = getFileContents("."+fname)
    print >> sys.stderr, result;

  else:
    result = "No such command: %s " % cmd

  printResult(result)
