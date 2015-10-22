#!/usr/local/bin/python2.7
'''
LUL Administrator Launcher:
Simple GUI to run other administrative 
python scripts

Author(s):
	Jorge Rojas
'''
import math
import Tkinter
import subprocess
from PIL import Image, ImageTk

WINDOW_HEIGHT = 250
WINDOW_WIDTH = 345

class rFrame(Tkinter.Frame):
  
	def __init__(self, parent):
		Tkinter.Frame.__init__(self, parent, background="white")   
		 
		self.parent = parent
		
		self.initUI()
	
	def taskReminder(self):
		terminal_cmd = ['python', 'scripts/updateAsana.py']
		subprocess.Popen( terminal_cmd )

	def agendaCreator(self):
		terminal_cmd = ['python', 'scripts/createAgendaFromAsana.py', 'agenda', '1. Agendas & Minutes/2015 - 2016']
		subprocess.Popen( terminal_cmd )

	def sendInvites(self):
		terminal_cmd = ['python', 'scripts/personalEmailer.py', '-d', 'jrojas2016@gmail.com']
		subprocess.Popen( terminal_cmd )

	def initUI(self):
	  	
		self.parent.title("LUL Virtual Admin")
		self.pack(fill=Tkinter.BOTH, expand=1)

		taskReminder = Tkinter.Button(self, text="Task Reminder", command=self.taskReminder)
		taskReminder.grid(row = 0, column = 0)

		createAgenda = Tkinter.Button(self, text="Create Agenda", command=self.agendaCreator)
		createAgenda.grid(row = 0, column = 1)

		sendInvites = Tkinter.Button(self, text="Send Invites", command=self.sendInvites)
		sendInvites.grid(row = 0, column = 2)

def main():
  
	root = Tkinter.Tk()
	root.resizable(0,0)	#Avoid window resizing
	img = ImageTk.PhotoImage(Image.open("media/lul_letters_reflection.jpg"))
	panel = Tkinter.Label(root, image = img)
	panel.pack(side = "top", fill = "both", expand = "yes")
	root.geometry("%sx%s+0+0"%(WINDOW_WIDTH, WINDOW_HEIGHT))
	app = rFrame(root)
	root.mainloop() 

if __name__ == '__main__':
	main()

