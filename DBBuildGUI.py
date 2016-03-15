# -*- coding: utf-8 -*-
"""
Created on Tue Feb 09 16:03:00 2016

@author: JCole119213
"""

#import pdb
import Tkinter as tki
import tkFileDialog
from EmailSamplesDB import EmailSamplesDB
import argparse
import logging
import os
from ProgressWindow import *

class DBBuildGUI(tki.Toplevel) :
	def __init__(self, parent, DBobj, *args, **kwargs) :
		try :
			initdir = kwargs['initialdir']
			del kwargs['initialdir']
		except :
			initdir = os.path.abspath(r'.')
		self.DBobj = DBobj
		self.parent = parent

		tki.Toplevel.__init__(self, parent)
		self.transient(parent)
		self.title("Build the sample database")
		self.result = None
		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		self.geometry("+%d+%d"%(parent.winfo_rootx()+50,
			                    parent.winfo_rooty()+50))

		self.SampleSetDistributionFrame = self.DefineSampleSetDistributionFrame()
		self.SampleSetDistributionFrame.grid(row=0,column=0,columnspan=2,pady=10,ipady=3,ipadx=3)

		tki.Label(self,text="Enter a directory with legitimate email samples:").grid(row=1,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.GoodSamples = tki.Entry(self,width=100)
		self.GoodSamples.grid(row=2,column=0,sticky=tki.W,padx=5)

		tki.Label(self,text="Enter a directory with spam samples:").grid(row=3,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.SpamSamples = tki.Entry(self,width=100)
		self.SpamSamples.grid(row=4,column=0,sticky=tki.W,padx=5)

		# defining options for opening a directory
		self.legitdir_opt = options1 = {}
		options1['initialdir'] = initdir
		options1['mustexist'] = True
		options1['title'] = 'Select a directory with legitimate email examples'
		self.BrowseLegit = tki.Button(self,text="Browse",command=self.asklegitdirectory)
		self.BrowseLegit.focus_set()
		self.BrowseLegit.grid(row=2,column=1,padx=5,pady=5)

		self.spamdir_opt = options2 = {}
		options2['initialdir'] = initdir
		options2['mustexist'] = True
		options2['title'] = 'Select a directory with spam examples'
		self.BrowseSpam = tki.Button(self,text="Browse",command=self.askspamdirectory)
		self.BrowseSpam.grid(row=4,column=1,padx=5,pady=5)

		self.ButtonsFrame = self.DefineButtonsFrame()
		self.ButtonsFrame.grid(row=5,column=0,columnspan=2,sticky=tki.W+tki.E,pady=20)

		self.dbfile_opt = {}
		self.dbfile_opt['initialdir'] = initdir
		self.dbfile_opt['filetypes'] = [('database files','.sqlite3'),('all files','.*')]

		self.bind("<Escape>",self.cancel)
		self.wait_window(self)
		return

	def cancel(self,_=None) :
		logging.debug("Shutting down the dialog")
		self.result = self.DBobj.DBpath
		self.parent.focus_set()
		self.destroy()
	
	def DefineSampleSetDistributionFrame(self) :
		SampleDistFrame = tki.Frame(self,relief=tki.SUNKEN,borderwidth=3)

		tki.Label(SampleDistFrame,text="Set Distribution Targets",font='TkHeadingFont 12').grid(row=0,columnspan=6,padx=30)

		tki.Label(SampleDistFrame,text="Training",width=8).grid(row=1,column=0,columnspan=2)
		tki.Label(SampleDistFrame,text="Cross Validation",width=16).grid(row=1,column=2,columnspan=2)
		tki.Label(SampleDistFrame,text="Test").grid(row=1,column=4,columnspan=2)

		self.TrainingPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.TrainingPercentEntry.insert(0,"60")
		self.TrainingPercentEntry.grid(row=2,column=0,sticky=tki.E)
		tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=1,sticky=tki.W)
		self.CrossValPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.CrossValPercentEntry.insert(0,"20")
		self.CrossValPercentEntry.grid(row=2,column=2,sticky=tki.E)
		tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=3,sticky=tki.W)
		self.TestPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.TestPercentEntry.insert(0,"20")
		self.TestPercentEntry.grid(row=2,column=4,sticky=tki.E)
		tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=5,sticky=tki.W)

		tki.Label(SampleDistFrame,text="Current DB Distribution",font='TkHeadingFont 12').grid(row=0,column=6,columnspan=3,padx=30)

		tki.Label(SampleDistFrame,text="Training").grid(row=1,column=6)
		tki.Label(SampleDistFrame,text="Cross Validation").grid(row=1,column=7)
		tki.Label(SampleDistFrame,text="Test").grid(row=1,column=8)

		self.DBTrainingPercent = tki.StringVar(SampleDistFrame)
		tki.Label(SampleDistFrame,textvariable=self.DBTrainingPercent).grid(row=2,column=6)
		self.DBCrossValPercent = tki.StringVar(SampleDistFrame)
		tki.Label(SampleDistFrame,textvariable=self.DBCrossValPercent).grid(row=2,column=7)
		self.DBTestPercent = tki.StringVar(SampleDistFrame)
		tki.Label(SampleDistFrame,textvariable=self.DBTestPercent).grid(row=2,column=8)
		self.UpdateDBDist()
		return SampleDistFrame 

	def UpdateDBDist(self) :
		logging.debug("Updating the DB distribution indicator")
		if self.DBobj.DBpath is not None :
			try :
				self.DBobj.ConnectDB(self.DBobj.DBpath)
				_,DBDist = self.DBobj.GetSampleDistribution()
				SampleCount = self.DBobj.GetSampleCount()
				self.DBobj.DisconnectDB()
				DBDist = [SetCount/SampleCount*100 for SetCount in DBDist]
			except ZeroDivisionError :
				DBDist = [0,0,0]
			except Exception as detail :
				logging.debug("Using default set distribution [0,0,0] due to error: %s"%detail)
				DBDist = [0,0,0]
		else :
			DBDist = [0,0,0]
		self.DBTrainingPercent.set("%.1f%%"%DBDist[0])
		self.DBCrossValPercent.set("%.1f%%"%DBDist[1])
		self.DBTestPercent.set("%.1f%%"%DBDist[2])
		return

	def GetTargetDBDist(self) :
		TargDBDist = [self.TrainingPercentEntry.get(),
				      self.CrossValPercentEntry.get(),
					  self.TestPercentEntry.get()]

		for ii,val in enumerate(TargDBDist) :
			try :
				TargDBDist[ii] = float(val)/100
				assert TargDBDist[ii]>=0 and TargDBDist[ii]<=1,"Sample distribution targets must be in the range [0,1]"
			except ValueError as detail :
				logging.error("Could not convert one of the sample distribution targets to a float: %s"%detail)
				TargDBDist[ii] = None
			except AssertionError as detail :
				logging.error(detail)
				TargDBDist[ii] = None

		if sum(TargDBDist) == 1 :
			return tuple(TargDBDist)
		else :
			logging.error("Total of the sample distribution targets must be 1")
			return (None,None,None)

	def DefineButtonsFrame(self) :
		ButFrame = tki.Frame(self)
		self.CreateDBBut = tki.Button(ButFrame,text="Create DB",command=self.NewDB)
		self.CreateDBBut.grid(row=0,column=0,padx=5,sticky=tki.W+tki.E)
		self.AttachDBBut = tki.Button(ButFrame,text="Attach DB",command=self.OpenDB)
		self.AttachDBBut.grid(row=0,column=1,padx=5,sticky=tki.W+tki.E)
		self.CloseDBBut = tki.Button(ButFrame,text="Close DB",command=self.CloseDB)
		self.CloseDBBut.grid(row=0,column=2,padx=5,sticky=tki.W+tki.E)
		self.AddToDBBut = tki.Button(ButFrame,text="Add to DB",command=self.AddDB)
		self.AddToDBBut.grid(row=0,column=3,padx=5,sticky=tki.W+tki.E)
		self.ResetDBBut = tki.Button(ButFrame,text="Reset DB",command=self.ResetDB)
		self.ResetDBBut.grid(row=0,column=4,padx=5,sticky=tki.W+tki.E)
		ButFrame.grid_columnconfigure(0,weight=1)
		ButFrame.grid_columnconfigure(1,weight=1)
		ButFrame.grid_columnconfigure(2,weight=1)
		ButFrame.grid_columnconfigure(3,weight=1)
		ButFrame.grid_columnconfigure(4,weight=1)
		self.connect_text = tki.StringVar(ButFrame)
		self.connect_text.set("Currently connected database: %s"%self.DBobj.DBpath)
		self.ConnectionLabel = tki.Label(ButFrame,textvariable=self.connect_text,justify="left")
		self.ConnectionLabel.grid(row=1,column=0,columnspan=5,sticky=tki.W)

		return ButFrame

# Function callbacks for GUI buttons
	def asklegitdirectory(self) :
		dirstr = tkFileDialog.askdirectory(**self.legitdir_opt)
		if dirstr :
			self.GoodSamples.delete(0,tki.END)
			self.GoodSamples.insert(0,dirstr)
			self.legitdir_opt['initialdir'] = dirstr
			if self.spamdir_opt['initialdir'] == os.path.abspath(r'.') :
				self.spamdir_opt['initialdir'] = dirstr
		return

	def askspamdirectory(self) :
		dirstr = tkFileDialog.askdirectory(**self.spamdir_opt)
		if dirstr :
			self.SpamSamples.delete(0,tki.END)
			self.SpamSamples.insert(0,dirstr)
			self.spamdir_opt['initialdir'] = dirstr
			if self.legitdir_opt['initialdir'] == os.path.abspath(r'.') :
				self.legitdir_opt['initialdir'] = dirstr
		return

	def NewDB(self) :
		"""
		Ask for a filename to create a new database file, then create a new database and initialize
		the required tables.
		"""
		self.dbfile_opt['title'] = 'Create a new email database file'
		filename = tkFileDialog.asksaveasfilename(**self.dbfile_opt)
		logging.debug('Connecting to database at %s'%filename)
		self.DBobj.ConnectDB(filename)
		logging.debug('Result: %s'%self.DBobj.DB_Connect)
		try :
			logging.debug('Creating fresh database at %s'%filename)
			self.DBobj.CreateDB()
		finally :
			logging.debug('Disconnecting database at %s'%self.DBobj.DB_Connect)
			self.DBobj.DisconnectDB()
			logging.debug('Result: %s'%self.DBobj.DB_Connect)
		self.connect_text.set("Currently connected database: %s"%self.DBobj.DBpath)
		self.UpdateDBDist()
		return

	def OpenDB(self) :
		"""
		Open a feature vector database file, extract the available word lists that feature vectors can be
		created against, and populate the word list drop down menu
		"""
		self.dbfile_opt['title'] = 'Select an existing email database file'
		filename = tkFileDialog.askopenfilename(**self.dbfile_opt)
		self.DBobj.DBpath = filename
		self.connect_text.set("Currently connected database: %s"%self.DBobj.DBpath)
		self.UpdateDBDist()
		return

	def CloseDB(self) :
		"""
		Forgets the path the database currently in use.  Should not need to actually close the connection
		because the connection should not be held open by any thread (that would block the database from
		other threads).
		"""
		assert self.DBobj.DB_Connect is None, "Expected database connection to already be closed, but it wasn't"
		self.DBobj.DBpath = None
		self.connect_text.set("Currently connected database: %s"%self.DBobj.DBpath)
		self.UpdateDBDist()
		return

	def AddDB(self) :
		"""
		"""
		def cmd(*args) :
			self.DBobj.ConnectDB()
			self.DBobj.AddToDB(*args)
			self.DBobj.DisconnectDB()

		TargDBDist = self.GetTargetDBDist()

		emailspath = self.GoodSamples.get()
		if emailspath :
			classname = str(self.DBobj.SQLCMDs['ClassesList'][0])
			args = [emailspath,classname,TargDBDist]
			ProgressWindow(self,cmd,*args,title="Progress adding emails")

		spampath = self.SpamSamples.get()
		if spampath :
			classname = str(self.DBobj.SQLCMDs['ClassesList'][1])
			args = [spampath,classname,TargDBDist]
			ProgressWindow(self,cmd,*args,title="Progress adding spam")

		self.UpdateDBDist()
		return

	def ResetDB(self) :
		self.DBobj.ConnectDB()
		try :
			self.DBobj.ResetDB()
			self.DBobj.CreateDB()
		except Exception as detail :
			logging.error(detail)
		finally :
			self.DBobj.DisconnectDB()
			self.UpdateDBDist()

###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()

	parser = argparse.ArgumentParser(description='Email samples database building GUI')
	parser.add_argument('--pragmapath','-p',
			            help='path to a json file with the PRAGMA commands for the database',
						default=os.path.abspath(r'.\DBSetup_SQL.json'))
	parser.add_argument('--sqlpath','-s',
			            help='path to a json file with the SQL commands for the database',
						default=os.path.abspath(r'.\EmailSamplesDB_SQL.json'))
	parser.add_argument('--tempsqlpath','-t',
			            help='path to a json file with the SQL commands for temp databases',
						default=os.path.abspath(r'.\TempDB_SQL.json'))
	parser.add_argument('--initialdir','-d',
			            help='path to an initial directory to start looking for files',
						default=os.path.abspath(r'.'))
	parser.add_argument('--version', action='version', version='%(prog)s 1.0')
	paramsobj = parser.parse_args()
	params = vars(paramsobj)

	testDB = EmailSamplesDB(params['sqlpath'],params['pragmapath'],params['tempsqlpath'])

	root = tki.Tk()
	root.wm_title("Test the database building dialog")
	icon_image = tki.Image("photo",file=os.path.abspath(r".\MainGUI.gif"))
	root.tk.call('wm','iconphoto',root._w,icon_image)
	initdir = os.path.abspath(r'.')
	DBBuildGUI(root,testDB,initialdir=initdir)
