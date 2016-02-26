# -*- coding: utf-8 -*-
"""
Created on Wed Feb 24 15:39:00 2016

@author: JCole119213
"""

from sklearn.svm import SVC
import logging
import threading
import Queue

class TrainSVMs(threading.Thread) :
	def __init__(self, DBobj, DBpath, PauseRef, PauseLock, PlotDataQ, **params) :
		super(TrainSVMs,self).__init__()
		self.stopflag = threading.Event()
		self.DBobj = DBobj
		self.DBpath = DBpath
		self.PauseRef = PauseRef
		self.PauseLock = PauseLock
		self.ParamSpace = dict()
		self.ParamSpace['Step'] = 600
		self.ParamSpace['MaxTraining'] = 1800
		self.ParamSpace['WordList'] = "wordlist0"
		self.ParamSpace['Costs'] = [1]
		self.ParamSpace.update(params)
		self.PlotDataQ = PlotDataQ
		return

	def stop(self) :
		self.stopflag.set()

	def stopped(self) :
		return self.stopflag.is_set()

	def verifygo(self) :
		if self.stopflag.is_set() :
			raise Exception("Thread stop flag is set.")

	def run(self) :
		assert not self.PauseLock.acquire(False), "The Stop button lock must be acquired before starting the TrainSVMs thread."
		try :
			jj = 0
			step = self.ParamSpace['Step']
			MaxTraining = self.ParamSpace['MaxTraining']
			listchoice = self.ParamSpace['WordList']
			Cs = self.ParamSpace['Costs']
	
			logging.debug('Connecting to database at %s'%self.DBpath)
			self.DBobj.ConnectDB(self.DBpath)
			logging.debug('Result: %s'%self.DBobj.DB_Connect)
			try :
				NumTraining = self.DBobj.GetTrainSampleCount()
				NumTraining = min(NumTraining,MaxTraining)
				Xcv,Ycv = self.DBobj.GetXY(listchoice,1)
				Xtrain = []
				Ytrain = []
				for m in range(0,NumTraining,step) :
					self.verifygo()
					Xs,Ys = self.DBobj.GetXY(listchoice,0,step,m)
					Xtrain.extend(Xs)
					Ytrain.extend(Ys)
					for cost in Cs :
						self.verifygo()
						clf = SVC(C=cost,kernel='linear')
						clf.fit(Xtrain,Ytrain)
						self.verifygo()
						TrainScore = clf.score(Xtrain,Ytrain)
						CVScore = clf.score(Xcv,Ycv)
						self.PlotDataQ.put((clf,m+step,cost,TrainScore,CVScore))
						logging.debug('%d, %d, %f, %f, %f'%(jj, m+step, cost, TrainScore, CVScore))
						jj += 1
			except Exception as detail :
				logging.error("Did not complete all the assigned SVM training: %s"%detail)
			finally :
				logging.debug('Disconnecting database at %s'%self.DBobj.DB_Connect)
				self.DBobj.DisconnectDB()
				logging.debug('Result: %s'%self.DBobj.DB_Connect)
		finally :
			self.PauseRef.configure(command=None)
			self.PauseLock.release()
