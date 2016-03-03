# -*- coding: utf-8 -*-
"""
Creates a temporary database using the system's temporary file infrastructure. This is useful when it is
necessary to maintain multiple data cursors in a database because a temporary copy of a given table can 
be made. Both database connections (the persistent and the temporary ones) can then be open at the same
time - one for reading and one for writing.

Created on Tue Feb 09 16:03:00 2016

@author: Joseph R. Cole
"""

#import pdb
import tempfile
import logging
import json
import os
import sqlite3

class TempDB :
	"""
	Controls the connection to a temporary database. All SQL commands are
	placed in an external JSON file so that the queries do not need to be hard coded.
	"""
	DB_Connect = None
	DB_Cursor = None

	def __init__(self,sqlcmdpath) :
		"""
		Load external data and parameters in preparation to work with a temporary database.

		sqlcmdpath -
			json file with SQL commands for queries on the sqlite3 database

		shared class variables -
			self.DBpath - full path to the temporary database file; will be set in TempDB.CreateDB()
		"""
		self.DBpath = None
		try :
			fhan = open(sqlcmdpath)
			SQLCMDStr = fhan.read()
			fhan.close()
			self.SQLCMDs = json.loads(SQLCMDStr)
		except Exception as detail :
			logging.error("Unable to load SQL commands from %s: %s"%(sqlcmdpath,detail))
			exit()
		self.CreateDB()
		return

	def __del__(self) :
		"""
		Automatically ensures the database connection is closed and any temporary files are deleted
		when all references to this object are gone.
		"""
		self.DisconnectDB()
		if self.DBpath is not None :
			try :
				os.remove(self.DBpath)
				logging.info("Removed temporary database at %s"%self.DBpath)
			except Exception as detail :
				logging.error("Failed to remove temporary database: %s"%self.DBpath)
				logging.error(detail)
			try :
				os.remove('-'.join([self.DBpath,"journal"]))
				logging.info("Removed temporary database journal at %s-journal"%self.DBpath)
			except :
				logging.info("No journal file identified for removal.")
		return

	def CreateDB(self) :
		"""
		Creates a temporary file to use for the database; similar to the unix touch command. The
		full path to the temporary file is saved in self.DBpath
		"""
		try :
			fid,self.DBpath = tempfile.mkstemp(suffix='.sqlite3',prefix='tmp',dir=None,text=False)
			fhan = os.fdopen(fid)
			fhan.close()
			logging.info("Created temporary database at %s"%self.DBpath)
		except :
			logging.error("Unable to create the database at %s"%self.DBpath)
		return

	def ConnectDB(self) :
		"""
		Connect to the temporary database and setup a database cursor
		"""
		try :
			self.DB_Connect = sqlite3.connect(self.DBpath)
			logging.info("Connected to temporary database at %s"%self.DBpath)
			self.DB_Cursor = self.DB_Connect.cursor()
		except Exception as detail:
			logging.error("Failed to connect to the database: %s"%detail)
			self.DB_Connect.rollback()
		return

	def DisconnectDB(self) :
		"""
		Disconnect the temporary database
		"""
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

	def RunCommand(self, sqlstr, params=(), commit=True) :
		"""
		Executes an SQL query against the temporary database

		sqlstr -
			a string containing the SQL command to execute; typically this would be one of the strings
			stored in the dictionary self.SQLCMDs, loaded from a JSON file during initialization
		params -
			an optional tuple containing any runtime values to fill in the sqlstr (marked by ? in the string)
		commit -
			an optional boolean indicating whether or not to commit the change to the database right away
			[default True]
		"""
		self.DB_Cursor.execute(sqlstr, params)
		if commit:
			self.DB_Connect.commit()

	def RunCommands(self, sqlstr, params=[()], commit=True) :
		"""
		Executes many SQL queries against the temporary database

		sqlstr -
			a string containing the SQL command to execute multiple times; typically this would be one of
			the strings stored in the dictionary self.SQLCMDs, loaded from a JSON file during initialization
		params -
			an optional list of tuples containing any runtime values to fill in the sqlstr (marked by ? in the string)
		commit -
			an optional boolean indicating whether or not to commit the changes to the database right away
			[default True]
		"""
		self.DB_Cursor.executemany(sqlstr, params)
		if commit:
			self.DB_Connect.commit()

################### Main Program ################### 

if __name__ == "__main__" :
	#Test code goes here
	logging.basicConfig(level=logging.INFO)
	#logging.basicConfig(filename='example.log',level=logging.INFO)
	#pdb.set_trace()
	aa = TempDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\TempDB_SQL.json")
	aa.ConnectDB()
	print "Creating fresh database"
	aa.CreateDB()
	print "Adding"
	#aa.AddToDB()
	#print "Reset the database"
	#aa.ResetDB()
