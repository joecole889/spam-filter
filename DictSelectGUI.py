# -*- coding: utf-8 -*-
"""
Created on Thurs Mar 10 13:26:00 2016

@author: Joseph R. Cole
"""

#import pdb
import Tkinter as tki
import tkSimpleDialog
import logging
import os
from EmailSamplesDB import *

class DictSelectGUI(tkSimpleDialog.Dialog) :
	def __init__(self, parent, DBobj, title=None) :
		self.DBobj = DBobj
		tkSimpleDialog.Dialog.__init__(self, parent, title)

	def body(self, parent) :
		tki.Label(parent,text="Select a dictionary to update:").grid(row=0,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.AvailDictsVar = tki.StringVar(parent)
		self.AvailDictsMenu = tki.OptionMenu(parent,self.AvailDictsVar,None)
		self.DBobj.ConnectDB()
		DictList = self.DBobj.GetAvailableDicts()
		self.UpdateDictDropDown(DictList)
		self.AvailDictsMenu.grid(row=1,column=0,sticky=tki.W,padx=5)
		return self.AvailDictsMenu

	def apply(self) :
		"""
		Return the database id of the user selected dictionary
		"""
		DictRef = self.AvailDictsVar.get()
		try :
			DictName,dict_id = self.DBobj.ResolveDictRef(DictRef)
		except Exception as detail :
			logging.error("Couldn't resolve selected dictionary reference %s: %s"%(DictRef,detail))
			dict_id = None
		self.result = dict_id

	def UpdateDictDropDown(self,NewList) :
		"""
		Updates the values available in the dictionary list drop down menu.
		The user should select the dictionary to use for an operation

		NewList - a list of tuples to define entrys for the word list drop down menu.  Each tuple is:
		("table name in the database for the dictionary","a human readable name for the dictionary")
		"""
		self.AvailDictsMenu['menu'].delete(0,'end')
		if (NewList is not None) and (len(NewList) > 0) :
			self.AvailDictsVar.set(str(NewList[0][0]))
			for choice,readable in NewList :
				choicestr = '%s: %s'%(choice,readable)
				self.AvailDictsMenu['menu'].add_command(label=choicestr, command=tki._setit(self.AvailDictsVar, str(choice)))
		else :
			self.AvailDictsVar.set('')
		return

	def cancel(self,_=None) :
		logging.debug("Shutting down the dialog")
		self.DBobj.DisconnectDB()
		self.parent.focus_set()
		self.destroy()
	
###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()
	aa = EmailSamplesDB(os.path.abspath(r".\EmailSamplesDB_SQL.json"),
		                os.path.abspath(r".\DBSetup_SQL.json"),
		                os.path.abspath(r".\TempDB_SQL.json"))
	aa.DBpath = os.path.abspath(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\tester2.sqlite3")

	root = tki.Tk()
	root.wm_title("Test the dictionary updating dialog")
	EndConnection = DictSelectGUI(root,aa,"Update a dictionary")
	dict_id = EndConnection.result
	if dict_id is not None :
		logging.debug("Dictionary id to update: %d"%dict_id)
	else :
		logging.debug("No id returned")
