#
# Adaptor for Shared Memory
#
from __future__ import print_function
import sys
import os
import sysv_ipc
import struct
import traceback
from ctypes import *

#
#
#
class ShmAdaptor(object):
  def __init__(self, name, id, size):
      self.name=name
      self.shm_id=id
      self.shm_size=size
      try:
        self.shm=sysv_ipc.SharedMemory(id, 0, mode=666) 
      except:
        self.shm=None

  def terminate(self):
      pass
  def createShm(self, id, size):
      self.shm=sysv_ipc.SharedMemory(id, sysv_ipc.IPC_CREAT, mode=666, size=size) 
      self.shm_size=size

  def read_int(self, off):
      return struct.unpack('i',self.shm.read(4, off))[0]

  def read_short(self, off):
      return struct.unpack('h',self.shm.read(2, off))[0]

  def read_ushort(self, off):
      return struct.unpack('H',self.shm.read(2, off))[0]

  def read_uchar(self, off):
      return struct.unpack('B',self.shm.read(1, off))[0]

  def read_float(self, off):
      return struct.unpack('f',self.shm.read(4, off))[0]

  def read_double(self, off):
      return struct.unpack('d',self.shm.read(8, off))[0]

  def write_int(self, off, val):
      self.shm.write(struct.pack('i',val), off)
      return

  def write_short(self, off, val):
      self.shm.write(struct.pack('h',val), off)
      return

  def write_byte(self, off, val):
      self.shm.write(struct.pack('b',val), off)
      return

  def write_float(self, off, val):
      self.shm.write(struct.pack('f',val), off)
      return

  def write_double(self, off, val):
      self.shm.write(struct.pack('d',val), off)
      return

