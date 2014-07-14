import omniORB
from RTC import *


def getTypeDesc(x):
  if(type(x) == tuple) : repId = x[2]
  else: repId=x._NP_RepositoryId
  return omniORB.findType(repId)

def getTypeType(x):
  return getTypeDesc(x)[0]

def getTypeId(x):
  typ = getTypeType(x)
  if typ in [omniORB.tcInternal.tv_struct,
		   omniORB.tcInternal.tv_union ] :
    return getTypeDesc(x)[2]
  elif typ in [omniORB.tcInternal.tv_objref,
              omniORB.tcInternal.tv_string,
              omniORB.tcInternal.tv_wstring,
              omniORB.tcInternal.tv_fixed,
              omniORB.tcInternal.tv_abstruct_interface,
	      omniORB.tcInternal.tv_local_interface] :
    return getTypeDesc(x)[1]
  else:
    return typ

def getTypeName(x):
  typ = getTypeType(x)
  if typ in [omniORB.tcInternal.tv_struct,
		   omniORB.tcInternal.tv_union ] :
    return getTypeDesc(x)[3]
  elif typ in [omniORB.tcInternal.tv_objref,
              omniORB.tcInternal.tv_string,
              omniORB.tcInternal.tv_wstring,
              omniORB.tcInternal.tv_fixed,
              omniORB.tcInternal.tv_abstruct_interface,
	      omniORB.tcInternal.tv_local_interface] :
    return getTypeDesc(x)[2]
  else:
    return typ

def getMemberDesc(x):
  typ = getTypeType(x)

  if typ in [omniORB.tcInternal.tv_struct,
		   omniORB.tcInternal.tv_union ] :
     return getTypeDesc(x)[4:]
  else:
     return None

def getMemberSize(x):
  desc = getMemberDesc(x)
  return len(desc)/2

def getMemberNames(x):
  desc = getMemberDesc(x)
  res = []
  for i in range(len(desc)/2):
    res.append(desc[i*2]) 
  return res

def getMemberTypeByName(x, name):
  desc = getMemberDesc(x)
  for i in range(len(desc)/2):
    if desc[i*2] == name: return desc[i*2 + 1] 
  return None

def getTypeInfo(x):
  desc = getTypeDesc(x)
  printTypeInfo(desc)

def printTypeInfo(typ, idx=0):
  if typ[0] == omniORB.tcInternal.tv_struct :
    vars = typ[4:]
    for x in range(len(vars)/2) :
      if type(vars[x * 2 +1]) == int:
        print " "*idx, vars[x * 2], vars[x * 2 +1]
      else:
        print " "*idx, vars[x * 2]
	printTypeInfo( vars[x * 2 +1], idx+1 )

