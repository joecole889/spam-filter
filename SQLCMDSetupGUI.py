# -*- coding: utf-8 -*-
"""
Created on Tue Feb 09 16:03:00 2016

@author: JCole119213
"""

#import pdb
import Tkinter as tki
import tkFileDialog
import tkSimpleDialog
import logging
import os

class SQLCMDSetupGUI(tkSimpleDialog.Dialog) :
	def __init__(self,parent,title=None,**kwargs) :
		initdir = os.path.abspath(r'.')
		params = {'MainDBCMDs':os.path.join(initdir,r'EmailSamplesDB_SQL.json'),
				  'PragmaCMDs':os.path.join(initdir,r'DBSetup_SQL.json'),
				  'TempDBCMDs':os.path.join(initdir,r'TempDB_SQL.json')}
		params.update(**kwargs)

		self.CurrentMainSQL = params['MainDBCMDs']
		self.CurrentPragmaSQL = params['PragmaCMDs']
		self.CurrentTempSQL = params['TempDBCMDs']
		self.file_opt = {'initialdir':os.path.dirname(self.CurrentMainSQL),
		                 'filetypes':[('json files','.json'),('java script files','.js'),('all files','.*')]}
		tkSimpleDialog.Dialog.__init__(self, parent, title)

	def cancel(self,_=None) :
		logging.debug("Shutting down the dialog")
		self.parent.focus_set()
		self.destroy()
	
	def body(self,parent) :
		self.MainSQLEntry = tki.Entry(parent,width=100)
		self.MainSQLEntry.insert(0,self.CurrentMainSQL)
		self.MainSQLEntry.grid(row=0,column=0,padx=5,sticky=tki.W+tki.E)
		tki.Button(parent,text="Browse",command=self.MainSQL).grid(row=0,column=1,padx=5,pady=2)

		self.PragmaSQLEntry = tki.Entry(parent,width=100)
		self.PragmaSQLEntry.insert(0,self.CurrentPragmaSQL)
		self.PragmaSQLEntry.grid(row=1,column=0,padx=5,sticky=tki.W+tki.E)
		tki.Button(parent,text="Browse",command=self.PragmaSQL).grid(row=1,column=1,padx=5,pady=2)

		self.TempSQLEntry = tki.Entry(parent,width=100)
		self.TempSQLEntry.insert(0,self.CurrentTempSQL)
		self.TempSQLEntry.grid(row=2,column=0,padx=5,sticky=tki.W+tki.E)
		tki.Button(parent,text="Browse",command=self.TempSQL).grid(row=2,column=1,padx=5,pady=2)

		return self.MainSQLEntry

	def apply(self) :
		temptup = (self.MainSQLEntry.get(),self.PragmaSQLEntry.get(),self.TempSQLEntry.get())
		if all(os.path.isfile(filestr) for filestr in temptup) :
			self.result = temptup
		else :
			self.result = None

# Function callbacks for GUI buttons
	def MainSQL(self) :
		filenamestr = tkFileDialog.askopenfilename(**self.file_opt)
		if filenamestr :
			self.MainSQLEntry.delete(0,tki.END)
			self.MainSQLEntry.insert(0,filenamestr)
			self.file_opt['initialdir'] = os.path.dirname(filenamestr)
		return

	def PragmaSQL(self) :
		filenamestr = tkFileDialog.askopenfilename(**self.file_opt)
		if filenamestr :
			self.PragmaSQLEntry.delete(0,tki.END)
			self.PragmaSQLEntry.insert(0,filenamestr)
			self.file_opt['initialdir'] = os.path.dirname(filenamestr)
		return

	def TempSQL(self) :
		filenamestr = tkFileDialog.askopenfilename(**self.file_opt)
		if filenamestr :
			self.TempSQLEntry.delete(0,tki.END)
			self.TempSQLEntry.insert(0,filenamestr)
			self.file_opt['initialdir'] = os.path.dirname(filenamestr)
		return

###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()

	root = tki.Tk()
	root.wm_title("Test the SQL initialization dialog")
	initdir = os.path.abspath(r'.')
	EndConnection = SQLCMDSetupGUI(root,"Select new SQL command files")
	if EndConnection.result is not None :
		logging.debug("Got: %s"%str(EndConnection.result))
	else :
		logging.debug("No result returned")
