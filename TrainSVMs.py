from sklearn.svm import SVC
from EmailSamplesDB import EmailSamplesDB
import logging

if __name__ == "__main__" :
	logging.basicConfig(level=logging.INFO)
	aa = EmailSamplesDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\EmailSamplesDB_SQL.json",
						r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\DBSetup_SQL.json")
	aa.ConnectDB(r"C:\Users\jcole119213\Documents\Python Scripts\LearningCurveApp\tester2.sqlite3")

	jj = 0
	clfs = []
	Cs = [0.3]
	Xcv,Ycv = aa.GetXY("wordlist0",1)
	Xtrain = []
	Ytrain = []
	NumTraining = aa.GetTrainSampleCount()
	step = 100
	for m in range(0,NumTraining,step) :
		Xs,Ys = aa.GetXY("wordlist0",0,step,m)
		Xtrain.extend(Xs)
		Ytrain.extend(Ys)
		for cost in Cs :
			clfs.append(SVC(C=cost,kernel='linear'))
			clfs[jj].fit(Xtrain,Ytrain)
			TrainScore = clfs[jj].score(Xtrain,Ytrain)
			CVScore = clfs[jj].score(Xcv,Ycv)
			print jj, m+step, cost, TrainScore, CVScore
			jj += 1
	Xtest,Ytest = aa.GetXY("wordlist0",2)
	TestScore = clfs[-1].score(Xtest,Ytest)
	print "SVM test result:",jj-1,m+step,cost,TestScore
