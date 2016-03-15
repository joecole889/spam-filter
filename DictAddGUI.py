# -*- coding: utf-8 -*-
"""
Created on Thurs Mar 10 11:03:00 2016

@author: Joseph R. Cole
"""

#import pdb
import Tkinter as tki
import tkSimpleDialog
import logging

class DictAddGUI(tkSimpleDialog.Dialog) :
	def body(self, parent) :
		tki.Label(parent,text="Enter a name for the dictionary:").grid(row=0,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.DictNameEntry = tki.Entry(parent,width=50)
		self.DictNameEntry.grid(row=1,column=0,sticky=tki.W,padx=5)
		return self.DictNameEntry

	def apply(self) :
		self.result = self.DictNameEntry.get()

	def cancel(self,_=None) :
		logging.debug("Shutting down the dialog")
		self.parent.focus_set()
		self.destroy()
	
###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()

	root = tki.Tk()
	root.wm_title("Test the dictionary adding dialog")
	EndConnection = DictAddGUI(root,"Create a dictionary")
	DictName = EndConnection.result
	if DictName :
		logging.debug("New dictionary will be labelled: %s"%DictName)
	else :
		logging.debug("No label returned")
