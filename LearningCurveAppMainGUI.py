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
import threading
from TrainSVMs import *
from PlotWorker import *

try :
	import Tkinter as tki
except ImportError :
	import tkinter as tki

class LearningCurveAppMainGUI(tki.Frame) :
	def __init__(self, root, **params) :
		self.params = params
		self.watchlock = threading.Lock()
		self.PauseLock = threading.Lock()
		self.PlotDataQ = Queue.Queue()
		self.datastore = []
		self.watchlist = [False,[600,-1],[-1,-1]]
		self.DBpath = None

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
		self.file_opt['initialdir'] = r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\\"
		self.file_opt['filetypes'] = [('database files','.sqlite3'),('all files','.*')]
		self.file_opt['title'] = 'Select a email database file or create a new one'

		self.DBobj = EmailSamplesDB(params['sqlpath'],params['pragmapath'],params['tempsqlpath'])
		self.StartPlotWorker()
		return

# Functions to define the GUI
	def DefineMenuBar(self, parent=None) :
		menubar = tki.Menu(parent)

		filemenu = tki.Menu(menubar, tearoff=0)
		filemenu.add_command(label="New Database...",command=self.NewDB)
		filemenu.add_command(label="Open Database...", command=self.OpenDB)
		filemenu.add_command(label="Close Database", command=self.CloseDB)
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
		self.MaxSamplesVal.insert(0,"1800")
		with self.watchlock :
			self.watchlist[1][1] = 1800
		self.MaxSamplesVal.bind("<FocusOut>",self.NewMaxSamps)
		self.MaxSamplesVal.bind("<Return>",self.NewMaxSamps)
		self.MaxSamplesVal.grid(row=1,column=1,sticky=tki.W)

		self.OutputStepLab = tki.Label(InputGrid,text="Output Step Size",anchor=tki.E,width=15,padx=5)
		self.OutputStepLab.grid(row=2,column=0)
		self.OutputStepVal= tki.Entry(InputGrid,width=7)
		self.OutputStepVal.insert(0,"600")
		self.OutputStepVal.grid(row=2,column=1,sticky=tki.W)

		self.CostListLab = tki.Label(InputGrid,text="List of costs to try",anchor=tki.E,width=15,padx=5)
		self.CostListLab.grid(row=3,column=0)
		self.CostListVal = tki.Entry(InputGrid,width=40)
		self.CostListVal.insert(0,"0.1, 0.3, 1, 3")
		# The above insert will be grabbed and added to the watchlist when the cost drop down is defined in DefinePlotTools()
		self.CostListVal.bind("<FocusOut>",self.UpdateCostList)
		self.CostListVal.bind("<Return>",self.UpdateCostList)
		self.CostListVal.grid(row=3,column=1,sticky=tki.W)

		return InputGrid

	def DefineButtons(self,parent=None) :
		InputButtons = tki.Frame(parent,pady=25)
		self.GoButton = tki.Button(InputButtons,text="Generate\nCurves",justify=tki.CENTER,padx=2,command=self.Go)
		self.GoButton.pack(side=tki.LEFT,padx=5)
		self.PauseButton = tki.Button(InputButtons,text="Stop\nExecution",justify=tki.CENTER,padx=10)
		self.PauseButton.pack(side=tki.LEFT,fill=tki.Y,padx=5)

		return InputButtons

	def DefinePlotTools(self,canvas,parent=None) :
		outcontrols = tki.Frame(parent)
		self.toolbar = NavigationToolbar2TkAgg(canvas,outcontrols)
		self.toolbar.pack(side=tki.LEFT,fill=tki.Y)
		self.toolbar.update()

		self.CostListDropDownVar = tki.StringVar(outcontrols)
		self.CostListDropDownVar.trace("w", self.NewCostSelect)
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
		self.XSecButton = tki.Button(XSecButtonFrame,text="Cross Section",command=self.ToggleXSec)
		self.XSecButton.pack()

		return XSecButtonFrame

# Function callbacks for GUI menu commands
	def PrepareExit(self) :
		self.LearningCurveCanvas.get_tk_widget().destroy()
		self.toolbar.destroy()
		self.root.destroy()
		return

	def NewDB(self) :
		filename = tkFileDialog.asksaveasfilename(**self.file_opt)
		self.DBpath = filename
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
		return

	def OpenDB(self) :
		filename = tkFileDialog.askopenfilename(**self.file_opt)
		self.DBpath = filename
		WordLists = self.GetWordLists(filename)
		self.UpdateWordListDropDown(WordLists)
		return

	def CloseDB(self) :
		assert self.DBobj.DB_Connect is None, "Expected database connection to already be closed, but it wasn't"
		self.DBPath = None
		self.UpdateWordListDropDown(None)
		return

# Functions that update user drop down lists in the GUI
	def UpdateCostList(self,_=None) :
		CurrentCostSelection = self.CostListDropDownVar.get()
		logging.debug("Current cost selection is %s"%CurrentCostSelection)

		# Do the actual drop down menu update
		Cs = self.GetCostList()
		Cs.sort()
		self.CostDropDown['menu'].delete(0,'end')
		for ii,C in enumerate(Cs) :
			CostStr = str(C)
			self.CostDropDown['menu'].add_command(label=CostStr, command=tki._setit(self.CostListDropDownVar, CostStr))

		# Check if it's possible to keep the previously selected cost
		try :
			ii = Cs.index(float(CurrentCostSelection))
			NewCostSelection = Cs[ii]
		except ValueError as detail :
			logging.debug("New cost list doesn't contain the previous cost selection.")
			NewCostSelection = Cs[0]
		logging.debug("New cost selection is %s"%NewCostSelection)

		# Grab the current graph state variables
		with self.watchlock :
			tempcost,tempcostmax = self.watchlist[2]
		logging.debug("Cost watch values are: %f of %f"%(tempcost,tempcostmax))

		# Trigger a graph update event if needed; only one of these will trigger a graph state change according to the xsec button status
		if (Cs[-1] != tempcostmax) :
			self.NewCostMax(Cs[-1])
		if (NewCostSelection != tempcost) :
			self.CostListDropDownVar.set(str(NewCostSelection))
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

# Functions to get user input from the GUI
	def GetStep(self) :
		stepstr = self.OutputStepVal.get()
		try :
			step = int(stepstr)
			assert step>=0,"Number of training samples per step must be non-negative."
		except ValueError as detail :
			logging.error("Couldn't convert given step value %s to an integer: %s"%(stepstr,detail))
			step = None
		except AssertionError as detail :
			logging.error(detail)
			step = None
		return step

	def GetMaxTraining(self) :
		maxsampstr = self.MaxSamplesVal.get()
		try :
			maxsamp = int(maxsampstr)
			assert maxsamp>=0,"Maximum number of training samples must be non-negative."
		except ValueError as detail :
			logging.error("Couldn't convert given max sample value %s to an integer: %s"%(maxsampstr,detail))
			maxsamp = None
		except AssertionError as detail :
			logging.error(detail)
			maxsamp = None
		return maxsamp

	def GetCostList(self) :
		CostListStr = self.CostListVal.get()
		try :
			Cs = [float(cost.strip()) for cost in CostListStr.split(',')]
			assert all(cost >= 0 for cost in Cs),"The given cost values must be non-negative."
		except ValueError as detail :
			logging.error("Couldn't convert given cost list value %s to a list of floats: %s"%(CostListStr,detail))
			Cs = None
		except AssertionError as detail :
			logging.error(detail)
			Cs = None
		return Cs

	def GetCostSelect(self) :
		coststr = self.CostListDropDownVar.get()
		try :
			cost = float(coststr)
		except ValueError as detail :
			logging.error("Couldn't convert selected cost value %s to a float: %s"%(coststr,detail))
			cost = None
		return cost

# Functions to get information from the database for the GUI
	def GetWordLists(self,filename) :
		logging.debug('Connecting to database at %s'%filename)
		self.DBobj.ConnectDB(filename)
		logging.debug('Result: %s'%self.DBobj.DB_Connect)
		try :
			WordLists = self.DBobj.GetAvailableWordLists()
		finally :
			logging.debug('Disconnecting database at %s'%self.DBobj.DB_Connect)
			self.DBobj.DisconnectDB()
			logging.debug('Result: %s'%self.DBobj.DB_Connect)
		return WordLists

# Functions to start other threads
	def Go(self,_=None) :
		got_lock = self.PauseLock.acquire(False)
		if got_lock :
			step = self.GetStep()
			if step is None :
				return
			Cs = self.GetCostList()
			if Cs is None :
				return
			MaxTraining = self.GetMaxTraining()
			if MaxTraining is None :
				return

			listchoice = self.WordListsVar.get()

			ParamSpace = dict()
			ParamSpace['Step'] = step
			ParamSpace['MaxTraining'] = MaxTraining
			ParamSpace['WordList'] = listchoice
			ParamSpace['Costs'] = Cs
			TrainThread = TrainSVMs(self.DBobj,self.DBpath,self.PauseButton,self.PauseLock,self.PlotDataQ,**ParamSpace)
			TrainThread.daemon = True
			self.PauseButton.configure(command=TrainThread.stop)
			TrainThread.start()
		return
	
	def StartPlotWorker(self) :
		PlotThread = PlotWorker(self.PlotDataQ, self.datastore, self.ax, self.watchlist, self.watchlock)
		PlotThread.daemon = True
		PlotThread.start()
		return

# Functions to signal that graph changes are needed
	def ToggleXSec(self) :
		with self.watchlock :
			self.watchlist[0] = tempvar = not self.watchlist[0]
		if tempvar :
			self.XSecButton.config(relief=tki.SUNKEN)
		else :
			self.XSecButton.config(relief=tki.RAISED)
		try :
			logging.debug("Sending graph state change signal ToggleXSec().")
			self.PlotDataQ.put(None)
		except Exception as detail :
			logging.error("Failed to send graph state change signal: %s"%detail)

	def NewCostMax(self,NewCMax) :
		with self.watchlock :
			temp_xsec_state = self.watchlist[0]
			self.watchlist[2][1] = NewCMax
		if temp_xsec_state :
			try :
				logging.debug("Sending graph state change signal NewCostMax().")
				self.PlotDataQ.put(None)
			except Exception as detail :
				logging.error("Failed to send graph state change signal: %s"%detail)
		else :
			logging.debug("No need to send graph state change signal from NewCostMax() due to cross section button state.")

	def NewCostSelect(self,*_) :
		with self.watchlock :
			temp_xsec_state = self.watchlist[0]
			self.watchlist[2][0] = self.GetCostSelect()
		if not temp_xsec_state :
			try :
				logging.debug("Sending graph state change signal NewCostSelect().")
				self.PlotDataQ.put(None)
			except Exception as detail :
				logging.error("Failed to send graph state change signal: %s"%detail)
		else :
			logging.debug("No need to send graph state change signal from NewCostSelect() due to cross section button state.")

	def NewMaxSamps(self,*_) :
		with self.watchlock :
			temp_xsec_state = self.watchlist[0]
			CurrentMaxSamp = self.watchlist[1][1]
			NewMaxSamp = self.GetMaxTraining()
			self.watchlist[1][1] = NewMaxSamp
		if not temp_xsec_state and (NewMaxSamp != CurrentMaxSamp):
			try :
				logging.debug("Sending graph state change signal NewMaxSamps().")
				self.PlotDataQ.put(None)
			except Exception as detail :
				logging.error("Failed to send graph state change signal: %s"%detail)
		else :
			logging.debug("No need to send graph state change signal from NewMaxSamps().")

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
	icon_image = tki.Image("photo",file=r".\MainGUI.gif")
	root.tk.call('wm','iconphoto',root._w,icon_image)
	MainWinHan = LearningCurveAppMainGUI(root,**params)
	root.mainloop()
