'''
Virtual Admin Server for LUL

Description:
	Server handles reminders, agenda
	creation, calendar reminders, etc.
	Use mongodb as database of admins

author(s):
	Jorge Rojas
'''
from sys import path
from os import getcwd
path.append(getcwd())
from scripts.updateAsana import updateAsana
from scripts.createAgendaFromAsana import createAgenda
from flask import Flask, request, render_template

TOTAL_ROUTES = 3
APP_URL = 'http://127.0.0.1:5000'

app = Flask(__name__)

class pageElements:

	error = None

	def __init__(self, title, parent = '/'):
		self.title = title
		self.parent = parent

	def changeParent(self, parent):
		self.parent = parent

def user_confirmed(usrEmail):
	return True

def valid_login(usrEmail, passWord):
	'''
	Given email and password, authorize user 
	to access Virtual Admin Dashboard
	'''
	if usrEmail == 'jrojas@stevens.edu':
		return True
	else:
		return False

@app.route('/')
def renderLanding():
	landingElements = pageElements('Virtual Admin Landing Page')
	return render_template('landingPage.html', pgElements = landingElements)
	# return 'LUL AA Admin Landing Page'

@app.route('/createAgenda')
def runCreateAgenda():
	createAgenda()
	#Return page after createAgenda() finishes execution
	homeElements = pageElements('Virtual Admin Dashboard')
	return render_template('homePage.html', pgElements = homeElements)

@app.route('/home')
def renderHome():
	homeElements = pageElements('Virtual Admin Dashboard', parent = '/home')
	return render_template('homePage.html', pgElements = homeElements)
	# return 'LUL AA Admin Home Page'

@app.route('/login', methods = ['GET', 'POST'])
def renderLogin():
	loginElements = pageElements('Virtual Admin Log-in Page', parent = '/login')
	if request.method == 'POST':
		if valid_login(request.form['email'], request.form['password']) and user_confirmed(request.form['email']):
			return renderHome()
		else:
			loginElements.error = 'ERROR: Invalid username/password'
	
	return render_template('loginPage.html', pgElements=loginElements)
	# return 'LUL AA Admin Login Page'

@app.route('/signUp', methods = ['GET','POST'])
def signUpUser():
	signUpElements = pageElements('Virtual Admin Sign-Up Page', parent = '/signUp')
	if request.method == 'POST':
		return render_template('signUpConfirmationPage.html')
	else:
		return render_template('loginPage.html', pgElements=signUpElements)

@app.route('/updateAsana')
def runUpdateAsana():
	updateAsana()
	#Return page after updateAsana() finishes execution
	homeElements = pageElements('Virtual Admin Dashboard')
	return render_template('homePage.html', pgElements = homeElements)

if __name__ == '__main__':
	app.debug = True
	app.run()