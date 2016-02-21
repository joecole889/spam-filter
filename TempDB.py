#import pdb
import tempfile
import logging
import json
import os
import sqlite3

class TempDB :
	DB_Connect = None
	DB_Cursor = None

	def __init__(self,sqlcmdpath) :
		self.DBpath = None
		try :
			fhan = open(sqlcmdpath)
			SQLCMDStr = fhan.read()
			fhan.close()
			self.SQLCMDs = json.loads(SQLCMDStr)
		except Exception as detail :
			logging.error("Unable to load SQL commands from %s: %s"%(sqlcmdpath,detail))
		self.CreateDB()
		return

	def __del__(self) :
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
		try :
			fid,self.DBpath = tempfile.mkstemp(suffix='.sqlite3',prefix='tmp',dir=None,text=False)
			fhan = os.fdopen(fid)
			fhan.close()
			logging.info("Created temporary database at %s"%self.DBpath)
		except :
			logging.error("Unable to create the database at %s"%self.DBpath)
		return

	def ConnectDB(self) :
		try :
			self.DB_Connect = sqlite3.connect(self.DBpath)
			logging.info("Connected to temporary database at %s"%self.DBpath)
			self.DB_Cursor = self.DB_Connect.cursor()
		except Exception as detail:
			logging.error("Failed to connect to the database: %s"%detail)
			self.DB_Connect.rollback()
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

	def RunCommand(self, sqlstr, params=(), commit=True) :
		self.DB_Cursor.execute(sqlstr, params)
		if commit:
			self.DB_Connect.commit()

	def RunCommands(self, sqlstr, params=[], commit=True) :
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
