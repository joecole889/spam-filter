# -*- coding: utf-8 -*-
"""
Running this module as __main__ creates a feature vector database without using a GUI

Created on Tue Feb 09 16:03:00 2016

@author: Joseph R. Cole
"""

#import pdb
import traceback
import json
import sqlite3
import os
from scipy.optimize import minimize
import random
from FeatureVecGen import FeatureVecGen
import logging
from TempDB import TempDB
import time
import cPickle
import threading

class EmailSamplesDB :
	"""
	Controls the connection to the feature vector database.  In the future this will be implemented more
	generically to serve as a base class that provides the interface to the LearningCurveAppMainGUI. A 
	developer could then inherit from this class to connect to any given feature vector database.  Currently,
	this class works with the email/spam feature vector database used in the tutorial.  All SQL commands are
	placed in an external JSON file so that the queries do not need to be hard coded.  The SQLCMDObj abstracts
	the SQL commands from the JSON file so that an external application can pass both the command along with
	its necessary parameters at the same time into this class's methods.
	"""
	DB_Connect = None
	DB_Cursor = None
	params = dict()

	def __init__(self,sqlcmdpath,pragmacmdpath,tempsqlcmdpath,**params) :
		"""
		Load external data and parameters in preparation to work with a feature vector database.

		sqlcmdpath -
			json file with SQL commands for queries on the sqlite3 database
		pragmacmdpath -
			json file with PRAGMA commands for initializing the sqlite3 database
		tempsqlcmdpath -
			json file with SQL commands for queries on a temporary database when it is necessary to
			read data/process it/write data back to the main database (using multiple cursors at the
			same time doesn't seem to be supported in sqlite3)
		params -
			a dict() with parameters controlling creation of feature vectors and other configurable options

			params['CommitFreq'] -
				number of writes to add to the database journal before a commit when doing large blocks of writes
			params['ProgFreq'] -
				number of files to add to the database before signalling the progress bar queue in AddToDB()
			params['TempDBCMDs'] -
				stores the tempsqlcmdpath for use with the temporary database when needed
			params['MinCountFrac'] -
				Used for creating the words lists against which feature vectors are created.
				Minimum frequency of word occurance in the training set before the word is included in the word list
				(specified as a fraction of the total number of words in the training set)
			params['MaxCountFrac'] -
				Used for creating the words lists against which feature vectors are created.
				Maximum frequency of word occurance in the training set allowing the word to be included in the word list
				(specified as a fraction of the total number of words in the training set)

		shared class variables - 
			self.DB_Connect - the sqlite database connection object

			self.DB_Cursor - the sqlite database cursor object

			self.DBpath - path to the current database file in use

			self.DBlock - a lock on the database preventing other threads from accessing it

			self.SQLCMDs - dict() containing all the available SQL commands

			self.DBSetup - dict() containing all the available PRAGMA commands
		"""
		self.DBpath = None
		self.DBlock = threading.Lock()
		self.params['MainDBCMDs'] = sqlcmdpath
		self.params['PragmaCMDs'] = pragmacmdpath
		self.params['TempDBCMDs'] = tempsqlcmdpath
		self.SetParams(**params)

		try :
			fhan = open(sqlcmdpath)
			SQLCMDStr = fhan.read()
			fhan.close()
			self.SQLCMDs = json.loads(SQLCMDStr)
		except Exception as detail :
			logging.error("Unable to load SQL commands from %s: %s"%(sqlcmdpath,detail))
		try :
			fhan = open(pragmacmdpath)
			PragmaCMDStr = fhan.read()
			fhan.close()
			self.DBSetup = json.loads(PragmaCMDStr)
		except Exception as detail :
			logging.error("Unable to load PRAGMA commands from %s: %s"%(pragmacmdpath,detail))
		return

	def SetParams(self,**params) :
		self.params['CommitFreq'] = self.params.get('CommitFreq',200)
		self.params['ProgFreq'] = self.params.get('ProgFreq',100)
		self.params['MaxCountFrac'] = self.params.get('MaxCountFrac',0.003)
		self.params['MinCountFrac'] = self.params.get('MinCountFrac',0.00003)
		self.params.update(params)
		return

	def __del__(self) :
		"""
		Automatically ensures the database connection is closed and the lock is released when all
		references to this object are gone.
		"""
		if self.DB_Connect is not None :
			self.DB_Cursor = None
			self.DB_Connect.close()
			self.DBlock.release()
		return

	def ConnectDB(self,DBpath=None) :
		"""
		Setup a connection to an sqlite3 feature vector database file. Remember to close immediately
		once your read or write is complete or other threads won't be able to use the database.

		DBpath - path to the database file to connect
		"""
		if DBpath is None :
			DBpath = self.DBpath
		logging.info("Attempting to connect to %s"%DBpath)
		try :
			assert self.DB_Connect is None, "Need to close previous connection first."
			got_lock = self.DBlock.acquire(False)	# Non blocking form of threading.Lock.acquire()
			assert got_lock, "Database is in use, couldn't get the lock."
			self.DB_Connect = sqlite3.connect(DBpath)
			for cmd in self.DBSetup.values() :
				self.DB_Connect.execute(cmd)
			self.DB_Cursor = self.DB_Connect.cursor()
			self.DBpath = DBpath
		except Exception as detail :
			logging.error("Unable to connect to database at %s: %s"%(DBpath,detail))
			self.DisconnectDB()
		return

	def ConnectDBblk(self,DBpath=None) :
		"""
		Setup a connection to an sqlite3 feature vector database file. Remember to close immediately
		once your read or write is complete or other threads won't be able to use the database. This
		is the same as ConnectDB() except that it blocks the thread and waits for the lock to be
		released if the database is in use.

		DBpath - path to the database file to connect
		"""
		if DBpath is None :
			DBpath = self.DBpath
		logging.info("Attempting to connect to %s"%DBpath)
		try :
			assert self.DB_Connect is None, "Need to close previous connection first."
			self.DBlock.acquire()	# Blocking form of threading.Lock.acquire()
			self.DB_Connect = sqlite3.connect(DBpath)
			for cmd in self.DBSetup.values() :
				self.DB_Connect.execute(cmd)
			self.DB_Cursor = self.DB_Connect.cursor()
			self.DBpath = DBpath
		except Exception as detail :
			logging.error("Unable to connect to database at %s: %s"%(DBpath,detail))
			self.DisconnectDB()
		return

	def DisconnectDB(self) :
		"""
		Disconnect a database and release the lock.
		"""
		try :
			if self.DB_Connect is not None :
				self.DB_Cursor = None
				self.DB_Connect.close()
				logging.info("Disconnected the database: %s"%self.DBpath)
				self.DB_Connect = None
			else :
				logging.info("No database to disconnect.")
			self.DBlock.release()
		except Exception as detail :
			logging.error("Failed to disconnect the database: %s"%detail)
		return

	def CreateDB(self) :
		"""
		Initialize the tables for a new database file.
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['CreateClassTable'])
			for ii,classname in enumerate(self.SQLCMDs['ClassesList']) :
				self.DB_Cursor.execute(self.SQLCMDs['InsertClass'],(ii,classname))

			self.DB_Cursor.execute(self.SQLCMDs['CreateSetTable'])
			for ii,setname in enumerate(self.SQLCMDs['SetList']) :
				self.DB_Cursor.execute(self.SQLCMDs['InsertSet'],(ii,setname))

			self.DB_Cursor.execute(self.SQLCMDs['CreateSampleTable'])
			self.DB_Cursor.execute(self.SQLCMDs['CreateDictListTable'])
			self.DB_Cursor.execute(self.SQLCMDs['CreateDictBuildTable'])
			self.DB_Cursor.execute(self.SQLCMDs['CreateWordLists'])
			self.DB_Cursor.execute(self.SQLCMDs['CreateFeatureTable'])
			self.DB_Connect.commit()
		except Exception as detail:
			logging.error("Failed to create the database: %s"%detail)
			self.DB_Connect.rollback()
		return

	def ResetDB(self) :
		"""
		Delete all the tables in a database.
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTables'])
			DictTables = self.DB_Cursor.fetchall()
			for table in DictTables :
				logging.debug("Dropping %s"%table[0])
				self.DB_Cursor.execute(self.SQLCMDs['DropTable']%table[0])

			self.DB_Cursor.execute(self.SQLCMDs['SelectWordLists'])
			WordListTables = self.DB_Cursor.fetchall()
			for table in WordListTables :
				logging.debug("Dropping %s"%table[0])
				self.DB_Cursor.execute(self.SQLCMDs['DropTable']%table[0])

			for table in self.SQLCMDs['TableList'] :
				logging.debug("Dropping %s"%table)
				self.DB_Cursor.execute(self.SQLCMDs['DropTable']%(table,))

			self.DB_Connect.commit()
		except Exception as detail:
			logging.error("Failed to reset the database: %s"%detail.message)
		return

	def AddToDB(self,dirpath,classname,samp_distr_targ,trackbar=None) :
		"""
		Add new sample emails to a database. No processing of the emails is done except to attempt
		conversion to utf-8.

		dirpath -
			a path to a directory of email files to add to the database
		classname -
			a reference to the class of the samples in the given directory (legitimate email or spam)
		samp_distr_targ -
			a tuple containing the desired fraction of samples assigned to each set (training,cross
			validation,test).  New samples are distributed to optimally match this desired distribution
			based on the number of new samples provided and the current distribution between sets of 
			samples already in the database. Each value in the tuple should be in the range [0,1], and
			the total of all values in the tuple should be 1.
		trackbar -
			an optional reference to a ProgressWindow object that allows the user to view the progress
			of adding the files to the database and to cancel adding if needed
		"""
		CurSampleCount = self.GetSampleCount()
		try :
			if isinstance(classname,str) :
				self.DB_Cursor.execute(self.SQLCMDs['SelectClassID'],(classname,))
				classid = self.DB_Cursor.fetchone()[0]
			elif isinstance(classname,int) :
				classid = classname
			else :
				raise TypeError("classname must be str or int")

			if not os.path.isdir(dirpath) :
				raise IOError("Provided directory path does not exist")

			for (dirname, dirs, files) in os.walk(dirpath) :
				NumSamples = len(files)
				SetAssignments = self.AssignSamplesToSets(NumSamples,samp_distr_targ)
				for ii,filename in enumerate(files) :
					thefile = os.path.join(dirname,filename)
					fhan = open(thefile)
					emailstr = fhan.read()
					fhan.close()
					HeaderSepPos = emailstr.find('\n\n')
					assert (HeaderSepPos != -1),'Unable to separate message body.'
					head = emailstr[0:HeaderSepPos].decode('utf-8','ignore')
					body = emailstr[HeaderSepPos+2:].decode('utf-8','ignore')
					order = random.randrange(2**(32-1) - 1)	# a value assigned to help ensure all classes of samples are drawn randomly from the database
					self.DB_Cursor.execute(self.SQLCMDs['InsertSample'],(ii+CurSampleCount,filename,head,body,classid,SetAssignments[ii],order))
					if trackbar is not None :
						if trackbar.stopped() :
							logging.debug("Breaking loop due to cancel signal")
							break
						if not bool((ii+1)%self.params['ProgFreq']) :
							trackbar.put(float(self.params['ProgFreq'])/NumSamples*100)
			self.DB_Connect.commit()
		except TypeError as detail :
			logging.critical(detail.message)
			exit()
		except IOError as detail :
			logging.error(detail.message)
		except Exception as detail :
			logging.error("Failed to add records to database: %s"%detail.message)
			self.DB_Connect.rollback()
		return

	def CreateDict(self,readable_name) :
		"""
		Add a new dictionary table to the database.

		readable_name - a human readable name to assign to the table that is saved alongside the automatically
		generated name used in the database

		return values:
			returns the database id of the dictionary
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['DictMax'])
			NextKey = self.DB_Cursor.fetchone()[0]
			if NextKey is not None:
				NextKey += 1
			else :
				NextKey = 0
			DictName = "dict%d"%NextKey
			self.DB_Cursor.execute(self.SQLCMDs['CreateDictTable']%DictName)
			self.DB_Cursor.execute(self.SQLCMDs['InsertDict'],(NextKey,DictName,readable_name))
			self.DB_Connect.commit()
		except Exception as detail :
			logging.error("Failed to create a new dictionary table: %s"%detail)
			self.DB_Connect.rollback()
		return NextKey

	def CreateWordList(self,readable_name,DictRef) :
		"""
		Add a new word list table to the database.

		readable_name - a human readable name to assign to the table that is saved alongside the automatically
		generated name used in the database
		DictRef - a reference to the dictionary table in the database from which the words in this list are
		taken

		return values:
			returns the database id of the new word list
		"""
		try :
			DictName,dict_id = self.ResolveDictRef(DictRef)
			self.DB_Cursor.execute(self.SQLCMDs['WordListMax'])
			NextKey = self.DB_Cursor.fetchone()[0]
			if NextKey is not None :
				NextKey += 1
			else :
				NextKey = 0
			WordListName = "wordlist%d"%NextKey
			self.DB_Cursor.execute(self.SQLCMDs['CreateWordList']%(WordListName,DictName))
			self.DB_Cursor.execute(self.SQLCMDs['InsertWordList'],(NextKey,dict_id,WordListName,readable_name))
			self.DB_Connect.commit()
		except Exception as detail :
			logging.error("Failed to create a new word list table: %s"%detail)
		return NextKey

	def DeleteWordList(self,WordListRef) :
		"""
		Removes a word list from the database

		WordListRef - a reference to the word list table to save
		"""
		try :
			ListName,list_id,DictRef,DictName = self.ResolveListRef(WordListRef)
			logging.debug("Removing references to %s"%ListName)
			self.DB_Cursor.execute(self.SQLCMDs['DeleteFeaturesFromWordList'],(list_id,))
			self.DB_Cursor.execute(self.SQLCMDs['DropTable']%ListName)
			self.DB_Cursor.execute(self.SQLCMDs['DeleteWordList'],(list_id,))
			self.DB_Connect.commit()
		except Exception as detail :
			logging.error(detail)
			self.DB_Connect.rollback()
		return

	def DeleteDict(self,DictRef) :
		try :
			DictName,dict_id = self.ResolveDictRef(DictRef)
			logging.debug("Removing references to %s"%DictName)
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictDependents'],(dict_id,))
			DependentWordLists = self.DB_Cursor.fetchall()
			for WordList in DependentWordLists :
				self.DeleteWordList(WordList[0])
			self.DB_Cursor.execute(self.SQLCMDs['DeleteBuildRecords'],(dict_id,))
			self.DB_Cursor.execute(self.SQLCMDs['DropTable']%DictName)
			self.DB_Cursor.execute(self.SQLCMDs['DeleteDict'],(dict_id,))
			self.DB_Connect.commit()
		except Exception as detail :
			logging.error(detail)
			self.DB_Connect.rollback()
		return

	def WriteWords(self,WordListRef,FileName) :
		"""
		Save a word list from the database out to a text file.

		WordListRef - a reference to the word list table to save
		FileName - the name (full path) of the file to save
		"""
		try :
			ListName,list_id,DictRef,DictName = self.ResolveListRef(WordListRef)
			self.DB_Cursor.execute(self.SQLCMDs['SelectFeatures']%(DictName,ListName))
			WordList = self.DB_Cursor.fetchall()
		except Exception as detail :
			logging.error("Failed to grab dictionary words for writing to file.")

		try :
			with open(FileName,'w') as fhan :
				for Word in WordList :
					fhan.write('%s\n' % Word[0])
		except Exception as detail :
			logging.error("Failed to write the file %s: %s"%(FileName,detail))
		return
	
	def LoadWords(self,FileName) :
		"""
		Load a list of words from a plain text file. Each word should be on its own line. Then
		create a dictionary table and a word list table in the database using these words.

		FileName - the name (full path) of the file to load
		"""
		try :
			with open(FileName,'r') as fhan :
				Words = fhan.read()
		except Exception as detail :
			logging.error("Failed to read file %s: %s"%(FileName,detail))
		try :
			WordList = Words.rstrip().split('\n')
			WordList = filter(None,WordList)
			WordList = [(Word,) for Word in WordList]
			DictRef = self.CreateDict(FileName)
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTable'],(DictRef,))
			DictName = self.DB_Cursor.fetchone()[0]
			self.DB_Cursor.executemany(self.SQLCMDs['InsertAllWordsToDict']%DictName,WordList)
			self.DB_Connect.commit()
			list_id = self.CreateWordList(FileName,DictRef)
			self.UpdateWordList(list_id,False)
		except Exception as detail :
			logging.error("Failed to add words to the new dictionary: %s"%detail)
			self.DB_Connect.rollback()
		return DictRef

	def UpdateDict(self,DictRef,countsqlcmdobj,sqlcmdobj,trackbar=None) :
		"""
		Process samples in the training set to update a dictionary with words and their frequency of
		occurance.

		DictRef -
			a reference to the dictionary table in the database from which the words in this list are
			taken
		countsqlcmdobj -
			used to count the number of samples to use to update the dictionary in case a trackbar is
			displayed. This parameter is a reference to an SQLCMDObj so the user can update the SQL
			query used.
		sqlcmdobj -
			if calls to AddToDB() and UpdateDict() are interleaved, it is up to the SQL query used to
			make sure that an email sample is not double counted in the dictionary histogram. This
			parameter is a reference to an SQLCMDObj so the user can update the SQL query used.
			Samples used to create a dictionary are tracked in a separate table in the database.
		trackbar -
			a hook for showing the progress of the loop in a dialog window; should not be set manually.
			Use with the ProgressWindow class if needed.
		"""
		# TODO: Rewrite this function to avoid using a temporary database by using an SQL query
		#       with LIMIT and OFFSET.  Test which method is faster.
		try :
			DictName,dict_id = self.ResolveDictRef(DictRef)
			#pdb.set_trace()
			# Setup temporary database
			tmpdb = TempDB(self.params['TempDBCMDs'])
			# Connect and create temporary tables
			tmpdb.ConnectDB()
			tmpdb.RunCommand(tmpdb.SQLCMDs['CreateDictTable']%DictName)
			tmpdb.RunCommand(tmpdb.SQLCMDs['CreateDictBuildTable'])
			tmpdb.DisconnectDB()
			# Attach temporary database
			self.DB_Cursor.execute(self.SQLCMDs['AttachDB'],(tmpdb.DBpath,"tmp"))
			# Copy dictionary and dictbuild to temporary database
			self.DB_Cursor.execute(self.SQLCMDs['CopyTable']%('.'.join(["tmp",DictName]),DictName))
			dictbuild = self.SQLCMDs['DictBuildTableName']
			self.DB_Cursor.execute(self.SQLCMDs['CopyTable']%('.'.join(["tmp",dictbuild]),dictbuild))
			# Detach temporary database
			self.DB_Cursor.execute(self.SQLCMDs['DetachDB'],("tmp",))
			
			# Connect to temporary database
			tmpdb.ConnectDB()
			# Loop over samples in persistent db and update tables in tempdb
			CommitCount = 0
			ProgUpdateCount = 0
			if trackbar is not None :
				countsqlcmdobj.run()
				NumSamples = self.DB_Cursor.fetchone()[0]
				logging.debug("Updating dictionary with %d samples"%NumSamples)
			for sample_id,SampleBody in sqlcmdobj.run() :
				#logging.debug("Working on: %d"%sample_id)
				#logging.debug("Inserting row to dictionary build table")
				tmpdb.RunCommand(tmpdb.SQLCMDs['InsertUsed'],(sample_id,dict_id))
				#logging.debug("Counting email body words")
				SampleWordCounts = FeatureVecGen.ParetoWords(SampleBody)
				#logging.debug("Looping over the words")
				for Word in SampleWordCounts.keys() :
					tmpdb.RunCommand(tmpdb.SQLCMDs['RetrieveWordCount']%DictName,(Word,))
					OldCount = tmpdb.DB_Cursor.fetchone()
					if OldCount is not None :
						SampleWordCounts[Word] = SampleWordCounts[Word] + OldCount[0]
				#logging.debug("Updating the word counts")
				if CommitCount != self.params['CommitFreq'] :
					CommitCount += 1
					tmpdb.RunCommands(tmpdb.SQLCMDs['UpdateWordCount']%DictName,SampleWordCounts.items(),False)
				else :
					tmpdb.RunCommands(tmpdb.SQLCMDs['UpdateWordCount']%DictName,SampleWordCounts.items(),True)
					CommitCount = 0
				if trackbar is not None :
					if trackbar.stopped() :
						logging.debug("Breaking loop due to cancel signal")
						break
					if ProgUpdateCount != self.params['ProgFreq']-1 :
						ProgUpdateCount += 1
					else :
						trackbar.put(float(self.params['ProgFreq'])/NumSamples*100)
						ProgUpdateCount = 0
			tmpdb.DB_Connect.commit()
			tmpdb.DisconnectDB()

			#pdb.set_trace()
			# Attach tempdb
			self.DB_Cursor.execute(self.SQLCMDs['AttachDB'],(tmpdb.DBpath,"tmp"))
			# Copy tables from tempdb
			self.DB_Cursor.execute(self.SQLCMDs['TransferUsed']%'.'.join(["tmp",dictbuild]))
			self.DB_Cursor.execute(self.SQLCMDs['TransferDict']%(DictName,'.'.join(["tmp",DictName])))
			# Detach and delete tempdb
			self.DB_Cursor.execute(self.SQLCMDs['DetachDB'],("tmp",))
			self.DB_Connect.commit()
			del tmpdb
		except TypeError as detail :
			logging.error(detail)
		except Exception as detail :
			logging.error("Failed to update dictionary %s: %s"%(DictName,detail))
			logging.error("Sample id: %d\nDictionary id: %d"%(sample_id,dict_id))
			tb = traceback.format_exc()
			logging.error(tb)
			self.DB_Connect.rollback()
		return

	def UpdateWordList(self,WordListRef,WordFilter=True) :
		"""
		Update a word list whenever a dictionary has been changed. Word lists are connected to specific
		dictionaries internally in the database, so it is not necessary to provide a dictionary reference.

		WordListRef -
			a reference to the word list table to save
		WordFilter -
			allows the user to control whether words in the dictionary should be excluded from
			the list based on parameters provided as class attributes (True) or all words in the
			dictionary should be added to the list (False)
		"""
		try :
			ListName,list_id,DictRef,DictName = self.ResolveListRef(WordListRef)
			if WordFilter == True :
				self.DB_Cursor.execute(self.SQLCMDs['TotalWordCount']%DictName)
				TotalCount = self.DB_Cursor.fetchone()[0]
				CountMax = self.params['MaxCountFrac'] * TotalCount
				CountMin = self.params['MinCountFrac'] * TotalCount
				self.DB_Cursor.execute(self.SQLCMDs['InsertWords']%(ListName,DictName),(CountMin,CountMax))
			else :
				self.DB_Cursor.execute(self.SQLCMDs['InsertAllWords']%(ListName,DictName))
			self.DB_Connect.commit()
		except Exception as detail :
			logging.error("Failed to update word list %s: %s"%(ListName,detail))
			self.DB_Connect.rollback()

	def MakeFeatureVecs(self,WordListRef,countsqlcmdobj,sqlcmdobj,trackbar=None) :
		"""
		Create feature vectors against a given word list. Uses a FeatureVecGen object as an engine for
		creating the feature vector given an email sample body.
		
		WordListRef -
			a reference to the word list table to save
		countsqlcmdobj -
			this parameter is an SQLCMDObj with the sql command to run along with it's bindings. Used
			to count the samples for which to create feature vectors.
		sqlcmdobj -
			this parameter is an SQLCMDObj with the sql command to run along with it's bindings. Used
			to select samples for which to create feature vectors.
		trackbar -
			a hook for showing the progress of the loop in a dialog window; should not be set manually.
			Use with the ProgressWindow class if needed.
		"""
		try :
			ListName,list_id,DictRef,DictName = self.ResolveListRef(WordListRef)

			#Get the feature vector word list
			self.DB_Cursor.execute(self.SQLCMDs['SelectFeatures']%(DictName,ListName))
			FeatureWords = self.DB_Cursor.fetchall()
			FeatureWords = [word[0] for word in FeatureWords]
			#Init FeatureVecGen object
			FeatureMaker = FeatureVecGen(FeatureWords)
			# Setup temporary database
			tmpdb = TempDB(self.params['TempDBCMDs'])
			# Connect and create temporary tables
			tmpdb.ConnectDB()
			tmpdb.RunCommand(tmpdb.SQLCMDs['CreateFeatureTable'])
			tmpdb.DisconnectDB()
			# Attach temporary database
			self.DB_Cursor.execute(self.SQLCMDs['AttachDB'],(tmpdb.DBpath,"tmp"))
			# Copy dictionary and dictbuild to temporary database
			featuretab = self.SQLCMDs['FeaturesTableName']
			self.DB_Cursor.execute(self.SQLCMDs['CopyTable']%('.'.join(["tmp",featuretab]),featuretab))
			# Detach temporary database
			self.DB_Cursor.execute(self.SQLCMDs['DetachDB'],("tmp",))
			
			# Connect to temporary database
			tmpdb.ConnectDB()
			# Loop over samples in persistent db and update tables in tempdb
			CommitCount = 0
			ProgUpdateCount = 0
			logging.debug("Counting samples")
			if trackbar is not None :
				countsqlcmdobj.run()
				NumSamples = self.DB_Cursor.fetchone()[0]
				logging.debug("Creating feature vectors for %d samples"%NumSamples)
			for sample_id,SampleBody in sqlcmdobj.run() :
				#logging.debug("Working on: %d"%sample_id)
				featurevec = FeatureMaker.MakeVec(SampleBody)
				featureserial = buffer(cPickle.dumps(featurevec))
				#logging.debug("Inserting row to feature table")
				if CommitCount != self.params['CommitFreq'] :
					CommitCount += 1
					tmpdb.RunCommand(tmpdb.SQLCMDs['InsertFeature'],(sample_id,list_id,featureserial),False)
				else :
					tmpdb.RunCommand(tmpdb.SQLCMDs['InsertFeature'],(sample_id,list_id,featureserial),True)
					CommitCount = 0
				if trackbar is not None :
					if trackbar.stopped() :
						logging.debug("Breaking loop due to cancel signal")
						break
					if ProgUpdateCount != self.params['ProgFreq']-1 :
						ProgUpdateCount += 1
					else :
						trackbar.put(float(self.params['ProgFreq'])/NumSamples*100)
						ProgUpdateCount = 0
			tmpdb.DB_Connect.commit()
			logging.debug("Done adding new features to tmpDB")
			tmpdb.DisconnectDB()

			#pdb.set_trace()
			# Attach tempdb
			self.DB_Cursor.execute(self.SQLCMDs['AttachDB'],(tmpdb.DBpath,"tmp"))
			# Copy tables from tempdb
			self.DB_Cursor.execute(self.SQLCMDs['TransferFeatures']%'.'.join(["tmp",featuretab]))
			# Detach and delete tempdb
			self.DB_Cursor.execute(self.SQLCMDs['DetachDB'],("tmp",))
			self.DB_Connect.commit()
			del tmpdb
		except TypeError as detail :
			logging.error(detail)
		except Exception as detail :
			logging.error("Failed to create feature vectors: %s"%detail)
			self.DB_Connect.rollback()
		return

	def GetSampleDistribution(self) :
		"""
		Return the fraction of samples in the database assigned to each set (training,cross validation,test)

		Return values:
			SetIDs - a list of the primary keys assigned to the sets in the database
			SetDistr - a list of the fractions of samples assigned to each set
		"""
		try :
			SetList = self.SQLCMDs['SetList']
			SetIDs = [0,]*len(SetList)
			SetDistr = [0,]*len(SetList)
			for ii,setname in enumerate(SetList) :
				self.DB_Cursor.execute(self.SQLCMDs['SelectSetID'],(setname,))
				SetIDs[ii] = self.DB_Cursor.fetchone()[0]
				self.DB_Cursor.execute(self.SQLCMDs['SampleSetCount'],(SetIDs[ii],))
				SetDistr[ii] = float(self.DB_Cursor.fetchone()[0])
		except Exception as detail :
			logging.info("Failed to retrieve sample set distribution: %s"%detail)
			SetIDs = (0,1,2)
			SetDistr = (0,0,0)
		return SetIDs,SetDistr

	def GetSampleCount(self) :
		"""
		Return the number of samples in the database

		Return values:
			CurSampleCount - integer number of samples in the database
		"""
		CurSampleCount = 0
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SampleCount'])
			CurSampleCount = self.DB_Cursor.fetchone()[0]
		except Exception as detail:
			logging.error("Failed to get count of samples in database: %s"%detail)
		return CurSampleCount

	def GetTrainSampleCount(self) :
		"""
		Return the number of samples in the training set

		Return values:
			CurSampleCount - integer number of samples in the training set
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SampleSetCount'],(0,))
			CurSampleCount = self.DB_Cursor.fetchone()[0]
		except Exception as detail:
			logging.error("Failed to get count of training samples in database: %s"%detail)
		return CurSampleCount

	def GetAvailableWordLists(self) :
		"""
		Return the word lists available in the database

		Return values:
			WordLists - a list of tuples with the available wordlists in the database where the SQL query
			used controls the order of items in the tuple
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SelectWordLists'])
			WordLists = self.DB_Cursor.fetchall()
		except Exception as detail :
			logging.error("Failed to return word lists: %s"%detail)
		return WordLists

	def GetAvailableDicts(self) :
		"""
		Return the dictionaries available in the database

		Return values:
			Dicts - a list of tuples with the available dictionaries in the database
			where the SQL query used controls the order of items in the tuple
		"""
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTables'])
			Dicts = self.DB_Cursor.fetchall()
		except Exception as detail :
			logging.error("Failed to return dictionaries: %s"%detail)
		return Dicts

	def GetXY(self,WordListRef,SetID,Limit=None,Offset=0) :
		"""
		Return feature vectors and their classes. The order is controlled by the SQL query used, and there
		is a value saved along with each sample to help randomize the mixture of classes returned.

		WordListRef -
			a reference to the word list table to save
		SetID -
			the primary key assigned to the set in the database for the requested feature vectors
		Limit -
			optional positive integer parameter to limit the number of feature vectors returned
		Offset -
			optional non-negative integer parameter to skip some number of feature vectors in the
			database. If Limit is None then Offset is forced to be 0 regardless of the value provided.

		Return values:
			X - a list of the requested feature vectors
			Y - a list of the classes associated with the returned feature vectors
		"""
		try :
			ListName,list_id,DictRef,DictName = self.ResolveListRef(WordListRef)
			if Limit is None :
				self.DB_Cursor.execute(self.SQLCMDs['SampleCount'])
				Limit = self.DB_Cursor.fetchone()[0]
				Offset = 0
			assert (Limit>0),"Limit argument must be a positive integer!"
			assert (Offset>=0),"Offset argument must be a non-negative integer!"
			self.DB_Cursor.execute(self.SQLCMDs['GetXY'],(list_id,SetID,Limit,Offset))
			XYs = self.DB_Cursor.fetchall()
			XYs = map(list, zip(*XYs))
			X = XYs[0]
			for ii,featurevec in enumerate(X) :
				X[ii] = cPickle.loads(str(featurevec))
			Y = XYs[1]
		except Exception as detail :
			logging.error("Failed to get X and Y lists: %s"%detail)
		return X,Y

	def ResolveListRef(self,WordListRef) :
		if isinstance(WordListRef,str) :
			ListName = WordListRef
			self.DB_Cursor.execute(self.SQLCMDs['SelectWordListID'],(WordListRef,))
			list_id = self.DB_Cursor.fetchone()[0]
		elif isinstance(WordListRef,int) :
			list_id = WordListRef
			self.DB_Cursor.execute(self.SQLCMDs['SelectWordList'],(WordListRef,))
			ListName = self.DB_Cursor.fetchone()[0]
		else :
			raise TypeError("WordListRef must be str or int")
		self.DB_Cursor.execute(self.SQLCMDs['SelectDictRef'],(list_id,))
		DictRef = self.DB_Cursor.fetchone()[0]
		DictName,dict_id = self.ResolveDictRef(DictRef)
		return ListName,list_id,DictRef,DictName

	def ResolveDictRef(self,DictRef) :
		if isinstance(DictRef,str) :
			DictName = DictRef
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictID'],(DictRef,))
			dict_id = self.DB_Cursor.fetchone()[0]
		elif isinstance(DictRef,int) :
			dict_id = DictRef
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTable'],(DictRef,))
			DictName = self.DB_Cursor.fetchone()[0]
		else :
			raise TypeError("DictName must be str or int")
		return DictName,dict_id

	def AssignSamplesToSets(self,NumNewSamples,samp_distr_targ) :
		"""
		Create set assignments for a number of new samples to be added to the database (training, cross validation, or test)

		NumNewSamples -
			the number of new samples to add; a set assignment will be made for each new sample
		samp_distr_targ -
			a tuple containing the desired fraction of samples assigned to each set (training,cross
			validation,test).  New samples are distributed to optimally match this desired distribution
			based on the number of new samples provided and the current distribution between sets of 
			samples already in the database. Each value in the tuple should be in the range [0,1], and
			the total of all values in the tuple should be 1.

		Return values:
			SetAssignmentList - a list of set assignments for each new sample; len(SetAssignmentList) == NumNewSamples
		"""
		SetAssignmentList = []
		(SetIDs,CurrentDistr) = self.GetSampleDistribution()
		CurSampleCount = self.GetSampleCount()
		try :
			NumSets = len(CurrentDistr)
			x0 = [0]*NumSets
			x0[0] = NumNewSamples
			x0 = tuple(x0)
			constargs = (samp_distr_targ,NumNewSamples,CurSampleCount,CurrentDistr)
			# boundary conditions - the new samples must be distributed to each set by fractions in the range [0,1]
			bnds = ((0,1),(0,1),(0,1))
			# constraints - the total of the distribution fractions must be equal to 1
			cons = {'type':'eq','fun': lambda x: x[0]+x[1]+x[2]-1}
			res = minimize(self.TargetDistrObj, x0, args=constargs,method='SLSQP',bounds=bnds,constraints=cons)
			AddedDistr = [0]*NumSets
			tot = 0
			for ii in range(0,NumSets-1) :
				AddedDistr[ii] = round(res.x[ii]*NumNewSamples)
				tot += AddedDistr[ii]
			AddedDistr[-1] = NumNewSamples-tot
			assert AddedDistr[-1]>=0,"Rounding problem calculating distribution of new samples into sets"
			for ii,val in enumerate(AddedDistr) :
				#print val
				SetAssignmentList.extend([SetIDs[ii]]*int(val))
		except Exception as detail:
			logging.critical("Failed to create set assignments: %s"%detail)
			exit()
		random.shuffle(SetAssignmentList)
		return SetAssignmentList

	@staticmethod
	def TargetDistrObj(x,t,newsamps,oldsamps,oldsetcounts) :
		"""
		Implements the equation to optimize for calculating how to distribute a given number of new samples between sets

		.. math::

			E = \\sum_{i=1}^3 (t_{i} - f_{i})^{2}

		where

		:math:`E` is the sample distribution sum of squares error

		:math:`t_{i}` is the targeted fractional distribution of samples to set i

		:math:`f_{i}` is the resulting fractional distribution of samples from a proposal to add a number of new samples to set i

		and :math:`i` iterates over (training, cross validation, and test) sets
		
		t -
			tuple of targeted distribution fractions; each value must be in the range [0,1] and the total must = 1
		newsamps -
			the total number of new samples to add to the database (integer)
		oldsamps -
			the total number of samples already in the database (integer)
		oldsetcounts -
			tuple of the (integer) counts of samples in each set for samples already in the database
		newtotal -
			the total number of samples that will be in the database once the new ones are added (integer)

		Return values:
			error - the sum of squares error between the targeted sample distribution and the proposed sample distribution
		"""
		error = 0
		newtotal = newsamps+oldsamps
		for ii in range(0,len(t)) :
			val = (t[ii] - (oldsetcounts[ii] + x[ii]*newsamps)/newtotal)
			error += val*val
		return error

class SQLCMDObj :
	def __init__(self,DBobj,sqlcmdname,params=()) :
		self.params = params
		self.DBobj = DBobj
		self.sqlstr = self.DBobj.SQLCMDs[sqlcmdname]
	def run(self) :
		return self.DBobj.DB_Cursor.execute(self.sqlstr,self.params)

###################################### Main Program ###################################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.INFO)
	aa = EmailSamplesDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\EmailSamplesDB_SQL.json",
						r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\DBSetup_SQL.json",
						r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\TempDB_SQL.json")
	aa.ConnectDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\tester1.sqlite3")
	print "Creating fresh database"
	aa.CreateDB()
	print "Adding good email messages"
	aa.AddToDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\EmailSamples\easy_ham","Legitimate Email",[.6,.2,.2])
	print "Adding spam email messages"
	aa.AddToDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\EmailSamples\spam",1,[.6,.2,.2])
	print "Creating fresh dictionary"
	DictRef = aa.CreateDict('My first dictionary')
	print "Updating word histograms"
	aa.UpdateDict(DictRef,"SelectNewTrainingBodies")
	print "Creating a feature vector word list"
	WordListRef = aa.CreateWordList("Test word list",DictRef)
	print "Updating the word list"
	aa.UpdateWordList(WordListRef)
	print "Loading a word list from file"
	dict_id = aa.LoadWords(r"C:\Users\jcole119213\Documents\Python Scripts\vocab.txt")
	list_id = aa.CreateWordList("Words from vocab.txt",dict_id)
	aa.UpdateWordList(list_id,False)
	print "Making the feature vectors"
	start_time = time.time()
	CountSamps = SQLCMDObj(aa,"SampleCount")
	SelectSamps = SQLCMDObj(aa,"SelectBodies")
	aa.MakeFeatureVecs(WordListRef,CountSamps,SelectSamps)
	elapsed_time = time.time() - start_time
	print "Elapsed time:",elapsed_time,'s'
	start_time = time.time()
	aa.MakeFeatureVecs(list_id,CountSamps,SelectSamps)
	elapsed_time = time.time() - start_time
	print "Elapsed time:",elapsed_time,'s'
	#print "Write a word list to a file"
	#FileName = r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\TestDict.txt"
	#aa.WriteWords("wordlist0",FileName)
	#print "Reset the database"
	#aa.ResetDB()
