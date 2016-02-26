# -*- coding: utf-8 -*-
"""
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
		super(PlotWorker,self).__init__()
		self.PlotDataQ = PlotDataQ
		self.datastore = datastore

		self.ax = ax
		self.canvas = ax.figure.canvas
		self.init_plot()

		self.watchlist = watchlist
		self.watchlock = watchlock
		return

	def init_plot(self) :
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
		logging.debug("Storing background due to draw event.")
		self.background = self.canvas.copy_from_bbox(self.ax.bbox)

	def run(self) :
		while True :
			try :
				data_tup = self.PlotDataQ.get()
				#logging.debug("Got data_tup %s from queue"%str(data_tup))
				start_t = time.time()

				if data_tup is not None :
					#logging.debug("Entering datastore manipulation for %s"%str(data_tup))
					self.datastore.append(data_tup)
					ii = self.getIndexOfTuple(data_tup[1],data_tup[2])
					if ii < len(self.datastore)-1 :
						del self.datastore[ii]
						logging.debug("Removing a previous calculated data point due to recalculation.")
					self.datastore.sort(key=itemgetter(1,2))
					#logging.debug("Exiting datastore manipulation for %s"%str(data_tup))
				else :
					with self.watchlock :
						logging.debug("Caught change in graph state: %d, %d of %d, %f of %f"%(self.watchlist[0],self.watchlist[1][0],self.watchlist[1][1],self.watchlist[2][0],self.watchlist[2][1]))

				#copy watches to keyword arguments before use for thread safety
				with self.watchlock :
					x = self.watchlist[0]
					m = self.watchlist[1][0]
					c = self.watchlist[2][0]
				self.plotter(cost=c, xsec_on=x, m=m)

				if data_tup is None :
					self.UpdateAxisLimits()

				end_t = time.time()
				elapsed_t = end_t-start_t
				logging.debug("Plotting elapsed time is: %f"%elapsed_t)

				self.PlotDataQ.task_done()
				#logging.debug("Done processing data_tup %s"%str(data_tup))
			except Exception as detail :
				logging.error("Problem plotting new data tuple: %s"%detail)
	
	def plotter(self,**kwargs) :
		logging.debug("Entering plotter() for %s"%str(kwargs.items()))
		if self.background is None:
			logging.debug("Returning from plotter() with background is None.")
			return

		params = {'m':0,
		          'cost':1,
		          'xsec_on':False}
		params.update(kwargs)

		if params['xsec_on'] :
			data = [(t[2],1-t[3],1-t[4]) for t in self.datastore if t[1]==params['m']]
		else :
			data = [(t[1],1-t[3],1-t[4]) for t in self.datastore if t[2]==params['cost']]
		logging.debug("Got this data: %s"%str(data))
		if not data :
			logging.debug("Returning from plotter() with no data to plot.")
			return
		self.xdata,self.ytdata,self.ycvdata = zip(*data)

		self.canvas.restore_region(self.background)
		self.linet.set_data(self.xdata, self.ytdata)
		self.linecv.set_data(self.xdata, self.ycvdata)
		self.ax.draw_artist(self.linet)
		self.ax.draw_artist(self.linecv)
		self.canvas.blit(self.ax.bbox)
		logging.debug("Leaving plotter() for %s"%str(kwargs.items()))

	def getIndexOfTuple(self, val1, val2):
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

	def UpdateAxisLimits(self) :
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
		self.ax.figure.canvas.draw()

		if not (self.ytdata and self.ycvdata) :
			logging.debug("Returning from UpdateAxisLimits() without updating y axis due to empty data lists.")
			return
		y_all = self.ytdata + self.ycvdata
		yminlim = 0.95*min(y_all)
		ymaxlim = 1.05*max(y_all)
		self.ax.set_ylim(yminlim,ymaxlim)
		self.ax.figure.canvas.draw()
		self.canvas.restore_region(self.background)
		self.ax.draw_artist(self.linet)
		self.ax.draw_artist(self.linecv)
		self.canvas.blit(self.ax.bbox)
		logging.debug("Exiting UpdateAxisLimits()")
