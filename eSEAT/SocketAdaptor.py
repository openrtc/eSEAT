#
#  SocketAdaptor 
#  Communication Adaptor for RawSocket
#
#   Copyright(C) 2015, Isao Hara, AIST  All rights reserved.
#   Release under the MIT License.
#

from __future__ import print_function
import sys
import os
import socket
import select
import time
import datetime
import threading
import struct
import copy
import types
import time

###############################################################
#
# SocketAdaptor: Communication Port for a raw socket connection
#
class SocketAdaptor(threading.Thread):
    def __init__(self, owner, name, host, port):
        threading.Thread.__init__(self)
        self.owner = owner
        self.name = name
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.mainloop = True
        self.start()

    #
    #  Background job ( message reciever )
    #
    def run(self):
        while self.mainloop:
            if self.connected == False:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    self.socket.settimeout(1)
                    self.connected = True
                except socket.error:
                    print( "reconnect error" )
                    time.sleep(1)
                except:
                    print (traceback.format_exc())

            if self.connected == True:
                try:
                    data = self.socket.recv(4096)   ## 4k
                    if len(data) != 0:
                        self.owner.processResult(self.name, data)
                except socket.timeout:
                    pass
                except socket.error:
                    print (traceback.format_exc())
                    self.socket.close()
                    self.connected = False
                except:
                    print (traceback.format_exc())

    #
    #  Stop background job
    #
    def terminate(self):
        self.mainloop = False
        if self.connected == True:
            self.socket.close()
            self.connected = False
    #
    #  Send message
    #
    def send(self, name, msg):
        if self.connected == False:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.connected = True
                print ("connect socket")
            except socket.error:
                print ("cannot connect")

        if self.connected == True:
            try:
                self.socket.sendall(msg+"\n")
            except socket.error:
                print (traceback.format_exc())
                self.socket.close()
                self.connected = False


