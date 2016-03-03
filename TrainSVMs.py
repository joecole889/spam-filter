# -*- coding: utf-8 -*-
"""
This module implements a class derived from the Thread class in the threading module to encapsulate the
execution of the SVM training thread. It uses an implementation of LibSVM from scikit-learn.

Created on Wed Feb 24 15:39:00 2016

@author: JCole119213
"""

from sklearn.svm import SVC
import logging
import threading
import Queue

class TrainSVMs(threading.Thread) :
	def __init__(self, DBobj, DBpath, PauseRef, PauseLock, PlotDataQ, **params) :
		"""
		Initialize references to variables shared with the main thread of execution in the LearningCurveApp
		module

		variables shared between threads -
			self.DBobj -
				a reference to the EmailSamplesDB object
			self.DBpath -
				the full path to the sqlite3 feature vector database file
			self.PauseRef -
				a reference to the Tkinter Stop button widget in the main GUI (needs to be configured with command=None on exit)
			self.PauseLock -
				a threading.Lock object that must be released on exit
			self.PlotDataQ -
				a Queue to use for interacting with the main thread
					this thread puts a data tuple with: (MachineLearningObject, NumberOfTrainingSamplesUsed, CostUsed, TrainingScore, CrossValidationScore)

		Parameters:
			self.ParamSpace -
				default parameters are overwritten by the params dictionary passed in to the constructor; these
				define the parameter space of SVMs the user wishes to explore

				self.ParamSpace['Step'] -
					the step size (number of training samples) to add for each new point of the learning curve
				self.ParamSpace['MaxTraining'] -
					the maximum number of training samples to use for training an SVM (last point on the learning curve).
					If the provided value is higher than the number of training samples available in the database,
					the lower limit is automatically used.
				self.ParamSpace['WordList'] -
					controls which feature vectors to select from the database, as the features could be generated
					against different word lists
				self.ParamSpace['Costs'] -
					a list of floats with the cost values to try when training the SVMs
		"""
		super(TrainSVMs,self).__init__()
		self.stopflag = threading.Event()
		self.DBobj = DBobj
		self.DBpath = DBpath
		self.PauseRef = PauseRef
		self.PauseLock = PauseLock
		self.ParamSpace = {'Step':600,
				           'MaxTraining':1800,
						   'WordList':"wordlist0",
						   'Costs':[1]}
		self.ParamSpace.update(params)
		self.PlotDataQ = PlotDataQ
		return

	def stop(self) :
		"""
		This thread is stoppable from the main thread of execution by calling this function
		"""
		self.stopflag.set()

	def stopped(self) :
		"""
		Utility function to check if the stop signal was sent.
		"""
		return self.stopflag.is_set()

	def verifygo(self) :
		"""
		Raises an exception if the stop signal was sent.
		"""
		if self.stopflag.is_set() :
			raise Exception("Thread stop flag is set.")

	def run(self) :
		"""
		The main loop for the TrainSVMs thread; trains an SVM for each point in the parameter space the
		user wishes to explore. Data is passed outside by putting it on the PlotDataQ. Periodic calls
		to self.verifygo() are used to make sure the user still wants to continue. In this version it is
		not possible to stop the thread until the current SVM finishes training, which could cause slow
		stopping response for large datasets.

		Note that this thread holds the lock on the feature vector database for its entire execution so
		the database is guaranteed not to change while it's running. The final actions of this thread are
		to release the database lock by closing the connection, deactivate the callback of the Stop button
		widget in the main GUI, and release the PauseLock for CPU heavy threads.
		"""
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
