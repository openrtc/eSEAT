#! python.exe

import cgi
import subprocess
import sys
import os
import rtctree
import rtctree.path
import rtctree.tree
import json
import time

"""
  Global variables
"""
__ORB__ = None
demo_mode = False


"""
 Formart a component node for NSView
"""
def format_node(node, flag):
  if flag==1 :
    return """ "*%s" """ % node.name
  elif flag==2 :
    return """ "#%s" """ % node.name
  else :
    return """ "%s" """ % node.name

"""
 Fomat a context node forn NSView
"""
def format_context(node):
  return  """ "folder": "%s" """ % node.name

"""
  Format NSView
"""
def format_nsview_json(tree, node):
  result = ""
  res = []
  try:
    chnode = node.children
    count = 0
    for x in chnode :
      if count > 0:
        result += ","
      path, port = rtctree.path.parse_path(x.full_path_str)
      res.append(x)
      if tree.is_directory(path) :
        val = format_context(x)
        val2 = format_nsview_json(tree,x)
        result += """{ %s, "components" : [ %s]}""" % (val, val2)
      else:
        flag = 0
        if tree.is_zombie(path) : flag = 1
        if tree.is_unknown(path) : flag = 2
        val = format_node(x, flag)
        result += val
      count += 1
  except:
    pass

  return result

"""
  Format NSView for demo.
"""
def format_dir_json(dirname):
  res = []
  filelist = os.listdir(dirname)
  for f in filelist :
    p = "%s\%s" % (dirname, f)
    if os.path.isdir(p) :
      val = format_dir_json(p)
      res.append( """{ "folder" : "%s", "components": [%s] }""" % (f, val) )
    else:
      res.append( """ "%s" """ % f )
  return ",".join(res)

"""
  Parse a data_type of a dataport
"""
def getDataType(tt):
  val = tt.split(":")
  if val[0] != 'IDL' or val[2] != '1.0':
    return tt
  return val[1].replace('/', '::')

"""
  Format port data of a component
"""
def format_port_info(port):
  result = port.name

  props = port.properties
  porttype = props['port.port_type']

  if porttype == 'DataOutPort' or porttype == 'DataInPort':
    #datatype= getDataType(props['dataport.data_type'])
    datatype= props['dataport.data_type']
    result += """(%s;%s)""" % (porttype, datatype)
  else:
    info=[]
    for x in port.interfaces :
      info.append( "%s|%s|%d" % (x.instance_name , x.type_name,  x.polarity) )

    info_str = "#".join(info)
    result += """(%s;%s)""" % (porttype, info_str)

  return result

"""
"""
def find_composite_comp(tree, member, inst_name):
  def get_fp(mgr, args):
    for c in mgr.components:
      if c.instance_name == inst_name:
        return c.full_path_str
    return None
  def is_correct_mgr(node):
    has_member = False
    has_inst_name = False
    for c in node.components:
      if c.instance_name == inst_name:
        has_inst_name = True
      elif c.instance_name == member.instance_name:
        has_member = True
    return has_member and has_inst_name
  return tree.iterate(get_fp, filter=['is_manager', is_correct_mgr])

"""
"""
def get_composite_properties(tree, comp):
  result=[]
  for o in comp.organizations:
    res={}
    if not o.sdo_id:
      sdo_id = "Unknown"
    else:
      sdo_id = o.sdo_id

    res['Composition_ID'] = sdo_id 
    res['ID'] = o.org_id 
    for m in o.members:
      c_path = find_composite_comp(tree, comp, m)
      if c_path:
        res['Member'] = c_path[0]
      else:
        res['Member'] = 'Unknown'
    result.append(res)
  return result

"""
"""
def get_composite_member_properties(tree, comp):
  result=[]
  for po in comp.parent_orgs:
    res={}
    if not po.sdo_id:
      sdo_id = "Unknown"
    else:
      sdo_id = po.sdo_id
    res['Parent_ID'] = sdo_id 
    res['ID'] = po.org_id 
    composition_path = find_composite_comp(tree, comp, po.sdo_id)
    if composition_path:
      res['Path'] = composition_path[0]
    else:
      res['Path'] = 'Unknown'

    result.append(res) 
  return result

"""
"""
def get_ecs_properties(ecs):
  result=[]
  for ec in ecs:
    res={}
    res['Handle'] = ec.handle
    res['State'] = ec.running_as_string(add_colour=False)
    res['Kind'] = ec.kind_as_string(add_colour=False)
    res['Rate'] = ec.rate
    if ec.owner_name:
      res['Owner'] = ec.owner_name

    if ec.participant_names:
      res['Participants'] = ec.participant_names

    if ec.properties:
      res['ExtraProperties'] = ec.properties
    result.append(res)
  return result

"""
"""
def get_ports_properties(comp, ports):
  result=[]
  for p in ports:
    res = get_port_properties(comp, p)
    result.append(res)

  return result

"""
"""
def get_port_properties(comp, p):
  res = {}
  res['Name'] = p.name
  res['Type'] = p.porttype
  res['Properties'] = p.properties

  if p.porttype == 'CorbaPort' and p.interfaces:
    res['Interfaces'] = []
    for intf in p.interfaces:
      res_intf = {}
      res_intf['InstanceName'] = intf.instance_name
      res_intf['TypeName'] = intf.type_name
      res_intf['Polarity'] = intf.polarity_as_string(add_colour=False)
    res['Interfaces'].append(res_intf)

  res['Connections'] = []
  for conn in p.connections:
    res_conn = {}
    dest_ports = []

    for name,dp in conn.ports:
      if not dp:
        dest_ports.append(name)
      elif not comp.get_port_by_ref(dp.object) :
        dest_ports.append(name)

    if dest_ports :
      res_conn['DestPorts'] = dest_ports
      res_conn['Name'] = conn.name
      res_conn['ID'] = conn.id
      keys = [k for k in conn.properties.keys() \
              if not k.endswith('inport_ref') \
              if not k.endswith('inport_ior')]
      for key in keys:
        if isinstance(conn.properties[key], str) :
          res_conn[key] = conn.properties[key]

      res['Connections'].append(res_conn)

  return res

"""
"""
def get_component_profile(tree, comp):
  res = ""
  profiles={}
  profiles['Name'] = comp.name
  profiles['State'] = comp.get_state_string(add_colour=False)
  profiles['Category'] = comp.category
  profiles['Description'] = comp.description
  profiles['InstanceName'] = comp.instance_name
  profiles['TypeName'] = comp.type_name
  profiles['Vendor'] = comp.vendor


  if comp.parent:
    profiles['Parent'] = comp.parent_object

  if comp.is_composite:
    if comp.is_composite_member:
      profiles['Type'] = 'Composite composite member'
    else:
      profiles['Type'] = 'Composite'
    profiles['Composite'] = get_composite_properties(tree, comp)

  elif comp.is_composite_member:
    profiles['Type'] = 'Monolithic composit member'
    profiles['CompositeMember'] = get_composite_member_properties(tree, comp)
  else:
    profiles['Type'] = 'Monolithic'

  profiles['ExtraProperties'] = comp.properties
  profiles['ExecutionContext'] = get_ecs_properties(comp.owned_ecs)
  profiles['Ports'] = get_ports_properties(comp, comp.ports)


  conf_sets = comp.conf_sets
  if conf_sets :
    profiles['ConfigSet'] = [k for k in conf_sets.keys() if not is_hidden(k) ]
    try:
      profiles['ConfigParams'] = conf_sets[comp.active_conf_set_name].data.keys()
    except:
      profiles['ConfigParams'] = []

  profiles['ActiveConfig'] = comp.active_conf_set_name 

  #print >> sys.stderr, profiles
  return profiles

"""
"""
def get_manager_profile(tree, comp):
  res = {}
  res['Name'] = comp.profile['name']
  res['InstanceName'] = comp.profile['instance_name']
  res['ProcessID'] = comp.profile['pid']
  res['NamingFormat'] = comp.profile['naming_formats']
  res['RefstringPath'] = comp.profile['refstring_path']
  res['ComponentPrecreate'] = comp.profile['components.precreate']

  res['LoadPath'] = comp.profile['modules.load_path']
  res['ConfigPath'] = comp.profile['modules.config_path']
  res['Preload'] = comp.profile['modules.preload']
  res['InitFunctionPrefix'] = comp.profile['modules.init_func_prefix']
  res['DownloadAllowed'] = comp.profile['modules.download_allowed']
  res['AbsolutePathAllowed'] = comp.profile['modules.abs_path_allowed']

  res['OsVersion'] = comp.profile['os.version']
  res['OsArchitecture'] = comp.profile['os.arch']
  res['OsRelease'] = comp.profile['os.release']
  res['OsHostname'] = comp.profile['os.hostname']
  res['OsName'] = comp.profile['os.name']

  res['LoadedModules'] = []
  for lm in comp.loaded_modules:
    res_lm = {}
    res_lm['Filepath'] = lm['file_path']
    res['LoadedModules'].append(res_lm)
  
  res['LoadableModules'] = []
  for lm in comp.loadable_modules:
    res_lm = {}
    res_lm['Filepath'] = lm['module_file_path']
    res['LoadableModules'].append(res_lm)

  return res

"""
"""
def get_or(tree,comp):
  res = ""
  res = get_component_profile(tree, comp)
  
  return res

"""
"""
def getFileContent(fname):
  global demo_mode
  res = ""
  if demo_mode and os.path.exists(fname) and os.path.isfile(fname):
    f = open(fname, 'r')
    contents = ""
    for line in f:
      contents += line
    f.close()
    res = "".join(contents.split("\n"))

  return res

"""
"""
def getFileContents(fname):
  res = ""
  if os.path.exists(fname) and os.path.isfile(fname):
    f = open(fname, 'r')
    contents = ""
    for line in f:
      contents += line
    f.close()
  return contents

"""
"""
def getPortInfoFromFile(filename):
  global demo_mode
  if demo_mode :
    info = getFileContent(filename)
    comp = eval(info)

    res = []
    for  port in comp['Ports'] :
      if port['Type'] == 'CorbaPort' :
        interfaces = port['Interfaces']
        info =[]
        for prop in interfaces:
          info.append( """%s|%s|%s""" % (prop['InstanceName'],prop['TypeName'],prop['Polarity']))
        propsinfo = "#".join(info)
      else :
        prop = port['Properties']
        propsinfo = prop['dataport.data_type']

      res.append("%s(%s;%s)" % (port['Name'] , port['Type'], propsinfo))

    result = ",".join(res)
  else:
    result = "unknown"
  return """ "ports": "%s" """ % result

"""
"""
def getRtcInfoFromFile(cwd, name):
  global demo_mode
  if demo_mode :
    ndir = cwd.split('/')
    dirname = "\\".join(ndir[2:])
    demoroot = os.getenv('DEMO_ROOT')
    if not demoroot:
      demoroot = """.\demo"""
    filename = """%s\%s\%s""" % (demoroot, dirname, name)

    result = getFileContent(filename)
    return eval(result)
  else:
    return ""

"""
"""
def getRtcPortFromFile(cwd, name):
  global demo_mode
  if demo_mode :
    ndir = cwd.split('/')
    dirname = "\\".join(ndir[2:])
    demoroot = os.getenv('DEMO_ROOT')
    if not demoroot:
      demoroot = """.\demo"""
    filename = """%s\%s\%s""" % (demoroot, dirname, name)
  
    if os.path.exists(filename) and os.path.isfile(filename):
      portinfo = getPortInfoFromFile(filename)
      result = """{"name": "%s", %s, "context" : "%s/"}""" % (name, portinfo, cwd)
    else:
      result = """{"name": "error", "ports": "", "msg" : "Invalid Component name!!", "context" : "%s/"}""" % cwd
  else:
    result = """{"name": "error", "ports": "", "msg" : "No such a component", "context" : "%s/"}""" % cwd

  return result


def getRtcTree(servers=None, paths=None, orb='global'):
  global __ORB__

  if paths : f= [paths]
  else: f=[]

  if orb=='global': orb=__ORB__
  tree = rtctree.tree.RTCTree(servers=servers, paths=paths, filter=f, orb=orb)

  if tree :
    if not __ORB__ : __ORB__ = tree.orb

  return tree

"""
"""
def getComponent(cwd, name=None, tree=None, orb='global'):
  try:
    path = cwd.split("/")
    if not path[-1] :
      path.pop()
      cwd = '/'.join(path)

    rootpath, port = rtctree.path.parse_path(cwd)

    if not tree:
      tree = getRtcTree(paths=rootpath, orb=orb)

    if name :
      rootpath.append(name)

    comp = tree.get_node(rootpath)
  except:
    tree = None
    comp = None
    port = None

  return tree, comp, port

"""
"""
def findConnectionId(port1, port2):
  port1_all_conns = port1.connections
  port2_all_conns = port2.connections

  for c2 in port2_all_conns:
    for c1 in port1_all_conns:
      if c1.id == c2.id :
        return c1.id

  return None

"""
"""
def getConnectedPorts(name):
  try:
    tree, comp, port = getComponent(name, None)
    port_objs = comp.connected_ports

  except:
    port_objs = None
    pass

  return tree,comp, port_objs


"""
"""
def getComponentPort(name, tree=None):
  try:
    tree, comp, port = getComponent(name, None, tree)
    port_obj = comp.get_port_by_name(port)
  except:
    port_obj = None
    pass

  return tree,comp, port_obj

"""
"""
def activateComponent(name, ec_index=0):
  code = 0
  tree, comp, port = getComponent(name)

  if tree and comp :
    comp.activate_in_ec(ec_index)
    time.sleep(0.5)
    state = comp.get_state_string(add_colour=False)
    result ="""{"name" :  "%s", "result" : "%s" }""" % (name, state)
    code = 1
  else:
    result ="""{"name" :  "%s", "result" : "Fail" }""" % name

  return code, result

"""
"""
def deactivateComponent(name, ec_index=0):
  code = 0
  tree, comp, port = getComponent(name)

  if tree and comp :
    comp.deactivate_in_ec(ec_index)
    result ="""{"name" :  "%s", "result" : "Success" }""" % name
    code = 1
  else:
    result ="""{"name" :  "%s", "result" : "Fail" }""" % name

  return code, result

"""
"""
def resetComponent(name, ec_index=0):
  code = 0
  tree, comp, port = getComponent(name)

  if tree and comp :
    comp.reset_in_ec(ec_index)
    result ="""{"name" :  "%s", "result" : "Success" }""" % name
    code = 1
  else:
    result ="""{"name" :  "%s", "result" : "Fail" }""" % name

  return code, result

"""
"""
def getComponentState(name, ec_index=0):
  code = 0
  tree, comp, port = getComponent(name)

  if tree and comp :
    state = comp.get_state_string(add_colour=False)
    result ="""{"name" :  "%s", "result" : "%s" }""" % (name, state)
    code = 1
  else:
    result ="""{"name" :  "%s", "result" : "Fail" }""" % name

  return code, result

"""
"""
def exitComponent(name):
  code = 0
  tree, comp, port = getComponent(name)

  if tree and comp :
    try:
      comp.exit()
      result ="""{"name" :  "%s", "result" : "Success" }""" % name
    except:
      result ="""{"name" :  "%s", "result" : "Fail" }""" % name
      pass
  else:
    result ="""{"name" :  "%s", "result" : "No such a component" }""" % name
    code = -1

  return code, result

"""
"""
def deleteZombieComponents(hosts):
  res = delete_all_zombies(hosts)

  result = ""

  if res == False:
    result = "Fail"
  else:
    for x in res:
      result += "Delete %s\n" % x
    result += "OK"

  return result

"""
"""
def getComponentList(host):
  if not host : host = ""
  roothost = "/"+host
  tree, root, port = getComponent(roothost)

  if tree and root :
    val = format_nsview_json(tree, root)
#    result = """{ "hostname": "%s", "components": [ %s ]} """ % (host, val)
  else:
    dirname = os.getenv('DEMO_ROOT')
    if not dirname : dirname = "demo"
    try:
      val = format_dir_json(dirname)
    except:
      val = """ "No such component" """

  result = """{ "hostname":"%s", "components": [ %s] }""" % (host, val)
  return result

"""
"""
def getConnectionInfo(name1, name2):
  result = {}

  try:
    p1 = catComponentInfo(name1)
    p2 = catComponentInfo(name2)

    connections1 = p1['PortInfo']['Connections']
    connections2 = p2['PortInfo']['Connections']

  except:
    print >>sys.stderr, "ERROR in getConnectionInfo"
    return result

  for con1 in  connections1 :
    for con2 in  connections2 :
      if con1['ID'] == con2['ID'] :
         result = con1
         if p1['PortInfo']['Type'] == 'CorbaPort':
           result['ConnectionType']='ServicePort'
         else:
           result['ConnectionType']='DataPort'
         break
  return result;
"""
"""
def catComponentInfo(name):
  tree, comp, port = getComponent(name,orb=None)
  result = {}

  if tree and comp :
    rootpath, port = rtctree.path.parse_path(name)

    if port :
      if comp.is_component :
        p = comp.get_port_by_name(port)
        if p :
          result['PortInfo'] = get_port_properties(comp, p)
    else:
      if comp.is_component :
        result = get_component_profile(tree,comp)
        result['PathUrl'] = name
      elif comp.is_manager :
        result = get_manager_profile(tree,comp)
        result['PathUrl'] = name
      elif comp.is_zombie:
        result = {'Name': comp.name, 'State': 'Zombie', 'Type': 'Zombie' }
        result['PathUrl'] = name
      else:
        result = "" 
  else:
    result = """{"name": "%s", "ports": "", "msg" : "No name!!"}""" % name

  return result


"""
"""
def catComponent(name):
  path = name.split("/")
  try:
    pos = path[-1].index(".rtc")
  except:
    return """{"name": "%s", "ports": "", "msg" : "No name!!"}""" % name
  
  rtcname = path.pop()
  cwd = "/".join(path)

  return catComponent2(cwd, rtcname)

"""
"""
def catComponent2(cwd, name):
  if not name :
   result= """{"name": "error", "ports": "", "msg" : "No name!!"}"""

  else:
    tree, comp, port = getComponent(cwd, name)

    if tree and comp :
      rootpath, port = rtctree.path.parse_path(cwd)
      if port :
        if comp.is_component :
          p = comp.get_port_by_name(port)
          if p :
            result['PortInfo'] = get_port_properties(comp, p)
      else:
        if comp.is_component :
          result = get_component_profile(tree,comp)
          result['PathUrl'] = cwd
        elif comp.is_manager :
          result = get_manager_profile(tree,comp)
          result['PathUrl'] = cwd
        elif comp.is_zombie:
          result = {'Name': comp.name, 'State': 'Zombie', 'Type': 'Zombie' }
          result['PathUrl'] = cwd
        else:
          result = "" 
    else:
      result= """{"name": "error", "ports": "", "msg" : "No name!!"}"""
      #result = getRtcInfoFromFile(cwd, name)
      #result['PathUrl'] = cwd

    return result

"""
"""
def getComponentInfo(cwd, name):
  if not name :
    result= """{"name": "error", "ports": "", "msg" : "No name....!!"}"""

  else:
    tree, comp, port = getComponent(cwd, name)

    if tree and comp :
      ports = comp.ports

      portInfo =""
      for x in ports:
        if portInfo != "" : portInfo +=","
        portInfo += format_port_info(x)

      ecs = get_ecs_properties(comp.owned_ecs)
      status = ecs[0]['State']
      PortsInfo = get_ports_properties(comp, comp.ports)

      result = """{"name": "%s", "ports" : "%s", "context" : "%s/"}""" % (name, portInfo, cwd)
    else:
      result = getRtcPortFromFile(cwd, name)

  return result

"""
"""
def connectPorts(name1, name2):
  if not name1 or  not name2:
    result =  '{"name": "error", "ports": "", "msg" : "Invalid Component name!!"}'
    code = -2

  else:
    try:
      tree1, comp1, port_obj1 = getComponentPort(name1)
      tree2, comp2, port_obj2 = getComponentPort(name2)

      conn_id = findConnectionId(port_obj1, port_obj2)

      if conn_id :
        result = "Connection %s:%s and %s:%s already exists. " % (comp1.name, port1, comp2.name, port2)
        code = 0
      else:
        profile =""
        port_obj1.connect([port_obj2] )
        #result = "Connected:  %s %s" % (name1, name2)
        result = "Connected:  "
        code = 1
    except Exception, e:
      result = "Error in connectPorts"
      code=-1

  return code,result


"""
"""
def disconnectPorts(name1, name2):
#  global __ORB__
  if not name1 or  not name2:
    result =  '{"name": "error", "ports": "", "msg" : "Invalid Component name!!"}'
    code = -2

  else:
    try:
      tree1, comp1, port_obj1 = getComponentPort(name1)
      tree2, comp2, port_obj2 = getComponentPort(name2)
      conn_id = findConnectionId(port_obj1, port_obj2)

      if conn_id :
        pobj = port_obj1.get_connection_by_id(conn_id)
        pobj.disconnect()
        result = "Disonnected:  %s and  %s" % (port_obj1.name, port_obj2.name)
        code = 1
      else: 
        result = "No such a connection."
        code = 0

    except Exception, e:
      result = "Error in disconnectPorts"
      code = -1

  return code,result

"""
"""
def delete_all_zombies(hosts='localhost'):
  hostnames = hosts.split(',')

  tree = getRtcTree(servers=hostnames)

  if not tree:
    return False

  def del_zombie(node, args):
    try:
      name = node.name
      node.parent.unbind(node.name)
      return name
    except Exception, e:
      traceback.print_exc()
      print >>sys.stderr, '{0}: {1}'.format(sys.argv[0], e)

  return tree.iterate(del_zombie, filter=['is_zombie'])


"""
"""
def is_hidden(name):
    hidden_prefix = '__'
    hidden_suffix = '__'
    return name.startswith(hidden_prefix) and name.endswith(hidden_suffix)

def getRtcConfigurationList(name):
  tree, comp, port = getComponent(name)

#  result =  '{"name": "error", "config": "", "msg" : "Invalid Component name!!"}'

  conf_sets = comp.conf_sets
  print conf_sets.keys()

  active_conf = comp.active_conf_set_name 

  result = []
  set_keys = [k for k in conf_sets.keys() if not is_hidden(k) or all]
  
  set_keys.sort()
  for set_name in set_keys:
    if set_name == active_conf :
      result = conf_sets[set_name].data
      params = conf_sets[set_name].data.keys()
      for param in params:
        print """ %s   %s """ % (param, conf_sets[set_name].data[param])

  return result


"""
"""
def getRtcConfiguration(name, conf_name):
  tree, comp, port = getComponent(name)
#  result =  '{"name": "error", "config": "", "msg" : "Invalid Component name!!"}'
  conf_sets = comp.conf_sets
  active_conf = comp.active_conf_set_name 
  result = conf_sets[active_conf].data[conf_name]

  return result


"""
"""
def setRtcConfiguration(name, conf_name, val, setname=None):
  tree, comp, port = getComponent(name)
#  result =  '{"name": "error", "config": "", "msg" : "Invalid Component name!!"}'
  if setname :
    comp.activate_conf_set(setname)
    active_conf = setname
  else:
    active_conf = comp.active_conf_set_name 

  comp.set_conf_set_value(active_conf, conf_name, val)
  comp.activate_conf_set(active_conf)

  print >> sys.stderr, "Config: %s: %s = %s" % (active_conf, conf_name, val)
  result = """ {"ConfigName" : "%s", "Value": "%s" }""" % (conf_name, val)
  return result


"""
"""
def activateRtcConfigurationSet(name, conf_name):
  tree, comp, port = getComponent(name)
  set_keys = [k for k in conf_sets.keys() if not is_hidden(k) ]

  for set_name in set_keys:
    if set_name == conf_name :
      comp.activate_conf_set(conf_name)

  result = """ { "Activate" : "%s" } """ % (conf_name)
  return result

"""
"""
def getRtcConfigurationSet(name):
  tree, comp, port = getComponent(name)
  conf_sets = comp.conf_sets
  result = [k for k in conf_sets.keys() if not is_hidden(k) ]
  return result

"""
"""
def getActiveRtcConfigurationSet(name):
  tree, comp, port = getComponent(name)
  result = comp.active_conf_set_name 
  return result

"""
"""
def getRtcProfileList(dirname):
  try:
    val = format_dir_json(dirname)
  except:
    val = """ "No such component" """

  result = """{ "folder":"%s", "components": [ %s] }""" % (dirname, val)
  return result


"""
"""
def getValue(form, val, n_arg):
  try:
    #res = form[val].value
    res = form[val]
  except:
    if len(sys.argv) > n_arg+1:
      res = sys.argv[n_arg+1]
    else:
      res = None
  return res

"""
"""
def printResult(result):
  #print "Content-type: text/html;charset=utf-8"
  #print ""
  print result
