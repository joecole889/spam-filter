# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 16:24:00 2016

@author: JCole119213
"""

#import pdb
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import matplotlib.pyplot as plt

try :
	import Tkinter as tki
except ImportError :
	import tkinter as tki

class LearningCurveAppMainGUI(tki.Frame) :
	def __init__(self, root, *args, **kwargs) :
		tki.Frame.__init__(self, root, *args, **kwargs)
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

		return

	def PrepareExit(self) :
		self.LearningCurveCanvas.get_tk_widget().destroy()
		self.toolbar.destroy()
		self.root.destroy()

		return

	def DefineMenuBar(self, parent=None) :
		menubar = tki.Menu(parent)

		filemenu = tki.Menu(menubar, tearoff=0)
		filemenu.add_command(label="New")
		filemenu.add_command(label="Open")
		filemenu.add_command(label="Save")
		filemenu.add_command(label="Save as...")
		filemenu.add_command(label="Close")
		filemenu.add_separator()
		filemenu.add_command(label="Exit", command=self.PrepareExit)
		menubar.add_cascade(label="File", menu=filemenu)

		editmenu = tki.Menu(menubar, tearoff=0)
		editmenu.add_command(label="Undo")
		editmenu.add_separator()
		editmenu.add_command(label="Cut")
		editmenu.add_command(label="Copy")
		editmenu.add_command(label="Paste")
		editmenu.add_command(label="Delete")
		editmenu.add_command(label="Select All")
		menubar.add_cascade(label="Edit", menu=editmenu)

		helpmenu = tki.Menu(menubar, tearoff=0)
		helpmenu.add_command(label="Help Index")
		helpmenu.add_command(label="About...")
		menubar.add_cascade(label="Help", menu=helpmenu)

		return menubar

	def DefineInputTable(self,parent=None) :
		InputGrid = tki.Frame(parent,padx=75,pady=50)
		self.MaxSamplesLab = tki.Label(InputGrid,text="Max Samples",anchor=tki.E,width=13,padx=5)
		self.MaxSamplesLab.grid(row=0,column=0)
		self.MaxSamplesVal = tki.Entry(InputGrid,width=7)
		self.MaxSamplesVal.insert(0,"1600")
		self.MaxSamplesVal.grid(row=0,column=1,sticky=tki.W)

		self.OutputStepLab = tki.Label(InputGrid,text="Output Step Size",anchor=tki.E,width=13,padx=5)
		self.OutputStepLab.grid(row=1,column=0)
		self.OutputStepVal= tki.Entry(InputGrid,width=7)
		self.OutputStepVal.insert(0,"100")
		self.OutputStepVal.grid(row=1,column=1,sticky=tki.W)

		self.CostListLab = tki.Label(InputGrid,text="List of costs to try",anchor=tki.E,width=13,padx=5)
		self.CostListLab.grid(row=2,column=0)
		self.CostListVal = tki.Entry(InputGrid,width=40)
		self.CostListVal.insert(0,"0.01, 0.03, 0.1, 0.3, 1, 3, 10")
		self.CostListVal.bind("<FocusOut>",self.UpdateCostList)
		self.CostListVal.bind("<Return>",self.UpdateCostList)
		self.CostListVal.grid(row=2,column=1,sticky=tki.W)

		return InputGrid

	def DefineButtons(self,parent=None) :
		InputButtons = tki.Frame(parent,pady=25)
		self.GoButton = tki.Button(InputButtons,text="Generate\nCurves",justify=tki.CENTER,padx=2)
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
		

################### Main Program ################### 

if __name__ == "__main__" :
	#pdb.set_trace()
	root = tki.Tk()
	root.wm_title("Learning Curve Analysis")
	icon_image = tki.Image("photo",file=r"./MainGUI.gif")
	root.tk.call('wm','iconphoto',root._w,icon_image)
	MainWinHan = LearningCurveAppMainGUI(root)
	root.mainloop()
