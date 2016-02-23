# -*- coding: utf-8 -*-
"""
Created on Tue Feb 09 16:03:00 2016

@author: JCole119213
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

class EmailSamplesDB :
	DB_Connect = None
	DB_Cursor = None
	params = dict()

	def __init__(self,sqlcmdpath,pragmacmdpath,tempsqlcmdpath,**params) :
		self.DBpath = None
		self.params['CommitFreq'] = 200
		self.params['TempDBCMDs'] = tempsqlcmdpath
		self.params['MaxCountFrac'] = 0.003
		self.params['MinCountFrac'] = 0.00003
		self.params.update(params)
		try :
			fhan = open(sqlcmdpath)
			SQLCMDStr = fhan.read()
			fhan.close()
			self.SQLCMDs = json.loads(SQLCMDStr)
		except Exception as detail :
			logging.error("Unable to load SQL commands from %s: %s"%(sqlcmdpath,detail))
			exit()
		try :
			fhan = open(pragmacmdpath)
			PragmaCMDStr = fhan.read()
			fhan.close()
			self.DBSetup = json.loads(PragmaCMDStr)
		except Exception as detail :
			logging.error("Unable to load PRAGMA commands from %s: %s"%(pragmacmdpath,detail))
			exit()
		return

	def __del__(self) :
		if self.DB_Connect is not None :
			self.DB_Cursor = None
			self.DB_Connect.close()
		return

	def ConnectDB(self,DBpath) :
		try :
			self.DB_Connect = sqlite3.connect(DBpath)
			for cmd in self.DBSetup.values() :
				self.DB_Connect.execute(cmd)
			self.DB_Cursor = self.DB_Connect.cursor()
			self.DBpath = DBpath
		except :
			logging.error("Unable to connect to database at %s"%DBpath)
		return

	def DisconnectDB(self) :
		try :
			if self.DB_Connect is not None :
				self.DB_Cursor = None
				self.DB_Connect.close()
				logging.info("Disconnected the database: %s"%self.DBpath)
				self.DB_Connect = None
			else :
				logging.info("No database to disconnect.")
		except Exception as detail :
			logging.error("Failed to disconnect the database: %s"%detail)
		return

	def CreateDB(self) :
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
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTables'])
			DictTables = self.DB_Cursor.fetchall()
			for table in DictTables :
				self.DB_Cursor.execute(self.SQLCMDs['DropTable']%table)
			for table in self.SQLCMDs['TableList'] :
				self.DB_Cursor.execute(self.SQLCMDs['DropTable']%(table,))
			self.DB_Connect.commit()
		except Exception as detail:
			logging.error("Failed to reset the database: %s"%detail.message)
		return

	def AddToDB(self,dirpath,classname,samp_distr_targ) :
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
					order = random.randrange(2**(32-1) - 1)
					self.DB_Cursor.execute(self.SQLCMDs['InsertSample'],(ii+CurSampleCount,filename,head,body,classid,SetAssignments[ii],order))
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
		try :
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

	def WriteWords(self,WordListRef,FileName) : # Allows saving of a dictionary
		try :
			if isinstance(WordListRef,str) :
				ListName = WordListRef
				self.DB_Cursor.execute(self.SQLCMDs['SelectWordListID'],(WordListRef,))
				list_id = self.DB_Cursor.fetchone()[0]
			elif isinstance(WordListRef,int) :
				list_id = WordListRef
				self.DB_Cursor.execute(self.SQLCMDs['SelectWordList'],(WordListRef,))
				ListName = self.DB_Cursor.fetchone()[0]
			else :
				raise TypeError("ListName must be str or int")
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictRef'],(list_id,))
			DictRef = self.DB_Cursor.fetchone()[0]
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTable'],(DictRef,))
			DictName = self.DB_Cursor.fetchone()[0]
			self.DB_Cursor.execute(self.SQLCMDs['SelectFeatures']%(DictName,ListName))
			WordList = self.DB_Cursor.fetchall()
		except Exception as detail :
			logging.error("Failed to grab dictionary words for writing to file.")

		try :
			fhan = open(FileName,'w')
			for Word in WordList :
				fhan.write('%s\n' % Word[0])
			fhan.close()
		except Exception as detail :
			logging.error("Failed to write the file %s: %s"%(FileName,detail))
		return
	
	def LoadWords(self,FileName) : # Allows loading of a saved word list to a dictionary
		try :
			fhan = open(FileName,'r')
			Words = fhan.read()
			fhan.close()
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
		except Exception as detail :
			logging.error("Failed to add words to the new dictionary: %s"%detail)
			self.DB_Connect.rollback()
		return DictRef

	def UpdateDict(self,DictRef,sqlcmdname) :
		try :
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
			for sample_id,SampleBody in self.DB_Cursor.execute(self.SQLCMDs[sqlcmdname],(dict_id,)) :
				logging.debug("Working on: %d"%sample_id)
				logging.debug("Inserting row to dictionary build table")
				tmpdb.RunCommand(tmpdb.SQLCMDs['InsertUsed'],(sample_id,dict_id))
				logging.debug("Counting email body words")
				SampleWordCounts = FeatureVecGen.ParetoWords(SampleBody)
				logging.debug("Looping over the words")
				for Word in SampleWordCounts.keys() :
					tmpdb.RunCommand(tmpdb.SQLCMDs['RetrieveWordCount']%DictName,(Word,))
					OldCount = tmpdb.DB_Cursor.fetchone()
					if OldCount is not None :
						SampleWordCounts[Word] = SampleWordCounts[Word] + OldCount[0]
				logging.debug("Updating the word counts")
				if CommitCount != self.params['CommitFreq'] :
					CommitCount += 1
					tmpdb.RunCommands(tmpdb.SQLCMDs['UpdateWordCount']%DictName,SampleWordCounts.items(),False)
				else :
					tmpdb.RunCommands(tmpdb.SQLCMDs['UpdateWordCount']%DictName,SampleWordCounts.items(),True)
					CommitCount = 0
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
		try :
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
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTable'],(DictRef,))
			DictName = self.DB_Cursor.fetchone()[0]
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

	def MakeFeatureVecs(self,WordListRef,sqlcmdname) :
		try :
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
			self.DB_Cursor.execute(self.SQLCMDs['SelectDictTable'],(DictRef,))
			DictName = self.DB_Cursor.fetchone()[0]

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
			for sample_id,SampleBody in self.DB_Cursor.execute(self.SQLCMDs[sqlcmdname]) :
				logging.debug("Working on: %d"%sample_id)
				SampleWords = FeatureMaker.RegularizeWords(SampleBody)
				SampleWords = FeatureMaker.StemWords(SampleWords)
				featurevec = FeatureMaker.MarkWordPresence(SampleWords)
				featureserial = buffer(cPickle.dumps(featurevec))
				logging.debug("Inserting row to feature table")
				if CommitCount != self.params['CommitFreq'] :
					CommitCount += 1
					tmpdb.RunCommand(tmpdb.SQLCMDs['InsertFeature'],(sample_id,list_id,featureserial),False)
				else :
					tmpdb.RunCommand(tmpdb.SQLCMDs['InsertFeature'],(sample_id,list_id,featureserial),True)
					CommitCount = 0
			tmpdb.DB_Connect.commit()
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
		try :
			SetList = self.SQLCMDs['SetList']
			SetIDs = [0,]*len(SetList)
			SetDistr = [0,]*len(SetList)
			for ii,setname in enumerate(SetList) :
				self.DB_Cursor.execute(self.SQLCMDs['SelectSetID'],(setname,))
				SetIDs[ii] = self.DB_Cursor.fetchone()[0]
				self.DB_Cursor.execute(self.SQLCMDs['SampleSetCount'],(SetIDs[ii],))
				SetDistr[ii] = float(self.DB_Cursor.fetchone()[0])
		except :
			logging.critical("Failed to retrieve sample set distribution")
			exit()
		return SetIDs,SetDistr

	def GetSampleCount(self) :
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SampleCount'])
			CurSampleCount = self.DB_Cursor.fetchone()[0]
		except Exception as detail:
			logging.error("Failed to get count of samples in database: %s"%detail)
		return CurSampleCount

	def GetTrainSampleCount(self) :
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SampleSetCount'],(0,))
			CurSampleCount = self.DB_Cursor.fetchone()[0]
		except Exception as detail:
			logging.error("Failed to get count of training samples in database: %s"%detail)
		return CurSampleCount

	def GetAvailableWordLists(self) :
		try :
			self.DB_Cursor.execute(self.SQLCMDs['SelectWordLists'])
			WordLists = self.DB_Cursor.fetchall()
		except Exception as detail :
			logging.error("Failed to return word lists: %s"%detail)
		return WordLists

	def GetXY(self,WordListRef,SetID,Limit=None,Offset=0) :
		try :
			if isinstance(WordListRef,str) :
				self.DB_Cursor.execute(self.SQLCMDs['SelectWordListID'],(WordListRef,))
				list_id = self.DB_Cursor.fetchone()[0]
			elif isinstance(WordListRef,int) :
				list_id = WordListRef
			else :
				raise TypeError("WordListRef must be str or int")
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

	def AssignSamplesToSets(self,NumNewSamples,samp_distr_targ) :
		SetAssignmentList = []
		(SetIDs,CurrentDistr) = self.GetSampleDistribution()
		CurSampleCount = self.GetSampleCount()
		try :
			NumSets = len(CurrentDistr)
			x0 = [0]*NumSets
			x0[0] = NumNewSamples
			x0 = tuple(x0)
			constargs = (samp_distr_targ,NumNewSamples,CurSampleCount,CurrentDistr)
			bnds = ((0,1),(0,1),(0,1))
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
				SetAssignmentList = SetAssignmentList + [SetIDs[ii]]*int(val)
		except Exception as detail:
			logging.critical("Failed to create set assignments: %s"%detail)
			exit()
		random.shuffle(SetAssignmentList)
		return SetAssignmentList

	@staticmethod
	def TargetDistrObj(x,t,newsamps,oldsamps,oldsetcounts) :
		error = 0
		newtotal = newsamps+oldsamps
		for ii in range(0,len(t)) :
			val = (t[ii] - (oldsetcounts[ii] + x[ii]*newsamps)/newtotal)
			error += val*val
		return error

################### Main Program ################### 

if __name__ == "__main__" :
	logging.basicConfig(level=logging.INFO)
	aa = EmailSamplesDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\EmailSamplesDB_SQL.json",
						r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\DBSetup_SQL.json")
	aa.ConnectDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\tester2.sqlite3")
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
	aa.MakeFeatureVecs(WordListRef,"SelectBodies")
	elapsed_time = time.time() - start_time
	print "Elapsed time:",elapsed_time,'s'
	start_time = time.time()
	aa.MakeFeatureVecs(list_id,"SelectBodies")
	elapsed_time = time.time() - start_time
	print "Elapsed time:",elapsed_time,'s'
	#print "Write a word list to a file"
	#FileName = r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\TestDict.txt"
	#aa.WriteWords("wordlist0",FileName)
	#print "Reset the database"
	#aa.ResetDB()
