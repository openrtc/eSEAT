#
#
#
from __future__ import print_function
import sys
import os
import traceback
import threading
import platform

import yaml

try:
  import utils
except:
  from . import utils
#
#
ros_node=None
ros_node_name=None
ros_thread=None
ros_thread_loop=False
ros_ports=[]
__ros_version__=0

try:
  import rospy
  import roslib
  import roslib.message

  import actionlib

  import std_msgs.msg as std_msgs
  import geometry_msgs.msg as geometry_msgs
  import sensor_msgs.msg as sensor_msgs

  __ros_version__=1
  sys.path.append(os.path.realpath('ros/lib/site-packages'))
  os.environ['ROS_PYTHON_LOG_CONFIG_FILE'] = '' 
  try:
    from core import getGlobals, setGlobals
  except:
    from .core import getGlobals, setGlobals
   
except:
  try:
    import rclpy
    import std_msgs.msg as std_msgs
    import geometry_msgs.msg as geometry_msgs
    import sensor_msgs.msg as sensor_msgs
    __ros_version__=2
    sys.path.append(os.path.realpath('ros2/lib/site-packages'))

    from .core import getGlobals, setGlobals
  except:
    __ros_version__=0
    raise(ImportError)

#
#  Functions
#
def setRosMaster(hostname=None):
  if not hostname : hostname = platform.uname()[1]
  os.environ['ROS_MASTER_URI'] = 'http://%s:11311' % hostname

#
#
def initRosNode(name, anonymous=False):
  global ros_node_name, ros_node

  if not ros_node_name:
    try:
      if __ros_version__ == 1:
        setRosMaster()
        rospy.init_node(name, anonymous=anonymous)
        ros_node_name=rospy.get_name()
        if ros_node_name == '/unnamed': ros_node_name=None
      elif __ros_version__ == 2:
        rclpy.init(args=[])
        ros_node=rclpy.create_node(name)
        ros_node_name="/"+name
        return ros_node
      else:
        print("=== Unexpected error ===")
        ros_node_name=None

    except:
      print("=== Fail to ros_init ===")
      ros_node_name=None
  return ros_node_name

#
#
def ros_name():
  global ros_node_name
  return ros_node_name
  
#
#
def getMsgClass(datatype):
  env=getGlobals()
  try:
    dtype=eval(datatype.replace('/','.'), env)
    return dtype
  except:
    try:
      pkg, klass=datatype.split('/')
      exec("import "+pkg+".msg as "+pkg , env)
      dtype=eval(datatype.replace('/','.'), env)
      return dtype
    except:
      traceback.print_exc()
      return None
#   
#        
def getRosVersion():
  global __ros_version__
  return __ros_version__

#
#
def createRate(hz):
  if __ros_version__ == 1:
    return rospy.Rate(hz)
  elif __ros_version__ == 2:
    #print("Sorry, not implemented....")
    pass
  else:
    print("Unexpected error")

  return None

#
#
def getRosNode():
  global ros_node
  return ros_node
#
#   
def getRosPorts():
  global ros_ports
  return ros_ports
#
#   
def addRosPorts(p):
  global ros_ports
  ros_ports.append(p)
  return ros_ports
#
#   
def delRosPorts(p):
  global ros_ports
  ros_ports.remove(p)
  return ros_ports
#
#   
def numRosPorts():
  global ros_ports
  return len(ros_ports)
#
#
def service_loop():
  global ros_node
  global ros_thread_loop
  if __ros_version__ == 2:
    while ros_thread_loop :
      rclpy.spin_once(ros_node, timeout_sec=1.0)
    print("..Terminate RosThread")
#
#
def startRosService():
  global ros_thread
  global ros_thread_loop
  if __ros_version__ == 2:
    if not ros_thread:
      ros_thread_loop=True
      ros_thread = threading.Thread(target=service_loop)
      ros_thread.start()
    else:
      print("Warning: ros_thread is already started")
#
#
def stopRosService():
  global ros_thread_loop
  ros_thread_loop=False
#
#
class RosAdaptor(object):
  def __init__(self, name, typ, comp):
    self.name=name
    self.comp=comp
    self.type=typ
    self._port=None
    self.service_dtype=None
    self.service_call=None
    self.service_timeout=1.0
    self.stop_event=threading.Event()
  #
  #
  def send(self, name, val):
    if self.name == name:
      if self.type == 'Publisher':
        self.publish(val)
    else:
      print("Error: mismatch topic name")
  #
  #
  def create(self, name, datatype, arg):
    if self.type == 'Publisher':
      self.createPublisher(name, datatype, arg)
    elif self.type == 'Subscriber':
      self.createSubscriber(name, datatype, arg)

  #
  # 
  def createPublisher(self, name, datatype, size=1, nodelay=False):
    global ros_node
    if self.type == 'Publisher':
      if __ros_version__ == 1:
        dtype=getMsgClass(datatype)
        self._port=rospy.Publisher(name, dtype, queue_size=size, tcp_nodelay=nodelay)
        self.service_dtype=dtype

      elif __ros_version__ == 2:
        if ros_node:
          dtype=getMsgClass(datatype)
          self._port=ros_node.create_publisher(dtype, name)
          self.service_dtype=dtype
          addRosPorts(self._port)
      else:
        print("Unexpected error")
      
    return self._port

  #
  #
  def createSubscriber(self, name, datatype, callback):
    global ros_node
    if self.type == 'Subscriber':
      if __ros_version__ == 1:
        dtype=getMsgClass(datatype)
        self._port=rospy.Subscriber(name, dtype, callback)
        self.service_dtype=dtype

      elif __ros_version__ == 2:
        if ros_node:
          dtype=getMsgClass(datatype)
          self._port=ros_node.create_subscription(dtype, name, callback)
          self.service_dtype=dtype
          addRosPorts(self._port)
      else:
        print("Unexpected error")
      
    return self._port

  #
  #
  def publish(self, val):
    try:
      if isinstance(val, self.service_dtype) :
        self._port.publish(val)

      elif  self.service_dtype == std_msgs.String :
        if __ros_version__ == 1:
          self._port.publish(val)
        elif __ros_version__ == 2:
          msg=std_msgs.String()
          msg.data=val
          self._port.publish(msg)
        else:
          print("Unexpected error in publish", val)

      else:
        msg=self._port.data_class()
        if type(val) == str:
          val = yaml.load(val)
        args=[]
        for x in val:
          if type(x) == str:
            args.append(yaml.load(x)) 
          else:
            args.append(x) 
      
        if __ros_version__ == 1:
          roslib.message.fill_message_args(msg, args)
          self._port.publish(msg)
        elif __ros_version__ == 2:
          print("Not implemented")

        else:
          print("Unexpected error")

    except:
      traceback.print_exc()
      pass

  #
  #
  def newMessage(self):
    if __ros_version__ == 1:
      return self._port.data_class()

    elif __ros_version__ == 2:
      return self.service_dtype()

    else:
      print("Unexpected error")
      return None

  #
  #
  def getMessageSlots(self):
    if __ros_version__ == 1:
      return roslib.message.get_printable_message_args(self._port.data_class())
    elif __ros_version__ == 2:
      print("Sorry, not implement..")
    else:
      print("Unexpected error")
    return None

  #
  #
  def createServer(self, srv_name, srv_type, srv_impl, fname):
    global ros_node

    self.type = 'RosServer'
    env=getGlobals()

    if srv_type.find('.') > 0:
      pkgname,srv = srv_type.split('.',1)
      exec_str="import %s.srv as %s" % (pkgname, pkgname)
      try:
        exec(exec_str, env)
      except:
        pass

    if fname:
        utils.exec_script_file(fname, env)

    self.service_dtype=eval(srv_type, env)

    if __ros_version__ == 1:
      if srv_impl is None:
        resfunc=eval(srv_type+"Response", env)
        srv_func=lambda x :  resfunc(self.comp.onCallback(srv_name, x, key='ros_service'))
      else:
        resfunc=eval(srv_type+"Response", env)
        srv_func=lambda x :  resfunc(eval(srv_impl, env)(x))
      

      self._port=rospy.Service(srv_name, self.service_dtype, srv_func) 

    elif __ros_version__ == 2:
      if srv_impl is None:
        srv_func=lambda x,y : self.comp.onCallback(srv_name, x, y, key='ros_service')
      else:
        srv_func=eval(srv_impl, env)

      self._port=ros_node.create_service(self.service_dtype, srv_name, srv_func) 
      addRosPorts(self._port)
    else:
      print("Unexpected error")

    return self._port 
        
  #
  #
  def createClient(self, srv_name, srv_type):
    global ros_node

    self.type = 'RosClient'
    env=getGlobals()
    if srv_type.find('.') > 0:
      pkgname,srv = srv_type.split('.',1)
      exec_str="import %s.srv as %s" % (pkgname, pkgname)
      try:
        exec(exec_str, env)
      except:
        pass

    self.service_dtype=eval(srv_type, env)
    if __ros_version__ == 1:
      self._port=rospy.ServiceProxy(srv_name, self.service_dtype)

    elif __ros_version__ == 2:
      self._port=ros_node.create_client(self.service_dtype, srv_name) 
      addRosPorts(self._port)

    else:
      print("Unexpected error")

    return self._port 
  #
  #
  def callRosService(self, name, *args):
    global ros_node
    try:
      if __ros_version__ == 1:
        return self._port(*args)

      elif __ros_version__ == 2:
        while not self._port.wait_for_service(timeout_sec=self.service_timeout):
          ros_node.get_logger().info('service not available....')
          return None

        try:
          if self.service_call.done() is None:
            print("Another service calling...")
            return None
        except:
          pass
        #
        #
        req=self.service_dtype.Request()
        i=0
        for x in req.__slots__:
          req.__setattr__(x, args[i])
          i = i+1
        #
        #
        try:
          self.service_call = self._port.call_async(req)
          #rclpy.spin_until_future_complete(ros_node, future)

          while not self.service_call.done() : pass
          if self.service_call.result() is None:
            print(self.service_call.exception())

          return self.service_call.result()

        except AttributeError: 
          self._port.call(req)
          self._port.wait_for_future()
          return self._port.response

        except:
          traceback.print_exc()

      else:
        print("Unexpected error")

      return None

    except:
      traceback.print_exc()
      print("Error in callRosService [%s]" % name)
      return None

  #
  #
  def callAsyncRosService(self, name, *args):
    global ros_node
    try:
      if __ros_version__ == 1:
        print("Sorry, rospy.ServiceService doesn't support async call, please use actinlib...")
        return None

      elif __ros_version__ == 2:
        while not self._port.wait_for_service(timeout_sec=self.service_timeout):
          ros_node.get_logger().info('service not available....')
          return None

        try:
          if self.service_call.done() is None:
            print("Another service calling...")
            return None
        except:
          pass
        #
        #
        req=self.service_dtype.Request()
        i=0
        for x in req.__slots__:
          req.__setattr__(x, args[i])
          i = i+1
        #
        #
        try:
          self.service_call=self._port.call_async(req)
          return self.service_call

        except AttributeError: 
          print("Sorry, ardernt doesn't support async call, please use bouncy...")
          return None

        except:
          traceback.print_exc()

      else:
        print("Unexpected error")

      return None

    except:
      traceback.print_exc()
      print("Error in callRosService [%s]" % name)
      return None
  #
  #
  def waitForServiceResponse(self):
    try:
      while self.service_call.done() is None: pass
    except:
      pass
    return self.service_call.result()
  #
  #
  def checkServiceResponse(self):
    try:
      return self.service_call.done()
    except:
      pass
    return None

  #
  #
  def createActionServer(self, act_id, act_type, act_cb, fname):
    global ros_node

    if __ros_version__ == 1:
      self.type = 'RosActionServer'
      env=getGlobals()

      if act_type.find('.') > 0:
        pkgname,msg = act_type.split('.',1)
        exec_str="import %s.msg as %s" % (pkgname, pkgname)
        try:
          exec(exec_str, env)
        except:
          pass

      self._action_name=act_id
      self._action_type=eval(act_type+"Action", env)
      self._action_feedback=eval(act_type+"Feedback", env)
      self._action_result=eval(act_type+"Result", env)

      if act_cb is None:
         action_cb = lambda x : self.comp.onCallback(act_id, x, key='ros_action')
      else:
         action_cb = eval(act_cb, env)

      self._port=actionlib.SimpleActionServer(act_id, self._action_type,
                execute_cb=action_cb, auto_start=False)

      self._port.start()
      return self._port
    else:
      print("=== Not Supported ===")

    return None
  #
  #
  def createActionClient(self, act_id, act_type):
    global ros_node

    if __ros_version__ == 1:
      self.type = 'RosActionClient'
      env=getGlobals()

      if act_type.find('.') > 0:
        pkgname,msg = act_type.split('.',1)

        exec_str="import %s.msg as %s" % (pkgname, pkgname)
        try:
          exec(exec_str, env)
        except:
          pass

      self._action_name=act_id
      self._action_type=eval(act_type+"Action", env)
      self._action_goal=eval(act_type+"Goal", env)

      self._port=actionlib.SimpleActionClient(act_id, self._action_type)
      return self._port
    else:
      print("=== Not Supported ===")
    return None

  #
  #
  def newActionGoal(self, *arg, **kwargs):
    try:
      return self._action_goal(*arg, **kwargs)
    except:
      pass
    return None
  #
  #
  def newActionFeedback(self, *arg, **kwargs):
    try:
      return self._action_feedback(*arg, **kwargs)
    except:
      pass
    return None
  #
  #
  def newActionResult(self, *arg, **kwargs):
    try:
      return self._action_result(*arg, **kwargs)
    except:
      pass
    return None
  #
  # 
  def isPreemptRequested(self):
    try:
      return self._port.is_preempt_requested()
    except:
      pass
    return False
  #
  # 
  def setPreempted(self):
    try:
      return self._port.set_preempted()
    except:
      pass
    return None
  #
  # 
  def getActionName(self):
    try:
      return self._action_name
    except:
      pass
    return False
  #
  # 
  def publishFeedback(self, val):
    try:
      self._port.publish_feedback(val)
    except:
      pass
    return
  #
  # 
  def setSucceeded(self, val):
    try:
      self._port.set_succeeded(val)
    except:
      pass
    return
  #
  # 
  def startActionServer(self):
    try:
      self._port.start()
    except:
      pass
    return 
  #
  #
  def setActionGoal(self, goal, **kwargs):
    try:
      self._port.wait_for_server()
      self._port.send_goal(goal, **kwargs)
    except:
      pass
    return 
  #
  #
  def setActionGoalEx(self, goal, done_cb=None, active_cb=None, feedback_cb=None):
    try:

      if done_cb:
         _done_cb=lambda x : self.comp.onCallback(self._action_name, x, key=done_cb)
      else:
         _done_cb=None

      if active_cb:
         _active_cb=lambda x : self.comp.onCallback(self._action_name, x, key=active_cb)
      else:
         _active_cb=None

      if feedback_cb:
         _feedback_cb=lambda x : self.comp.onCallback(self._action_name, x, key=feedback_cb)
      else:
         _feedback_cb=None

      self._port.wait_for_server()
      self._port.send_goal(goal, done_cb=_done_cb, active_cb=_active_cb, feedback_cb=_feedback_cb)
    except:
      pass
    return 
  #
  #
  def waitAction(self, sec=5.0):
    try:
      self._port.wait_for_result(rospy.Duration.from_sec(sec))
      return self._port.get_status()
    except:
      pass
    return None
  #
  #
  def waitActionResult(self):
    try:
      self._port.wait_for_result()
      return self._port.get_result()
    except:
      pass
    return None

  #
  #
  def terminate(self):
    global ros_node
    if __ros_version__ == 1:
      pass
    elif __ros_version__ == 2:
      if ros_node:
        stopRosService()
        if self.type == 'RosServer':
          ros_node.destory_service(self._port)

        delRosPorts(self._port)

        if numRosPorts() < 1:
          ros_node.destory_node()
          rclpy.shutdown()
    else:
      pass
