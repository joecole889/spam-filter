# -*- coding: utf-8 -*-
"""
Running this module as __main__ starts the application main GUI

Created on Wed Jan 27 16:24:00 2016

@author: Joseph R. Cole
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
	"""
	Design and logic for the Tkinter based main GUI of the learning curve application
	"""
	def __init__(self, root, **params) :
		"""
		Initialize the main GUI and shared variables for other threads.

		root - a parent object from Tkinter in which to draw the main GUI

		params - a dict() that allow the user to pass in parameters
			params['sqlpath'] -
				path to a json file with SQL commands for the main database
			params['pragmapath'] -
				path to a json file with PRAGMA commands for the main database
			params['tempsqlpath'] -
				path to a json file with SQL commands for a temporary database
			params['initialdir'] -
				a directory in which to start looking for a database file

		variables shared between threads -
			self.watchlock -
				a lock to protect variables watched by the PlotWorker thread
			self.watchlist -
				a list of values watched by the PlotWorker thread to control the state of the Plot
				all communication with the thread is accomplished by putting values on the PlotDataQ
				self.watchlist[0] -
					switches the plot x-axis between # training samples (false) and
					the cost or regularization parameters tried (true)
				self.watchlist[1][0] -
					location where a learning curve cross section is shown when watchlist[0] is true
				self.watchlist[1][1] -
					maximum extent of the # of training samples axis if watchlist[0] is false
				self.watchlist[2][0] -
					cost or regularization value for the displayed learning curve when watchlist[0] is false
				self.watchlist[2][1] -
					maximum extent of the cost/regularization axis if watchlist[0] is true
			self.datastore -
				a list of data tuples with the scores of trained solutions to be plotted as
				learning curves
			self.PlotDataQ -
				a Queue to use for interacting with the PlotWorker thread
			self.DBpath -
				path to the current feature vector database
			self.PauseLock - 
				A lock to prevent multiple CPU heavy threads from starting at once.
				all CPU heavy threads must be given this lock in the acquired state,
				releae the lock at the end of computations, and provide a stopping function
				to be attached to the Stop button in the GUI
		"""
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
		self.file_opt['initialdir'] = params['initialdir']
		self.file_opt['filetypes'] = [('database files','.sqlite3'),('all files','.*')]
		self.file_opt['title'] = 'Select a email database file or create a new one'

		self.DBobj = EmailSamplesDB(params['sqlpath'],params['pragmapath'],params['tempsqlpath'])
		self.StartPlotWorker()
		return

# Functions to define the GUI
	def DefineMenuBar(self, parent=None) :
		"""
		Define the menu bar for the main GUI including file, edit, and help menus
		Set the commands for callbacks when any of the available options is selected

		parent - a reference to the frame of the main GUI
		"""
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
		"""
		Initialize the left plane of the GUI
		primarily entry boxes and drop down lists to control which machine learning solutions to test

		parent - a reference to the frame of the main GUI
		"""
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
		# TODO: pass in a params dict to initialize these hard coded starting values
		self.MaxSamplesVal.insert(0,"1800")
		with self.watchlock :
			self.watchlist[1][1] = 1800
		self.MaxSamplesVal.bind("<FocusOut>",self.NewMaxSamps)
		self.MaxSamplesVal.bind("<Return>",self.NewMaxSamps)
		self.MaxSamplesVal.grid(row=1,column=1,sticky=tki.W)

		self.OutputStepLab = tki.Label(InputGrid,text="Output Step Size",anchor=tki.E,width=15,padx=5)
		self.OutputStepLab.grid(row=2,column=0)
		self.OutputStepVal= tki.Entry(InputGrid,width=7)
		# TODO: pass in a params dict to initialize these hard coded starting values
		self.OutputStepVal.insert(0,"600")
		self.OutputStepVal.grid(row=2,column=1,sticky=tki.W)

		self.CostListLab = tki.Label(InputGrid,text="List of costs to try",anchor=tki.E,width=15,padx=5)
		self.CostListLab.grid(row=3,column=0)
		self.CostListVal = tki.Entry(InputGrid,width=40)
		# TODO: pass in a params dict to initialize these hard coded starting values
		self.CostListVal.insert(0,"0.1, 0.3, 1, 3")
		# The above insert will be grabbed and added to the watchlist when the cost drop down is defined in DefinePlotTools()
		self.CostListVal.bind("<FocusOut>",self.UpdateCostList)
		self.CostListVal.bind("<Return>",self.UpdateCostList)
		self.CostListVal.grid(row=3,column=1,sticky=tki.W)

		return InputGrid

	def DefineButtons(self,parent=None) :
		"""
		Define Go and Stop buttons

		parent - a reference to a parent frame
		"""
		InputButtons = tki.Frame(parent,pady=25)
		self.GoButton = tki.Button(InputButtons,text="Generate\nCurves",justify=tki.CENTER,padx=2,command=self.Go)
		self.GoButton.pack(side=tki.LEFT,padx=5)

		# No command is defined because this button must be configured whenever a CPU heavy thread is started
		self.PauseButton = tki.Button(InputButtons,text="Stop\nExecution",justify=tki.CENTER,padx=10)
		self.PauseButton.pack(side=tki.LEFT,fill=tki.Y,padx=5)

		return InputButtons

	def DefinePlotTools(self,canvas,parent=None) :
		"""
		Define the zoom and pan tools for the learning curve plot

		parent - a reference to a parent frame
		"""
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
		"""
		Initialize the matplotlib canvas for plotting

		parent - a reference to a parent frame
		"""
		self.fighan = plt.Figure()
		self.ax = self.fighan.add_subplot(111)
		canvas = FigureCanvasTkAgg(self.fighan,parent)
		canvas.show()

		return canvas

	def DefineXSecButton(self,parent=None) :
		"""
		Define a button to toggle the plot between a learning curve and a cross section of curves where
		the x-axis becomes the cost or regularization values tried.  This is connected to self.watchlist[0]

		parent - a reference to a parent frame
		"""
		XSecButtonFrame = tki.Frame(parent,pady=15)
		self.XSecButton = tki.Button(XSecButtonFrame,text="Cross Section",command=self.ToggleXSec)
		self.XSecButton.pack()

		return XSecButtonFrame

# Function callbacks for GUI menu commands
	def PrepareExit(self) :
		"""
		Clean up and close the GUI
		"""
		self.LearningCurveCanvas.get_tk_widget().destroy()
		self.toolbar.destroy()
		self.root.destroy()
		return

	def NewDB(self) :
		"""
		Ask for a filename to create a new database file, then create a new database and initialize
		the required tables.
		"""
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
		"""
		Open a feature vector database file, extract the available word lists that feature vectors can be
		created against, and populate the word list drop down menu
		"""
		filename = tkFileDialog.askopenfilename(**self.file_opt)
		self.DBpath = filename
		WordLists = self.GetWordLists(filename)
		self.UpdateWordListDropDown(WordLists)
		return

	def CloseDB(self) :
		"""
		Forgets the path the database currently in use.  Should not need to actually close the connection
		because the connection should not be held open by any thread (that would block the database from
		other threads).
		"""
		assert self.DBobj.DB_Connect is None, "Expected database connection to already be closed, but it wasn't"
		self.DBPath = None
		self.UpdateWordListDropDown(None)
		return

# Functions that update user drop down lists in the GUI
	def UpdateCostList(self,_=None) :
		"""
		Update the drop down menu that is used to select the learning curve for the selected cost.
		Trigger a graph state change event if necessary.

		_ is an unused input that would contain metadata about a triggering event if this function is used as a widget's .bind() method
		"""
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
			ii = Cs.index(float(CurrentCostSelection))	#throws ValueError if the value isn't in the list
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
		"""
		Updates the values available in the word list drop down menu.
		The user should select the word list to create feature vectors against

		NewList - a list of tuples to define entrys for the word list drop down menu.  Each tuple is:
		("table name in the database for the word list","a human readable name for the word list")
		"""
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
		"""
		Return the value form the step entry box widget after checking for errors
		"""
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
		"""
		Return the value form the max training samples entry box widget after checking for errors
		"""
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
		"""
		Return the value form the cost list entry box widget after checking for errors.
		The user should input a comma separated list of non-negative floats
		"""
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
		"""
		Return the value of the current cost selection as a float
		"""
		coststr = self.CostListDropDownVar.get()
		try :
			cost = float(coststr)
		except ValueError as detail :
			logging.error("Couldn't convert selected cost value %s to a float: %s"%(coststr,detail))
			cost = None
		return cost

# Functions to get information from the database for the GUI
	def GetWordLists(self,filename) :
		"""
		Return a list of database tables with the feature vector word lists

		filename - a path to the current database in use (usually self.DBpath)
		"""
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
		"""
		Starts the CPU heavy thread that is used to train the algorithm instances based on user input from the GUI.
		The first action must be to acquire the PauseLock.  The thread itself must release the PauseLock when it
		finishes.

		_ is an unused input that would contain metadata about a triggering event if this function is used as a widget's .bind() method
		"""
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

			ParamSpace = dict()	#parameter space to check with trained algorithm instances
			ParamSpace['Step'] = step
			ParamSpace['MaxTraining'] = MaxTraining
			ParamSpace['WordList'] = listchoice
			ParamSpace['Costs'] = Cs
			# Initialize the training thread
			TrainThread = TrainSVMs(self.DBobj,self.DBpath,self.PauseButton,self.PauseLock,self.PlotDataQ,**ParamSpace)
			TrainThread.daemon = True	#terminate the thread immediately if the main GUI is closed
			# Configure the Stop button in case the user gets cold feet; the thread must provide a stop function
			self.PauseButton.configure(command=TrainThread.stop)
			# Start the training thread
			TrainThread.start()
		return
	
	def StartPlotWorker(self) :
		"""
		Start the thread that monitors the PlotDataQ and continuously updates the plot
		"""
		PlotThread = PlotWorker(self.PlotDataQ, self.datastore, self.ax, self.watchlist, self.watchlock)
		PlotThread.daemon = True
		PlotThread.start()
		return

# Functions to signal that graph changes are needed
	def ToggleXSec(self) :
		"""
		Toggles the state of the plot between a learning curve and a cross section of learning curves with
		different cost/regularization values.  Sends a graph state change signal to the PlotWorker thread.
		"""
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
		"""
		Updates the maximum cost watch variable for the PlotWorker() thread.  Sends the graph state change
		signal if necessary depending on the state of the cross section button in the main GUI

		NewCMax - a float to set as the new value of the maximum cost watch variable
		"""
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
		"""
		Updates the cost selection watch variable according to the user selection in the cost list drop down
		menu.  Triggers a graph state change signal if necessary depending on the state of the cross section
		button in the main GUI.

		_ is a list of arguments that may be automatically provided because this function is used as a callback for a trace on a Tkinter StringVar.  However, the data is not used in this function for anything.
		"""
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
		"""
		Updates the cost selection watch variable according to the user selection in the cost list drop down
		menu.  Triggers a graph state change signal if necessary depending on the state of the cross section
		button in the main GUI.

		_ is a list of arguments that may be automatically provided because this function is used as a
		callback for a trace on a Tkinter StringVar.  However, the data is not used in this function
		for anything.
		"""
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

###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.DEBUG)
	#pdb.set_trace()

	parser = argparse.ArgumentParser(description='Learning curve GUI for training SVMs to classify SPAM')
	parser.add_argument('--pragmapath','-p',
			            help='path to a json file with the PRAGMA commands for the database',
						default='.\DBSetup_SQL.json')
	parser.add_argument('--sqlpath','-s',
			            help='path to a json file with the SQL commands for the database',
						default='.\EmailSamplesDB_SQL.json')
	parser.add_argument('--tempsqlpath','-t',
			            help='path to a json file with the SQL commands for temp databases',
						default='.\TempDB_SQL.json')
	parser.add_argument('--initialdir','-d',
			            help='path to an initial directory to start looking for files',
						default='.')
	parser.add_argument('--version', action='version', version='%(prog)s 1.0')
	paramsobj = parser.parse_args()
	params = vars(paramsobj)

	root = tki.Tk()
	root.wm_title("Learning Curve Analysis")
	icon_image = tki.Image("photo",file=r".\MainGUI.gif")
	root.tk.call('wm','iconphoto',root._w,icon_image)
	MainWinHan = LearningCurveAppMainGUI(root,**params)
	root.mainloop()
