#!/usr/bin/env python

import sys
import threading

try:
    import Tkinter as tk
    import ScrolledText
except:
    import tkinter as tk
    import tkinter.scrolledtext as ScrolledText

#
#
class RedirectText(object):
    def __init__(self, text_ctrl, parent):
        self.output = text_ctrl
        self.parent = parent

    def write(self, string):
        try:
            self.parent.lock()
            self.output.insert(tk.END, string)
            self.output.see('end')
            self.parent.unlock()
        except:
            pass

#
#
class OutViewer(object):
    def __init__(self):
        self.root = None
        self.scrtxt = None
        self.rdtxt = None
        self.locking = threading.RLock()

    def createViewer(self, root=None, use_top=False):
        if not root : 
            self.root = tk.Tk()
        
        if use_top :
            self.top = tk.Toplevel()
        else:
            self.top = self.root

        self.frame = tk.Frame(self.top)
        self.frame.pack()
  
        self.toolbar = tk.Frame(self.frame)
        b1 = tk.Button(self.toolbar, text="Clear", width=6, command=self.clear)
        b1.pack(side="left", padx=2, pady=2)

        b1 = tk.Button(self.toolbar, text="Captue", width=6, command=self.setStdout)
        b1.pack(side="left", padx=4, pady=2)

        b1 = tk.Button(self.toolbar, text="Release", width=6, command=self.resetStdout)
        b1.pack(side="left", padx=2, pady=2)

        self.toolbar.pack(side="top", fill=tk.X)

        self.scrtxt = ScrolledText.ScrolledText(self.frame)
        self.scrtxt.configure(font='TkFixedFont')
        self.scrtxt.pack(side="top")

        self.rdtxt = RedirectText(self.scrtxt, self)
        self.setStdout()

    def clear(self):
        if self.scrtxt:
            self.lock()
            self.scrtxt.delete('1.0', tk.END+'-1c')
            self.unlock()

    def lock(self):
        self.locking.acquire()

    def unlock(self):
        self.locking.release()

    def setStdout(self):
        if self.rdtxt:
            self.lock()
            sys.stdout = self.rdtxt
            self.unlock()
    
    def resetStdout(self):
        self.lock()
        sys.stdout = sys.__stdout__
        self.unlock()


