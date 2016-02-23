# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 16:24:00 2016

@author: JCole119213
"""

#import pdb
import argparse
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import matplotlib.pyplot as plt
import tkFileDialog
import logging
from EmailSamplesDB import *
from sklearn.svm import SVC

try :
	import Tkinter as tki
except ImportError :
	import tkinter as tki

class LearningCurveAppMainGUI(tki.Frame) :
	def __init__(self, root, **params) :
		self.params = params
		tki.Frame.__init__(self, root)
		self.root = root
		self.pack()

		self.MenuBar = self.DefineMenuBar(root)
		root.config(menu=self.MenuBar)

		self.InputPane = tki.Frame(root)
		self.InputPane.pack(side=tki.LEFT,expand=True,fill=tki.BOTH)
		self.InputGrid = self.DefineInputTable(self.InputPane)
		self.InputGrid.pack(side=tki.TOP,fill=tki.X,expand=True)
		self.InputButtons = self.DefineButtons(self.InputPane)
		self.InputButtons.pack(side=tki.BOTTOM)

		self.OutputPane = tki.Frame(root)
		self.OutputPane.pack(side=tki.LEFT,expand=True,fill=tki.BOTH)

		self.LearningCurveCanvas = self.DefinePlotCanvas(self.OutputPane)
		self.PlotTools = self.DefinePlotTools(self.LearningCurveCanvas,self.OutputPane)
		self.CrossSectionButton = self.DefineXSecButton(self.OutputPane)
		self.PlotTools.pack(fill=tki.X,expand=True,side=tki.TOP)
		self.LearningCurveCanvas.get_tk_widget().pack(fill=tki.BOTH,expand=True,side=tki.TOP)
		self.CrossSectionButton.pack(side=tki.TOP,pady=25)

		self.file_opt = {}
		self.file_opt['initialdir'] = 'C:\\'
		self.file_opt['filetypes'] = [('database files','.sqlite3'),('all files','.*')]
		self.file_opt['title'] = 'Select a email database file or create a new one'

		self.DBobj = EmailSamplesDB(params['sqlpath'],params['pragmapath'],params['tempsqlpath'])
		return

	def PrepareExit(self) :
		self.LearningCurveCanvas.get_tk_widget().destroy()
		self.toolbar.destroy()
		self.root.destroy()

		return

	def DefineMenuBar(self, parent=None) :
		menubar = tki.Menu(parent)

		filemenu = tki.Menu(menubar, tearoff=0)
		filemenu.add_command(label="New Database...")
		filemenu.add_command(label="Open Database...", command=self.ConnectDB)
		filemenu.add_command(label="Close Database", command=self.DisconnectDB)
		filemenu.add_separator()
		filemenu.add_command(label="Load Word List from File...")
		filemenu.add_command(label="Save Word List to File...")
		filemenu.add_separator()
		filemenu.add_command(label="Save SVM")
		filemenu.add_command(label="Save SVM as...")
		filemenu.add_separator()
		filemenu.add_command(label="Exit", command=self.PrepareExit)
		menubar.add_cascade(label="File", menu=filemenu)

		editmenu = tki.Menu(menubar, tearoff=0)
		editmenu.add_command(label="Add Samples to DB...")
		editmenu.add_command(label="Add Dictionary to DB...")
		editmenu.add_command(label="Select Words for List...")
		editmenu.add_command(label="Set SQL Command Paths...")
		menubar.add_cascade(label="Edit", menu=editmenu)

		helpmenu = tki.Menu(menubar, tearoff=0)
		helpmenu.add_command(label="About...")
		menubar.add_cascade(label="Help", menu=helpmenu)

		return menubar

	def ConnectDB(self) :
		filename = tkFileDialog.askopenfilename(**self.file_opt)
		logging.debug('Connecting to database at %s'%filename)
		self.DBobj.ConnectDB(filename)
		logging.debug('Result: %s'%self.DBobj.DB_Connect)
		WordLists = self.DBobj.GetAvailableWordLists()
		self.UpdateWordListDropDown(WordLists)
		return

	def DisconnectDB(self) :
		logging.debug('Disconnecting database at %s'%self.DBobj.DB_Connect)
		self.DBobj.DisconnectDB()
		logging.debug('Result: %s'%self.DBobj.DB_Connect)
		self.UpdateWordListDropDown(None)
		return

	def DefineInputTable(self,parent=None) :
		InputGrid = tki.Frame(parent,padx=75,pady=50)

		self.WordListsLab = tki.Label(InputGrid,text="Word List Selection",anchor=tki.E,width=15,padx=5)
		self.WordListsLab.grid(row=0,column=0)
		self.WordListsVar = tki.StringVar(InputGrid)
		self.WordListsVal = tki.OptionMenu(InputGrid,self.WordListsVar,None)
		self.UpdateWordListDropDown(None)
		self.WordListsVal.grid(row=0,column=1,sticky=tki.W)

		self.MaxSamplesLab = tki.Label(InputGrid,text="Max Samples",anchor=tki.E,width=15,padx=5)
		self.MaxSamplesLab.grid(row=1,column=0)
		self.MaxSamplesVal = tki.Entry(InputGrid,width=7)
		self.MaxSamplesVal.insert(0,"1600")
		self.MaxSamplesVal.grid(row=1,column=1,sticky=tki.W)

		self.OutputStepLab = tki.Label(InputGrid,text="Output Step Size",anchor=tki.E,width=15,padx=5)
		self.OutputStepLab.grid(row=2,column=0)
		self.OutputStepVal= tki.Entry(InputGrid,width=7)
		self.OutputStepVal.insert(0,"100")
		self.OutputStepVal.grid(row=2,column=1,sticky=tki.W)

		self.CostListLab = tki.Label(InputGrid,text="List of costs to try",anchor=tki.E,width=15,padx=5)
		self.CostListLab.grid(row=3,column=0)
		self.CostListVal = tki.Entry(InputGrid,width=40)
		self.CostListVal.insert(0,"0.01, 0.03, 0.1, 0.3, 1, 3, 10")
		self.CostListVal.bind("<FocusOut>",self.UpdateCostList)
		self.CostListVal.bind("<Return>",self.UpdateCostList)
		self.CostListVal.grid(row=3,column=1,sticky=tki.W)

		return InputGrid

	def DefineButtons(self,parent=None) :
		InputButtons = tki.Frame(parent,pady=25)
		self.GoButton = tki.Button(InputButtons,text="Generate\nCurves",justify=tki.CENTER,padx=2)
		self.GoButton.bind("<ButtonRelease-1>",self.Go)
		self.GoButton.pack(side=tki.LEFT,padx=5)
		self.PauseButton = tki.Button(InputButtons,text="Pause",justify=tki.CENTER,padx=10)
		self.PauseButton.pack(side=tki.LEFT,fill=tki.Y,padx=5)

		return InputButtons

	def DefinePlotTools(self,canvas,parent=None) :
		outcontrols = tki.Frame(parent)
		self.toolbar = NavigationToolbar2TkAgg(canvas,outcontrols)
		self.toolbar.pack(side=tki.LEFT,fill=tki.Y)
		self.toolbar.update()

		self.CostListDropDownVar = tki.StringVar(outcontrols)
		self.CostDropDown = tki.OptionMenu(outcontrols,self.CostListDropDownVar,None)
		self.UpdateCostList()
		self.CostDropDown.pack(side=tki.RIGHT,fill=tki.Y)

		return outcontrols

	def DefinePlotCanvas(self,parent=None) :
		self.fighan = plt.Figure()
		self.ax = self.fighan.add_subplot(111)
		canvas = FigureCanvasTkAgg(self.fighan,parent)
		canvas.show()

		return canvas

	def DefineXSecButton(self,parent=None) :
		XSecButtonFrame = tki.Frame(parent,pady=15)
		self.XSecButton = tki.Button(XSecButtonFrame,text="Cross Section")
		self.XSecButton.pack()

		return XSecButtonFrame

	def UpdateCostList(self,_=None) :
		CostListStr = self.CostListVal.get()
		self.CostDropDown['menu'].delete(0,'end')

		for ii,CostStr in enumerate(CostListStr.split(',')) :
			CostStr = CostStr.strip()
			if ii == 0 :
				self.CostListDropDownVar.set(CostStr)
			self.CostDropDown['menu'].add_command(label=CostStr, command=tki._setit(self.CostListDropDownVar, CostStr))

		return

	def UpdateWordListDropDown(self,NewList) :
		self.WordListsVal['menu'].delete(0,'end')
		if NewList is not None :
			self.WordListsVar.set(str(NewList[0][0]))
			for choice,readable in NewList :
				choicestr = '%s: %s'%(choice,readable)
				self.WordListsVal['menu'].add_command(label=choicestr, command=tki._setit(self.WordListsVar, str(choice)))
		else :
			self.WordListsVar.set('')

		return

	def Go(self,_=None) :
		jj = 0
		clfs = []
		Xtrain = []
		Ytrain = []

		step = self.GetStep()
		if step is None :
			return
		Cs = self.GetCostList()
		if Cs is None :
			return
		MaxTraining = self.GetMaxTraining()
		if MaxTraining is None :
			return
		NumTraining = self.DBobj.GetTrainSampleCount()
		NumTraining = min(NumTraining,MaxTraining)

		listchoice = self.WordListsVar.get()
		Xcv,Ycv = self.DBobj.GetXY(listchoice,1)
		for m in range(0,NumTraining,step) :
			Xs,Ys = self.DBobj.GetXY(listchoice,0,step,m)
			Xtrain.extend(Xs)
			Ytrain.extend(Ys)
			for cost in Cs :
				clfs.append(SVC(C=cost,kernel='linear'))
				clfs[jj].fit(Xtrain,Ytrain)
				TrainScore = clfs[jj].score(Xtrain,Ytrain)
				CVScore = clfs[jj].score(Xcv,Ycv)
				logging.debug('%d, %d, %f, %f, %f'%(jj, m+step, cost, TrainScore, CVScore))
				jj += 1
			self.UpdatePlot()
		Xtest,Ytest = self.DBobj.GetXY(listchoice,2)
		TestScore = clfs[-1].score(Xtest,Ytest)
		logging.debug("SVM test result: %d, %d, %f, %f"%(jj-1,m+step,cost,TestScore))
		return
	
	def UpdatePlot(self) :
		pass
		return

	def GetStep(self) :
		stepstr = self.OutputStepVal.get()
		try :
			step = int(stepstr)
		except ValueError as detail :
			logging.error("Couldn't convert given step value %s to an integer: %s"%(stepstr,detail))
			step = None
		return step

	def GetMaxTraining(self) :
		maxsampstr = self.MaxSamplesVal.get()
		try :
			maxsamp = int(maxsampstr)
		except ValueError as detail :
			logging.error("Couldn't convert given max sample value %s to an integer: %s"%(maxsampstr,detail))
			maxsamp = None
		return maxsamp

	def GetCostList(self) :
		CostListStr = self.CostListVal.get()
		try :
			Cs = [float(cost.strip()) for cost in CostListStr.split(',')]
		except ValueError as detail :
			logging.error("Couldn't convert given cost list value %s to a list of floats: %s"%(CostListStr,detail))
			Cs = None
		return Cs

################### Main Program ################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()

	parser = argparse.ArgumentParser(description='Learning curve GUI for training SVMs to classify SPAM')
	parser.add_argument('--pragmapath','-p',help='path to a json file with the PRAGMA commands for the database',default='.\DBSetup_SQL.json')
	parser.add_argument('--sqlpath','-s',help='path to a json file with the SQL commands for the database',default='.\EmailSamplesDB_SQL.json')
	parser.add_argument('--tempsqlpath','-t',help='path to a json file with the SQL commands for temp databases',default='.\TempDB_SQL.json')
	parser.add_argument('--version',action='version', version='%(prog)s 1.0')
	paramsobj = parser.parse_args()
	params = vars(paramsobj)

	root = tki.Tk()
	root.wm_title("Learning Curve Analysis")
	icon_image = tki.Image("photo",file=r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\MainGUI.gif")
	root.tk.call('wm','iconphoto',root._w,icon_image)
	MainWinHan = LearningCurveAppMainGUI(root,**params)
	root.mainloop()
