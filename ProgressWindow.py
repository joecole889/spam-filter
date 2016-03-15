#import pdb
import Tkinter as tki
import ttk
import threading
import Queue
import time
import logging

class ProgressWindow(tki.Toplevel):
	"""
	"""
	def __init__(self,parent,TrackedFunc,*args,**kwargs):
		logging.debug("Initializing the progress tracker dialog window")

		self.ProgQ = Queue.Queue()
		self.currentstep = 0
		self.parent = parent
		self.params = {'title':"Test Progress",'timer':250}
		self.params.update(kwargs)
		kwargs.pop('title',None)
		kwargs.pop('timer',None)

		tki.Toplevel.__init__(self,parent)
		self.transient(parent)
		self.title(self.params['title'])
		self.result = None
		self.body()
		self.initial_focus = self.buttonbox()
		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		self.geometry("+%d+%d"%(parent.winfo_rootx()+50,
			                    parent.winfo_rooty()+50))
		self.initial_focus.focus_set()

		logging.debug("Initializing the work producer thread")
		self.gp = GenericProducer(self.ProgQ,TrackedFunc,*args,**kwargs)
		self.gp.daemon = True
		self.gp.start()

		self._job = self.after(0,self.checkqueue)
		logging.debug("Storing timer job %s"%self._job)
		logging.debug("Entering the dialog event loop")
		self.wait_window(self)

	def buttonbox(self) :
		box = tki.Frame(self)
		w = tki.Button(box,text="Cancel",width=10,command=self.cancel)
		w.pack(side=tki.LEFT,padx=5,pady=5)
		self.bind("<Escape>",self.cancel)
		box.pack()
		return w

	def body(self) :
		bod = tki.Frame(self)
		self.ProgBar = ttk.Progressbar(bod, orient='horizontal', length=300, mode='determinate')
		self.ProgBar.pack(padx=10, pady=10)
		bod.pack(padx=5, pady=5)
		bod.update_idletasks()

	def cancel(self,_=None) :
		logging.debug("Shutting down the dialog")
		if self._job is not None :
			logging.debug("Cancelling the checkqueue() timer job %s"%self._job)
			self.after_cancel(self._job)
			self._job = None
		else :
			logging.debug("No timer job to cancel")
		if self.gp.is_alive() and not self.gp.stopped() :
			logging.debug("Stopping the GenericProducer thread early")
			self.gp.stop()
			try :
				self.gp.join()
			except Exception as detail :
				logging.debug(detail)
		self.parent.focus_set()
		self.destroy()
	
	def checkqueue(self) :
		#logging.debug("Executing timer job %s"%self._job)
		self._job = None
		reset_timer = True
		try :
			while self.ProgQ.qsize() :
				stepamount = self.ProgQ.get(False)
				if isinstance(stepamount,str) and (stepamount == "_ProducerDone") :
					reset_timer = False
					logging.debug("Caught the work finished signal")
					break
				logging.debug("Got step %f from queue"%stepamount)
				self.currentstep += stepamount
				assert self.currentstep>=0 and self.currentstep<=100,"Bad step value gotten from queue"
				logging.debug("Updating the progressbar widget")
				self.ProgBar.step(stepamount)
				self.ProgBar.update_idletasks()
				logging.debug("progressbar widget update complete")
				self.ProgQ.task_done()
		except Queue.Empty as detail :
			logging.debug("Queue was empty, setting timer to check again in a bit")
		except AssertionError as detail :
			logging.error(detail)
			reset_timer = False
		finally :
			if reset_timer :
				self._job = self.after(self.params['timer'],self.checkqueue)
				#logging.debug("Storing timer job %s"%self._job)
			else :
				self.cancel()

class GenericProducer(threading.Thread) :
	def __init__(self,ProgQ,IO_heavy_func,*args,**kwargs) :
		super(GenericProducer,self).__init__()
		self.stopflag = threading.Event()
		self.ProgQ = ProgQ
		self.arglist = list(args)
		self.arglist.append(self)
		self.params = kwargs
		self.IO_heavy_func = IO_heavy_func

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
	
	def put(self,val) :
		self.ProgQ.put(val)

	def run(self) :
		logging.debug("GenericProducer thread is started")
		self.IO_heavy_func(*self.arglist,**self.params)
		logging.debug("GenericProducer thread finished work.")
		self.stop()
		self.ProgQ.put("_ProducerDone")

####################################### Main Program #######################################

if __name__ == "__main__":
	def testproducerfunc(Wrapper=None) :
		for ii in range(5) :
			time.sleep(1)
			if Wrapper is not None :
				if not Wrapper.stopped() :
					logging.debug("Producer thread adding a step to the queue: %d"%ii)
					Wrapper.put(20)
				else :
					break
		logging.debug("Producer function finished work")

	logging.basicConfig(level=logging.DEBUG)
	root = tki.Tk()
	frameref = tki.Frame(root)
	frameref.pack()
	butref = tki.Button(frameref,text="Hello",command= lambda: ProgressWindow(root,testproducerfunc))
	butref.pack()
	logging.debug("Entering root.mainloop()")
	root.mainloop()
