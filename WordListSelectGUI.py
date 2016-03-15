# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 12:21:00 2016

@author: Joseph R. Cole
"""

#import pdb
import Tkinter as tki
import tkSimpleDialog
import logging
import os
from EmailSamplesDB import *

class WordListSelectGUI(tkSimpleDialog.Dialog) :
	def __init__(self, parent, DBobj, title=None) :
		self.DBobj = DBobj
		tkSimpleDialog.Dialog.__init__(self, parent, title)

	def body(self, parent) :
		tki.Label(parent,text="Select a word list:").grid(row=0,column=0,sticky=tki.W,padx=5)
		self.AvailWordListsVar = tki.StringVar(parent)
		self.AvailWordListsMenu = tki.OptionMenu(parent,self.AvailWordListsVar,None)
		self.DBobj.ConnectDB()
		WordLists = self.DBobj.GetAvailableWordLists()
		self.UpdateWordListDropDown(WordLists)
		self.AvailWordListsMenu.grid(row=1,column=0,sticky=tki.W,padx=5)

		return self.AvailWordListsMenu

	def apply(self) :
		"""
		Return the database id of the new word list
		"""
		try :
			ListRef = self.AvailWordListsVar.get()
			ListName,list_id,DictRef,DictName = self.DBobj.ResolveListRef(ListRef)
		except Exception as detail :
			logging.error(detail)
			list_id = None
		self.result = list_id

	def UpdateWordListDropDown(self,NewList) :
		"""
		Updates the values available in the word list drop down menu.
		The user should select the word list to use for an operation.

		NewList - a list of tuples to define entrys for the word list drop down menu.  Each tuple is:
		("table name in the database for the word list","a human readable name for the word list")
		"""
		self.AvailWordListsMenu['menu'].delete(0,'end')
		if (NewList is not None) and (len(NewList) > 0) :
			self.AvailWordListsVar.set(str(NewList[0][0]))
			for choice,readable in NewList :
				choicestr = '%s: %s'%(choice,readable)
				self.AvailWordListsMenu['menu'].add_command(label=choicestr, command=tki._setit(self.AvailWordListsVar, str(choice)))
		else :
			self.AvailWordListsVar.set('')
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
	root.wm_title("Test the word list selection dialog")
	EndConnection = WordListRemoveGUI(root,aa,"Select a word list")
	if EndConnection.result is not None :
		logging.debug("Word list id selected: %s"%str(EndConnection.result))
	else :
		logging.debug("No word list id returned")
