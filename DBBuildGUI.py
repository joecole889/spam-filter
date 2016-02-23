# -*- coding: utf-8 -*-
"""
Created on Tue Feb 09 16:03:00 2016

@author: JCole119213
"""

#import pdb

try :
	import Tkinter as tki
except ImportError :
	import tkinter as tki

import tkFileDialog

class DBBuildGUI(tki.Frame) :
	def __init__(self, root, *args, **kwargs) :
		tki.Frame.__init__(self, root, *args, **kwargs)
		self.root = root
		self.pack()

		self.SampleSetDistributionFrame = self.DefineSampleSetDistributionFrame()
		self.SampleSetDistributionFrame.grid(row=0,column=0,columnspan=2,pady=10,ipady=3,ipadx=3)

		self.GoodSamplesLabel = tki.Label(self,text="Enter a directory with legitimate email samples:").grid(row=1,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.GoodSamples = tki.Entry(self,width=100)
		self.GoodSamples.grid(row=2,column=0,sticky=tki.W,padx=5)

		self.SpamSamplesLabel = tki.Label(self,text="Enter a directory with spam samples:").grid(row=3,column=0,columnspan=2,sticky=tki.W,padx=5)
		self.SpamSamples = tki.Entry(self,width=100)
		self.SpamSamples.grid(row=4,column=0,sticky=tki.W,padx=5)

		# defining options for opening a directory
		self.legitdir_opt = options1 = {}
		options1['initialdir'] = 'C:\\'
		options1['mustexist'] = True
		options1['title'] = 'Select a directory with legitimate email examples'
		self.BrowseLegit = tki.Button(self,text="Browse",command=self.asklegitdirectory)
		self.BrowseLegit.grid(row=2,column=1,padx=5,pady=5)

		self.spamdir_opt = options2 = {}
		options2['initialdir'] = 'C:\\'
		options2['mustexist'] = True
		options2['title'] = 'Select a directory with spam examples'
		self.BrowseSpam = tki.Button(self,text="Browse",command=self.askspamdirectory)
		self.BrowseSpam.grid(row=4,column=1,padx=5,pady=5)

		self.ButtonsFrame = self.DefineButtonsFrame()
		self.ButtonsFrame.grid(row=5,column=0,columnspan=2)

		return

	def DefineSampleSetDistributionFrame(self) :
		SampleDistFrame = tki.Frame(self,relief=tki.SUNKEN,borderwidth=3)

		self.TargetDistributionsLabel = tki.Label(SampleDistFrame,text="Set Distribution Targets",font='TkHeadingFont 12').grid(row=0,columnspan=6,padx=30)

		self.TrainingPercentEntryLabel = tki.Label(SampleDistFrame,text="Training",width=8).grid(row=1,column=0,columnspan=2)
		self.CrossValPercentEntryLabel = tki.Label(SampleDistFrame,text="Cross Validation",width=16).grid(row=1,column=2,columnspan=2)
		self.TestPercentEntryLabel = tki.Label(SampleDistFrame,text="Test").grid(row=1,column=4,columnspan=2)

		self.TrainingPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.TrainingPercentEntry.insert(0,"60")
		self.TrainingPercentEntry.grid(row=2,column=0,sticky=tki.E)
		self.PercentLabel1 = tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=1,sticky=tki.W)
		self.CrossValPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.CrossValPercentEntry.insert(0,"20")
		self.CrossValPercentEntry.grid(row=2,column=2,sticky=tki.E)
		self.PercentLabel2 = tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=3,sticky=tki.W)
		self.TestPercentEntry = tki.Entry(SampleDistFrame,justify='center',width=5)
		self.TestPercentEntry.insert(0,"20")
		self.TestPercentEntry.grid(row=2,column=4,sticky=tki.E)
		self.PercentLabel3 = tki.Label(SampleDistFrame,text='%',width=1).grid(row=2,column=5,sticky=tki.W)

		self.DBDistributionsLabel = tki.Label(SampleDistFrame,text="Current DB Distribution",font='TkHeadingFont 12').grid(row=0,column=6,columnspan=3,padx=30)

		self.TrainingPercentLabel = tki.Label(SampleDistFrame,text="Training").grid(row=1,column=6)
		self.CrossValPercentLabel = tki.Label(SampleDistFrame,text="Cross Validation").grid(row=1,column=7)
		self.TestPercentLabel = tki.Label(SampleDistFrame,text="Test").grid(row=1,column=8)

		self.DBTrainingPercent = tki.Label(SampleDistFrame,text='0%').grid(row=2,column=6)
		self.DBCrossValPercent = tki.Label(SampleDistFrame,text='0%').grid(row=2,column=7)
		self.DBTestPercent = tki.Label(SampleDistFrame,text='0%').grid(row=2,column=8)

		return SampleDistFrame 

	def DefineButtonsFrame(self) :
		ButFrame = tki.Frame(self)
		self.AttachDBBut = tki.Button(ButFrame,text="Create/Attach DB")
		self.AttachDBBut.grid(row=0,column=0,padx=5)
		self.AddToDBBut = tki.Button(ButFrame,text="Add to DB")
		self.AddToDBBut.grid(row=0,column=1,padx=5)
		self.ResetDBBut = tki.Button(ButFrame,text="Reset DB")
		self.ResetDBBut.grid(row=0,column=2,padx=5)
		self.ConnectionLabel = tki.Label(ButFrame,text="Currently connected database: None",justify="left")
		self.ConnectionLabel.grid(row=1,column=0,columnspan=4,sticky=tki.W)

		return ButFrame

	def asklegitdirectory(self) :
		dirstr = tkFileDialog.askdirectory(**self.legitdir_opt)
		if dirstr :
			self.GoodSamples.delete(0,tki.END)
			self.GoodSamples.insert(0,dirstr)
			self.legitdir_opt['initialdir'] = dirstr
			if self.spamdir_opt['initialdir'] == 'C:\\' :
				self.spamdir_opt['initialdir'] = dirstr
		return

	def askspamdirectory(self) :
		dirstr = tkFileDialog.askdirectory(**self.spamdir_opt)
		if dirstr :
			self.SpamSamples.delete(0,tki.END)
			self.SpamSamples.insert(0,dirstr)
			self.spamdir_opt['initialdir'] = dirstr
			if self.legitdir_opt['initialdir'] == 'C:\\' :
				self.legitdir_opt['initialdir'] = dirstr
		return

################### Main Program ################### 

if __name__ == "__main__" :
	#pdb.set_trace()
	root = tki.Tk()
	root.wm_title("Build the email sample database")
	icon_image = tki.Image("photo",file=r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\MainGUI.gif")
	root.tk.call('wm','iconphoto',root._w,icon_image)
	MainWinHan = DBBuildGUI(root)
	root.mainloop()
