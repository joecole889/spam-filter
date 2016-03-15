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

class WordListAddGUI(tkSimpleDialog.Dialog) :
	def __init__(self, parent, DBobj, title=None) :
		self.DBobj = DBobj
		parent.register(self.MinValidate)
		parent.register(self.MaxValidate)
		self.mininvhook = (parent.register(self.MinReset), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
		self.maxinvhook = (parent.register(self.MaxReset), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
		tkSimpleDialog.Dialog.__init__(self, parent, title)

	def body(self, parent) :
		tki.Label(parent,text="Enter a name for the word list:").grid(row=0,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.WordListEntry = tki.Entry(parent,width=50)
		self.WordListEntry.grid(row=1,column=0,columnspan=2,sticky=tki.W,padx=5)

		tki.Label(parent,text="Select a dictionary for a word source:").grid(row=2,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.AvailDictsVar = tki.StringVar(parent)
		self.AvailDictsMenu = tki.OptionMenu(parent,self.AvailDictsVar,None)
		self.DBobj.ConnectDB()
		DictList = self.DBobj.GetAvailableDicts()
		self.UpdateDictDropDown(DictList)
		self.AvailDictsMenu.grid(row=3,column=0,columnspan=2,sticky=tki.W,padx=5)

		MinPerc = self.DBobj.params['MinCountFrac']
		MaxPerc = self.DBobj.params['MaxCountFrac']
		tki.Label(parent,text="Word count\nlower limit").grid(row=4,column=0)
		tki.Label(parent,text="Word count\nupper limit").grid(row=4,column=1)
		self.MinEntry = tki.Entry(parent)
		self.MinEntry.insert(0,MinPerc)
		self.MinEntry.grid(row=5,column=0)
		self.MaxEntry = tki.Entry(parent)
		self.MaxEntry.insert(0,MaxPerc)
		self.MaxEntry.grid(row=5,column=1)
		self.MinEntry.config(validate='focus',validatecommand=self.MinValidate,invalidcommand=self.mininvhook)
		self.MaxEntry.config(validate='focus',validatecommand=self.MaxValidate,invalidcommand=self.maxinvhook)

		return self.WordListEntry

	def apply(self) :
		"""
		Return the database id of the new word list
		"""
		try :
			DictRef = self.AvailDictsVar.get()
			DictName,dict_id = self.DBobj.ResolveDictRef(DictRef)
			WordListName = self.WordListEntry.get()
			MinPerc,MaxPerc = self.MinMaxGet()
		except Exception as detail :
			logging.error("Bad parameters given for the new word list: %s"%detail)
			WordListName,dict_id,MinPerc,MaxPerc = (None,None,0,1)
		self.result = (WordListName,dict_id,MinPerc,MaxPerc)

	def MinValidate(self) :
		logging.debug("validating min")
		Valid = False
		try :
			MaxPerc = self.MaxGet()
			MinPerc = self.MinGet()
			assert MinPerc>=0,"Lower limit must be non-negative"
			assert MinPerc<MaxPerc,"Lower limit %f must be less than upper limit %f"%(MinPerc,MaxPerc)
			Valid = True
		except ValueError as detail :
			logging.error("Couldn't convert limits to float")
		except AssertionError as detail :
			logging.error(detail)
		return Valid

	def MaxValidate(self) :
		logging.debug("validating max")
		Valid = False
		try :
			MinPerc = self.MinGet()
			MaxPerc = self.MaxGet()
			assert MaxPerc>MinPerc,"Upper limit %f must be greater than lower limit %f"%(MaxPerc,MinPerc)
			assert MaxPerc<=1,"Upper limit must be less than or equal to 1"
			Valid = True
		except ValueError as detail :
			logging.error("Couldn't convert limits to float")
		except AssertionError as detail :
			logging.error(detail)
		return Valid

	def MinReset(self,d,i,P,s,S,v,V,W) :
		widget = self.parent.nametowidget(W)
		self.MinEntry.delete(0,tki.END)
		self.MinEntry.insert(0,0)
		self.MinEntry.after_idle(lambda W,v: self.parent.nametowidget(W).configure(validate=v), W, v)

	def MaxReset(self,d,i,P,s,S,v,V,W) :
		widget = self.parent.nametowidget(W)
		self.MaxEntry.delete(0,tki.END)
		self.MaxEntry.insert(0,1)
		widget.after_idle(lambda W,v: self.parent.nametowidget(W).configure(validate=v), W, v)

	def MinGet(self) :
		MinPercStr = self.MinEntry.get()
		if MinPercStr != '' :
			MinPerc = float(MinPercStr)
		else :
			MinPerc = 0
		return MinPerc

	def MaxGet(self) :
		MaxPercStr = self.MaxEntry.get()
		if MaxPercStr != '' :
			MaxPerc = float(MaxPercStr)
		else :
			MaxPerc = 1
		return MaxPerc

	def MinMaxGet(self) :
		return self.MinGet(),self.MaxGet()

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
	root.wm_title("Test the word list adding dialog")
	EndConnection = WordListAddGUI(root,aa,"Add a word list")
	if EndConnection.result[0] is not None :
		logging.debug("Parameters to add new word list: %s"%str(EndConnection.result))
	else :
		logging.debug("No word list parameters returned")
