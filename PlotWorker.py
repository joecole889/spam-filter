# -*- coding: utf-8 -*-
"""
This module implements a class derived from the Thread class in the threading module to encapsulate the
execution of the PlotWorker thread.

Created on Wed Feb 24 15:39:00 2016

@author: JCole119213
"""

import logging
import threading
import Queue
from operator import itemgetter
from matplotlib.lines import Line2D
import time

class PlotWorker(threading.Thread) :
	def __init__(self, PlotDataQ, datastore, ax, watchlist, watchlock) :
		"""
		Initialize references to variables shared with the main thread of execution in the LearningCurveApp
		module

		variables shared between threads -
			self.PlotDataQ -
				a Queue to use for interacting with the main thread
					contains 'None' signal to indicate a change of graph state, *or*
					contains a data tuple with: (MachineLearningObject, NumberOfTrainingSamplesUsed, CostUsed, TrainingScore, CrossValidationScore)
			self.datastore -
				a list of data tuples with the scores of trained solutions to be plotted as
				learning curves
			self.ax -
				a reference to the matplotlib axes in the main GUI (where this thread will plot data)
			self.watchlist -
				a list of values updated by the main thread to control the state of the plot.
				All communication between threads is accomplished by putting values on the PlotDataQ (None indicates the watchlist changed)

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
			self.watchlock -
				a lock to protect variables watched by the PlotWorker thread

		Parameters:
			self.params['RedrawDelay'] -
				parameter to control the sleep time between redrawing the axes animating the graph lines; this
				is needed because matplotlib is *not* technically thread safe
		"""
		super(PlotWorker,self).__init__()
		self.PlotDataQ = PlotDataQ
		self.datastore = datastore

		self.ax = ax
		self.canvas = ax.figure.canvas
		self.init_plot()

		self.watchlist = watchlist
		self.watchlock = watchlock
		# TODO: make this configurable from and optional dictionary passed into this constructor
		self.params = {'RedrawDelay':0.6}
		return

	def init_plot(self) :
		"""
		Setup the plot for the first time (runs with this thread is first started). Sets a callback executed
		when a draw event occurs to store the background of the plot.

		internal variables -
			self.xdata -
				x coordinates of the data to plot
			self.ytdata -
				y coordinates of the data to plot for the training score line
			self.ycvdata -
				y coordinate of the data to plot for the cross validation score line
		"""
		self.xdata = []
		self.ytdata = []
		self.ycvdata = []
		self.linet = Line2D(self.xdata, self.ytdata, animated=True, label='Training')
		self.linecv = Line2D(self.xdata, self.ycvdata, animated=True, color='r', label='Cross Validation')
		self.ax.add_line(self.linet)
		self.ax.add_line(self.linecv)
		self.background = None
		self.canvas.mpl_connect('draw_event', self.update_background)
		self.ax.set_ylim(0,1.05)
		self.ax.set_ylabel('Error')
		self.ax.set_xlabel('Number of Training Samples')
		self.ax.legend()
		self.ax.figure.canvas.draw()

	def update_background(self, _=None):
		"""
		Store the plot background (all the static elements) for more efficient line animations on top

		_ is an unused argument that is automatically passed to the function when it is used as a draw event
		based binding containing information about the triggering event (see init_plot())
		"""
		logging.debug("Storing background due to draw event.")
		self.background = self.canvas.copy_from_bbox(self.ax.bbox)

	def run(self) :
		"""
		Main execution loop for the PlotWorker thread; called when the main thread of execution starts
		this thread. Blocks until data or a 'None' signal it put on the PlotDataQ from outside.
		"""
		while True :
			try :
				data_tup = self.PlotDataQ.get()
				#logging.debug("Got data_tup %s from queue"%str(data_tup))
				start_t = time.time()

				# Copy watches to temp variables for thread safety
				with self.watchlock :
					x = self.watchlist[0]
					m = self.watchlist[1][0]
					mm = self.watchlist[1][1]
					c = self.watchlist[2][0]
					mc = self.watchlist[2][1]

				if data_tup is not None :
					# 1) Update the datastore
					self.datastore.append(data_tup)
					ii = self.getIndexOfTuple(data_tup[1],data_tup[2])
					if ii < len(self.datastore)-1 :
						del self.datastore[ii]
						logging.debug("Removing a previous calculated data point due to recalculation.")
					self.datastore.sort(key=itemgetter(1,2))

					# 2) If the new data matchs graph state then plot it
					if (x and (m==data_tup[1])) or ((not x) and (c==data_tup[2])) :
						self.PullDataFromStore(cost=c, xsec_on=x, m=m)
						self.DoLineAnimation()
				else :
					logging.debug("Caught change in graph state: %d, %d of %d, %f of %f"%(x,m,mm,c,mc))
					# 1) Update the animated plot element data based on data already in the datastore
					self.PullDataFromStore(cost=c, xsec_on=x, m=m)
					# 2) Redraw the plot axes and store the background
					self.UpdateAxisLimits()
					# 3) Sleep because matplotlib is not thread safe and it needs time to redraw
					time.sleep(self.params['RedrawDelay'])
					# 4) Animate the graph lines
					self.DoLineAnimation()

				end_t = time.time()
				elapsed_t = end_t-start_t
				logging.debug("Plotting elapsed time is: %f"%elapsed_t)

				self.PlotDataQ.task_done()
				#logging.debug("Done processing data_tup %s"%str(data_tup))
			except Exception as detail :
				logging.error("Problem plotting new data tuple: %s"%detail)
	
	def PullDataFromStore(self,**kwargs) :
		"""
		Updates the data plotted by the PlotWorker with the latest data from the datastore

		kwargs - a dict() to overwrite default values of gstate

		internal variables -
			gstate -
				the current state of the graph (what is on the x axis and which learning curve or
				cross section is shown)
			self.xdata -
				x coordinates of the data to plot
			self.ytdata -
				y coordinates of the data to plot for the training score line
			self.ycvdata -
				y coordinate of the data to plot for the cross validation score line
		"""
		logging.debug("Entering PullDataFromStore() for %s"%str(kwargs.items()))
		gstate = {'m':0,
		          'cost':1,
		          'xsec_on':False}
		gstate.update(kwargs)

		if gstate['xsec_on'] :
			data = [(t[2],1-t[3],1-t[4]) for t in self.datastore if t[1]==gstate['m']]
		else :
			data = [(t[1],1-t[3],1-t[4]) for t in self.datastore if t[2]==gstate['cost']]
		if not data :
			logging.debug("Returning from PullDataFromStore() with no data.")
		else :
			self.xdata,self.ytdata,self.ycvdata = zip(*data)
			logging.debug("Got this xdata: %s"%str(self.xdata))
		logging.debug("Leaving PullDataFromStore() for %s"%str(kwargs.items()))

	def getIndexOfTuple(self, val1, val2):
		"""
		Returns the index of the datatuple that matches the input values provided. This is a worker function
		used when adding new data to the datastore to avoid adding multiple instances of the same data.

		val1 -
			number of training samples used to train the solution taken from the PlotDataQ
		val2 -
			cost or regularization value used when training the solution taken from the PlotDataQ
		
		Return values:
			pos or lendata-1 - the index in the datastore of the data tuple matching the provided values
		"""
		lendata = len(self.datastore)
		for pos,t in enumerate(self.datastore[0:lendata-1]):
			if (t[1] > val1) : break
			if (t[1] == val1) and (t[2] == val2) :
				return pos

		if (self.datastore[-1][1] == val1) and (self.datastore[-1][2] == val2) :
			return lendata-1
		else :
			# Matches behavior of list.index
			raise ValueError("list.index(m,cost): match to %d,%f not in list"%(val1,val2))

	def DoLineAnimation(self) :
		"""
		Animate the plot lines with the data saved in self.xdata, self.ytdata, and self.ycvdata

		internal variables -
			self.xdata -
				x coordinates of the data to plot
			self.ytdata -
				y coordinates of the data to plot for the training score line
			self.ycvdata -
				y coordinate of the data to plot for the cross validation score line
		"""
		logging.debug("Entering DoLineAnimation()")
		if self.background is None:
			logging.debug("Returning from DoLineAnimation() with background is None.")
			return
		self.canvas.restore_region(self.background)
		if self.xdata and self.ytdata and self.ycvdata :
			self.linet.set_data(self.xdata, self.ytdata)
			self.linecv.set_data(self.xdata, self.ycvdata)
			self.ax.draw_artist(self.linet)
			self.ax.draw_artist(self.linecv)
		else :
			logging.error("No data to draw")
		self.canvas.blit(self.ax.bbox)
		logging.debug("Leaving DoLineAnimation()")

	def UpdateAxisLimits(self) :
		"""
		Update the static elements of the plot (x and y axis, etc.) when a graph state change signal is caught
		"""
		logging.debug("Entering UpdateAxisLimits()")

		xminlim = 0
		with self.watchlock :
			if self.watchlist[0] :
				xmaxlim = 1.05*self.watchlist[2][1]
				self.ax.set_xlabel('Cost')
			else :
				xmaxlim = 1.05*self.watchlist[1][1]
				self.ax.set_xlabel('Number of Training Samples')
		self.ax.set_xlim(xminlim,xmaxlim)

		if not (self.ytdata and self.ycvdata) :
			self.ax.figure.canvas.draw()
			logging.debug("Returning from UpdateAxisLimits() without updating y axis due to empty data lists.")
			return

		y_all = self.ytdata + self.ycvdata
		yminlim = 0.95*min(y_all)
		ymaxlim = 1.05*max(y_all)
		self.ax.set_ylim(yminlim,ymaxlim)
		self.ax.figure.canvas.draw()
		logging.debug("Exiting UpdateAxisLimits()")
