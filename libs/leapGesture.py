from __future__ import print_function
from itertools import chain
global center_r, center_l

center_r=[0,0,0]
center_l=[0,0,0]

def LeapGesture(frame, Info, Swipe, Circle, Screen, Key):
  global seat,center_r, center_l
  ges = frame.gestures
  if ges :
    for g in ges:
      if g.type == 1:
        val = getSwipeGesture(g)
	if (val):
          info = "Pos: %3.1f, %3.1f, %3.1f" % (val[1].x, val[1].y, val[1].z)
          seat.setEntry(Swipe, info)
          seat.setEntry(Info, val[0].split(':')[1])

      elif g.type == 4:
        val = getCircleGesture(g)
	if (val):
          info = "Center: %3.1f, %3.1f, %3.1f" % (val[1].x, val[1].y, val[1].z)
          seat.setEntry(Circle, info)
          seat.setEntry(Info, val[0].split(':')[1])

      elif g.type == 5:
        val = getScreenGesture(g)
	if (val):
          info = "Pos: %3.1f, %3.1f, %3.1f" % (val[1].x, val[1].y, val[1].z)
          seat.setEntry(Screen, info)
          seat.setEntry(Info, val[0].split(':')[1])

      elif g.type == 6:
        val = getKeyGesture(g)
	if (val):
          info = "Pos: %3.1f, %3.1f, %3.1f" % (val[1].x, val[1].y, val[1].z)
          info += " D: %3.1f, %3.1f, %3.1f" % (val[2].x, val[2].y, val[2].z)

          seat.setEntry(Key, info)
          seat.setEntry(Info, val[0].split(':')[1])

      else:
          print ("Gesture[ %d ]" % (g.type))

def getLeapGesture(ges):
  global seat
  if ges :
    for g in ges:
      if g.type == 4:
        val = getCircleGesture(g)
        if val : return val[0]
      elif g.type == 1:
        val = getSwipeGesture(g)
        if val : return val[0]
      else:
          pass
  return None

#
#
def getCircleGesture(g, thr=25):
  if g.type == 4:
#    if g.circle.state == 3 :
    if g.circle.state == 3 and g.circle.radius > thr :
      if g.circle.normal.z < 0:
        Gesture = "%d:CW_Circle,%3.1f" % (g.id, g.circle.radius)
      else:
        Gesture = "%d:CCW_Circle,%3.1f" % (g.id, g.circle.radius)
      return [Gesture, g.circle.center, g.circle.radius]
  return None

def getSwipeGesture(g):
  if g.type == 1:
    if g.swipe.state == 3:
      Gesture="%d:Swipe" % (g.id)
      shval= 0.5

      if g.swipe.direction.x >  shval: Gesture +="Right"
      if g.swipe.direction.x < -shval: Gesture +="Left"
      if g.swipe.direction.y >  shval: Gesture +="Up"
      if g.swipe.direction.y < -shval: Gesture +="Down"

      if g.swipe.startPosition.x > 0: Gesture +="_R"
      else: Gesture +="_L"

      return [Gesture, g.swipe.startPosition, g.swipe.position, g.swipe.speed]
  return None


def getScreenGesture(g):
  if g.type == 5:
    if g.screen.state == 3 or g.screen.state == 1:
      Gesture="%d:Screen" % (g.id)
      return [Gesture, g.screen.position, g.screen.direction, g.screen.state]
  return None

def getKeyGesture(g):
  if g.type == 6:
    if g.key.state == 3:
      Gesture="%d:Key" % (g.id)
      return [Gesture, g.key.position, g.key.direction]
  return None

#
#
def LeapHands(hands, nId, InfoId):
  global seat, center_r, center_l

  if len(hands) == 2 :
    handR=hands[0]
    handL=hands[1]
  elif len(hands) == 1 :
    handR=hands[0]
    handL=None
  else:
    handR=None
    handL=None

  pos1, ori1, num1 = getLeapHandInfo(handR)
  pos2, ori2, num2 = getLeapHandInfo(handL)

  if pos1[0] > pos2[0] :
    sideR = "1"
    cr=center_r
    sideL = "2"
    cl=center_l
  else:
    sideR = "2"
    cr=center_l
    sideL = "1"
    cl=center_r

  seat.setEntry(nId, len(hands))
  LeapHandInfo(pos1, cr, ori1, InfoId+sideR, num1[0], num1[1])
  LeapHandInfo(pos2, cl, ori2, InfoId+sideL, num2[0], num2[1])


def getLeapHands(hands):
  global seat

  if len(hands) == 2 :
    if hands[0].palmPosition.x > hands[1].palmPosition.x :
      return [getLeapHandInfo(hands[1]), getLeapHandInfo(hands[0])]
    else:
      return [getLeapHandInfo(hands[0]), getLeapHandInfo(hands[1])]

  elif len(hands) == 1 :
    if hands[0].palmPosition.x > 0 :
      return [None, getLeapHandInfo(hands[0])]
    else:
      return [getLeapHandInfo(hands[0]), None]

  else:
    return [None, None]

def getLeapHandInfo(hand):
  try:
    if hand :
      pos = hand.palmPosition
      ori = hand.palmOrientation
      nm = NumOfFingerState(hand.fingers)
      return [[pos.x, pos.y, pos.z], [ori.roll*57.3, ori.pitch*57.3, ori.yaw*57.3],nm]
    else:
      return [[0,0,0], None, [0, 0]]

  except:
    return [None, None, [0, 0]]

def LeapHandInfo(pos, c, ori, Id, n=0, m=0):
  global seat
  if ori :
    infoPos =" %3.1f, %3.1f, %3.1f" % (pos[0]-c[0],pos[1]-c[1],pos[2]-c[2])
    seat.setEntry(Id+"Pos", infoPos)
    infoOri =" %d, %d, %d, [%d/%d]" % (ori[0], ori[1], ori[2], m, n)
    seat.setEntry(Id+"Ori", infoOri)
  else:
    seat.setEntry(Id+"Pos", "")
    seat.setEntry(Id+"Ori", "")

def NumOfFingerState(fingers):
  res_h = 0
  res_t = 0
  for f in fingers:
    if f.touchZone > 0 : res_h += 1
    if f.touchZone > 1 : res_t += 1

  return [res_h, res_t]

def  getTouchFlag(tflag, finfo):
  if not tflag and finfo[0] >= 4 and finfo[1] >= 3:
    return  1 
  if tflag and finfo[0] < 3 :
    return 0
  return -1

def touchLabel(flag, eid):
  global seat
  if flag : seat.setLabelConfig(eid, bg="red")
  else: seat.setLabelConfig(eid, bg="grey")

def printPosDiff(st, pos, eid):
  global seat
  dpos=getPosDiff(st, pos)
  if dpos and eid:
    strP="[ %3.0f, %3.0f %3.0f]" % ( dpos[0], dpos[1], dpos[2])
    seat.setEntry(eid, strP)

def getPosDiff(st, pos):
  global seat
  try:
    if st:
      return [pos[0]-st[0], pos[1]-st[1], pos[2]-st[2]]
  except:
    pass
  return []
