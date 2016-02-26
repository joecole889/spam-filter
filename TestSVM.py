Xtest,Ytest = self.DBobj.GetXY(listchoice,2)
maxtrial = 0
maxCV = 0
bestii = 0
for ii,OutTup in enumerate(self.OutputList) :
	if OutTup[1] > maxtrial :
		maxtrial = OutTup[1]
		maxCV = 0
	if OutTup[4] > maxCV :
		maxCV = OutTup[4]
		bestii = ii
TestScore = self.OutputList[bestii][0].score(Xtest,Ytest)
logging.debug("SVM test result: %d, %d, %f, %f"%(bestii,self.OutputList[bestii][1],self.OutputList[bestii][2],TestScore))
