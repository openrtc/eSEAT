#
#
#import ssr
from __future__ import print_function
#execfile("rtc_handle.py")

def initNS(hostname="localhost"):
  global rtm
  rtm=RtmEnv([])
  ns=NameSpace(rtm.orb, hostname)
  ns.list_obj()
  return ns

def initSeatNS(hostname="localhost"):
  ns=NameSpace(seat.manager._orb, hostname)
  ns.list_obj()
  return ns

def get_handle_list(hostname="localhost"):
  global NS
  try:
    NS = initSeatNS(hostname)
  except:
    NS = initNS(hostname)

  hdls_names = NS.rtc_handles.keys()
  n=1
  res=[]
  for name in hdls_names:
    print (n,":", name)
    res.append(name)
    n += 1
  return res

def get_handle(name, ns=None):
  global NS
  if not ns : ns=NS

  if name.count(".rtc") == 0 : name = name+".rtc"

  try:
    return ns.rtc_handles[name]
  except:
    #get_handle_list()
    return None

def get_port_info(name, ns=None):
  h =  get_handle(name, ns)
  res=[]
  if h :
    for x in h.inports.keys():
      res.append( "%s (in) [%s]" % (x, h.inports[x].data_type))
    for x in h.outports.keys():
      res.append( "%s (out) [%s]" % (x, h.outports[x].data_type))
    for x in h.services.keys():
      res.append( "%s (service)" % (x,))
  return res

def exit_rtc(name, ns=None):
  h=get_handle(name, ns)
  if h : h.exit()

def get_named_dataport(name, port, ns=None):
  global NS
  if not ns : ns=NS

  if name.count(".rtc") == 0 : name = name+".rtc"
  hndl=get_handle(name, ns)

  if hndl and port:
    if port in hndl.inports.keys():
      return hndl.inports[port]
    if port in hndl.outports.keys():
      return hndl.outports[port]

  return None

def get_name_port(path1):
  val =  path1.split(":")
  if len(val) == 1 : return [path1, None]
  return val

def create_connection_name(path1, path2):
  global NS
  name1, port1 =  get_name_port(path1)
  name2, port2 =  get_name_port(path2)

  try:
    pp1 = get_named_dataport(name1, port1, NS)
    pp2 = get_named_dataport(name2, port2, NS)
    pn1 = string.join([name1,pp1.name, name2, pp2.name], '_')
    pn2 = string.join([name2,pp2.name, name1, pp1.name], '_')
    return [pn1, pn2]

  except:
    print ("ERROR in create_connection_name.")
    pass

  return None 

def check_connection_list(names, connections):
  for name in names:
    if name in connections.keys() : return True

  return False

def connect_ports(path1, path2):
  global NS, connections
  pp1 = None
  pp2 = None
  con = None
  path1=str(path1.strip())
  path2=str(path2.strip())

  if check_connection(path1, path2):
    print ("Connection already exist.")
    return None

  cnames = create_connection_name(path1, path2)
  if not cnames:
    print ("Invalid Path: %s, %s" % (path1, path2))
    return None

    
  name1, port1 =  get_name_port(path1)
  name2, port2 =  get_name_port(path2)

  try:
    pp1 = get_named_dataport(name1, port1, NS)
    pp2 = get_named_dataport(name2, port2, NS)

    if pp1 and pp2:
      con = IOConnector([pp1, pp2], cnames[0])
      con.connect()
      connections[con.name] = con

  except:
    print ("Connection error")
    pass

  return con

def find_connection(path1, path2):
  global NS, connections
  path1=str(path1.strip())
  path2=str(path2.strip())
  cnames = create_connection_name(path1, path2)

  if not cnames:
    print( "Invalid Path: %s, %s" % (path1, path2) )

  if cnames[0] in connections:
      return [cnames[0], connections[cnames[0]] ]

  if cnames[1] in connections:
      return [cnames[1], connections[cnames[1]] ]

  print ("No connection exists.")
  return None

def disconnect_ports(path1, path2):
  global NS, connections
  path1=str(path1.strip())
  path2=str(path2.strip())
  if not check_connection(path1, path2):
    print ("No connection exist.")
    return None

  res=remove_connection(path1, path2)
#  con = find_connection(path1, path2)
#  if con:
#    del(connections[con[0]])
#    con[1].disconnect();
#    return con[0]
  return res

def activate_rtc(path1):
  name, port =  get_name_port(path1)

  h=get_handle(name.strip())
  if h :
    h.activate()
    return "RTC_OK"
  else:
    return "No such a RTC:"+name

def activate_rtcs(names):
  res=""
  for n in names.split(",") :
    res = activate_rtc(n) + "\n"
  return res

def deactivate_rtc(path1):
  name, port =  get_name_port(path1)

  h=get_handle(name.strip())
  if h :
    h.deactivate()
    return "RTC_OK"
  else:
    return "No such a RTC:"+name

def deactivate_rtcs(names):
  res=""
  for n in names.split(",") :
    res = deactivate_rtc(n) + "\n"
  return res

def exit_rtc(path1):
  name, port =  get_name_port(path1)

  h=get_handle(name.strip())
  if h :
    h.exit()
    return "RTC_OK"
  else:
    return "No such a RTC:"+name

def exit_rtcs(names):
  res=""
  for n in names.split(",") :
    res = exit_rtc(n) + "\n"
  return res

def retrieve_connection_profiles(path1):
  global NS
  name1, port1 =  get_name_port(path1)

  try:
    pp1 = get_named_dataport(name1, port1, NS)
    return pp1.get_connections()
  except:
    return []

def check_connection(path1, path2):
  connectors1=retrieve_connection_profiles(path1)
  connectors2=retrieve_connection_profiles(path2)
  for con in connectors1:
    cid = con.connector_id
    for con2 in connectors2:
      if cid == con2.connector_id : return con
  return None
 
def remove_connection(path1, path2):
  con = check_connection(path1, path2)
  if con :
    con.ports[0].disconnect(con.connector_id)
    return con
  else:
    print ("No Connections")
    return False

def disconnect_all(path1):
  cprofs=retrieve_connection_profiles(path1)
  for x in cprofs:
     x.ports[0].disconnect(x.connector_id)

def make_connection(paths, dim=","):
  ports=paths.split(dim) 
  if len(ports) == 2:
    connect_ports(ports[0], ports[1])

def delete_connection(paths, dim=","):
  ports=paths.split(dim) 
  if len(ports) == 2:
    disconnect_ports(ports[0], ports[1])

def clear_connection_list():
    connections = []


#### Global Variables
rtc_list={}
connections={}
nshost="localhost"

