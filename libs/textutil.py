
def printText(txt, msg):
  global seat
  seat.appendText(txt, msg+"\n")

def sendDoubleSeq(in_str):
  global seat,rtc_result
  instr = seat.getEntry(in_str)
  if instr.strip() :
      rtc_result=eval("TimedDoubleSeq(Time(0,0),["+instr+"])")

def ouputDoubleSeq(out_str):
  global seat,rtc_result
  data=rtc_in_data.data
  l_data=len(data)
  msg = ""
  for i in range(l_data):
    msg = msg + " %1.3f" % (data[i])
    if i < (l_data -1) : msg = msg + ","
  seat.setEntry(out_str, msg)

def mkTime():
  import time
  ctime=time.time()
  return Time(int(ctime), int((ctime-int(ctime))*1000))

def mkTimedDoubleSeq(v, tm=None ):
  if tm :  tm=mkTime()
  else : tm=Time(0,0)

  return TimedDoubleSeq(tm, v)

def outPosAngle(n, v_in, tm_in, d=1):
  global seat,rtc_result
  val=float(seat.getEntry(v_in)) * d
  tm=float(seat.getEntry(tm_in))
  v =[ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
  v[n] = val
  v[6] = tm
  rtc_result=mkTimedDoubleSeq(v)

def outputJoints(val):
  global seat,rtc_in_data
  data = rtc_in_data.data
  ldata = len(data)
  for i in range(ldata):
    tag=val+str(i)
    ang = " %1.3f" % (data[i])
    seat.setEntry(tag,ang)

def sendJoints(val):
  global seat,rtc_result
  v = "["
  for i in range(7):
    tag=val+str(i)
    v = v+seat.getEntry(tag)
    v = v+", "
  v = v+seat.getEntry("timeIn2") + "]"
  #print v
  rtc_result=mkTimedDoubleSeq(eval(v))

def copyJoints(sval, tval):
  global seat
  for i in range(7):
    stag=sval+str(i)
    ttag=tval+str(i)
    seat.setEntry(ttag, seat.getEntry(stag))

