# -*- coding: utf-8 -*-
"""
Contains a class to generate feature vectors from email text. Utility functions are also included for
creating the dictionaries needed to build the feature vectors. Uses the Porter stemmer algorithm
as implemented in the natural language processing toolkit (nltk).

Created on Fri Feb 12 13:35:00 2016

@author: JCole119213
"""

#import pdb
import re
from nltk.stem.porter import PorterStemmer

class FeatureVecGen :
	def __init__(self,DictList) :
		"""
		Initialize the feature vector creation engine with a list of words from a dictionary.

		DictList -
			a list of strings (words) from a dictionary, used to build the feature vectors
		"""
		self.HashDict(DictList)	#Initializes self.DictHash
		return

	def MakeVec(self,SampleBody) :
		"""
		Implements the full flow of creating a feature vector from the raw string extracted from an email

		SampleBody -
			unprocessed text from the body of an email message

		Return values:
			featurevec -
				a list of integers (actually only 0 or 1, but stored as int) indicating the absence or
				presence in SampleBody of each dictionary word from self.DictHash
		"""
		SampleWords = self.RegularizeWords(SampleBody)
		SampleWords = self.StemWords(SampleWords)
		featurevec = self.MarkWordPresence(SampleWords)
		return featurevec

	def MarkWordPresence(self,EmailContentsReg) :
		"""
		Create a feature vector from the regularized text of an email message body

		EmailContentsReg -
			a list of strings (words) after processing by the FeatureVecGen.RegularizeWords() method

		Return values:
			FeatureVec -
				a list of integers (actually only 0 or 1, but stored as int) indicating the absence or
				presence in EmailContentsReg of each dictionary word from self.DictHash
		"""
		FeatureVec = [0] * len(self.DictHash)
		for Word in EmailContentsReg :
			FeatureInd = self.DictHash.get(Word,-1)  # Check if word is in the dictionary
			if FeatureInd != -1 :
				FeatureVec[FeatureInd] = 1	  # Note the presence of the word as a feature - only one instance of the word matters
		return FeatureVec

	def HashDict(self,DictList) :
		"""
		Creates a hash to determine the presence of a word in the dictionary and the corresponding feature location

		DictList -
			a list of strings (words) from a dictionary, used to build the feature vectors
		"""
		self.DictHash = dict()
		for ind,Word in enumerate(DictList) :
			self.DictHash[Word] = ind
		return

	@classmethod
	def ParetoWords(cls,TextToProcess) :
		"""
		Creates a dictionary with a count of all words in the text to be processed

		TextToProcess -
			unprocessed text from the body of an email message

		Return values:
			DictHist -
				a Python dictionary where the value associated with each key (regularized, stemmed words) is
				a count of the number of times that word occurred in TextToProcess
		"""
		DictHist = dict()

		Words = cls.RegularizeWords(TextToProcess)
		ShortWords = cls.StemWords(Words)

		# Create word histogram
		for ShortWord in ShortWords :
			DictHist[ShortWord] = DictHist.get(ShortWord,0) + 1 # Create the histogram of word counts

		return DictHist

	@staticmethod
	def RegularizeWords(FileStr) :
		"""
		Removes email addresses, punctuation, HTML tags, etc.

		FileStr -
			unprocessed text from the body of an email message
			
		Return values:
			FileWords -
				a list of stings split by punctuation and filtered from 0 length strings
		"""
		FileStr = FileStr.lower()    # Go to lower case
		FileStr = re.sub('<[^<>]+>',' ',FileStr)    # Remove HTML tags without < or > inside
		FileStr = re.sub('\d+','number',FileStr)    # Replace all numbers with the string 'number'
		FileStr = re.sub('(http|https)://[^\s]*','httpaddr',FileStr)    # Replace all URLs with the string 'httpaddr'
		FileStr = re.sub('[^\s]+@[^\s]+','emailaddr',FileStr)    # Replace all emails with the string 'emailaddr'
		FileStr = re.sub('[$]+','dollar',FileStr)    # Replace all $ signs with the string 'dollar' as spam is likely to reference money
		FileWords = re.split('[\s\|@/#\.\-:&\*\+=\[\]\?!\(\)\{\},\'">_<;%~]',FileStr)
		return filter(None,FileWords)

	@staticmethod
	def StemWords(WordList) :
		"""
		Extracts the root of a word (e.g. stepped -> step) using the Porter stemmer algorithm

		WordList -
			a list of strings (words) as processed by the FeatureVecGen.RegularizeWords() method

		Return values:
			StemmedWordList - a list of root words from the input list
		"""
		stemmer = PorterStemmer()
		StemmedWordList = []
		# Loop over list and stem the words
		for Word in WordList :
			assert (Word.find('[\W_]') == -1),'Failed to remove all non-alphanumeric characters: %s' % Word
			try :   # Not sure about the reliability of the Porter Stemmer code, so use a try/catch block
				ShortWord = stemmer.stem(Word)
				assert(len(ShortWord) > 2) # Ignore words less than 3 characters long
				StemmedWordList.append(ShortWord)
			except :
				continue
		return StemmedWordList

################### Main Program ################### 

if __name__ == "__main__" :
	print "Test code goes here."
