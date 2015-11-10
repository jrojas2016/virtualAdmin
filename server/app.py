'''
Virtual Admin Server for LUL

Description:
	Server handles reminders, agenda
	creation, calendar reminders, etc.
	Use mongodb as database of admins

author(s):
	Jorge Rojas
'''
import smtplib
import hashlib
import datetime
from rq import Queue
from sys import path
from os import getcwd
from worker import conn
path.append(getcwd())
from pymongo import MongoClient
from scripts.updateAsana import updateAsana
from scripts.createAgendaFromAsana import createAgenda
from flask import Flask, request, render_template, redirect

app = Flask(__name__)
q = Queue(connection=conn)

'''MongoDB Client & Collections'''
client = MongoClient('mongodb://heroku_9n5zjh5h:7rtcqvms12rtrib2lc2ts26ga8@ds045064.mongolab.com:45064/heroku_9n5zjh5h')
va_db = client['heroku_9n5zjh5h']
c_chapters = va_db['chapters']

class pageElements:
	usr = None
	error = None

	def __init__(self, title, parent = '/'):
		self.title = title
		self.parent = parent

	def changeParent(self, parent):
		self.parent = parent

def sendEmailConfirmation(postForm):
	#Implement email confirmation after sign-up
	sender = 'va.test2016@gmail.com'
	passwrd = 'VAsorullit0'
	server = smtplib.SMTP("smtp.gmail.com",587)
	server.starttls()
	server.login(sender, passwrd)
	send_email = postForm['email']
	send_name = send_email.split('@')[0]
	msg = [ 
		'From: %s'%sender, 
		'To: %s'%send_email,
		'Subject: Virtual Admin - Email Confirmation',
		'',
		'Thanks for joining Virtual Admin. To confirm your email please click the link below:',
		'',
		'http://virtualadmin.herokuapp.com/confirm/%s'%send_name,
		'',
		'Sincerely,',
		'Virtual Admin Team'
	]

	message = '\r\n'.join( msg )

	try:
		server.sendmail( sender, send_email, message )
		print 'Email sent successfully to %s'%postForm['email']
	except:
		print 'Email failed to send to %s!'%postForm['email']

	server.quit()

def signUpUser(postForm):
	newUser = True
	usr_email = postForm['email']
	usr_name = usr_email.split('@')[0]
	usr_psswrd = postForm['password']
	post = {
		'email': usr_email,
		'name': usr_name,
		'password': hashlib.sha512(usr_psswrd).hexdigest(),
		'joined-on': datetime.datetime.utcnow(),
		'email_confirmed': False,
		'integrations': [ None ],
		'organization': None
	}

	for cur_chapter in c_chapters.find():
		if cur_chapter['email'] == usr_email:
			newUser = False

	if newUser:
		c_chapters.insert_one(post)
		status = None
	elif newUser and usr_psswrd == None:
		status = 'Password is a required field!'
	elif not newUser and usr_psswrd == None:
		status = 'Password is a required field!'
	else:
		status = 'There already exists an account with the email %s. Please Log in here: http://virtualadmin.herokuapp.com/login'%usr_email

	return status


def validLogin(postForm):
	'''
	Given email and password, authorize user 
	to access Virtual Admin Dashboard
	'''
	psswrd = hashlib.sha512(postForm['password']).hexdigest()
	for cur_chapter in c_chapters.find():
		if postForm['email'] == cur_chapter['email'] and psswrd == cur_chapter['password']:
			if cur_chapter['email_confirmed'] == True:
				return True
			else:
				return False
		else:
			return False

@app.route('/')
def renderLanding():
	landingElements = pageElements('Virtual Admin Landing Page')
	return render_template('landingPage.html', pgElements = landingElements)

@app.route('/confirm/<usrName>')
def confirmUser(usrName = None):

	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": {
				"email_confirmed": True
			} 
		}
	)
	print res
	if res['updatedExisting'] == True:
		print 'User was successfully confirmed!'
	else:
		print 'Failed to confirm user!'

	loginElements = pageElements('Virtual Admin Log-in Page', parent = '/login')
	return render_template('loginPage.html', pgElements = loginElements)

@app.route('/dashboard/<name>/createAgenda')
def runCreateAgenda(name = None):
	res = q.enqueue(createAgenda, 'debug')
	# createAgenda()
	# homeElements = pageElements('Virtual Admin Dashboard')
	return redirect('/dashboard/%s'%name)
	# return render_template('dashboardPage.html', pgElements = homeElements)

@app.route('/dashboard/<name>')
def renderDashboard(name = None):
	dashElements = pageElements('Virtual Admin Dashboard', parent = '/dashboard')
	dashElements.usr = name
	return render_template('dashboardPage.html', pgElements = dashElements)

@app.route('/login', methods = ['GET', 'POST'])
def renderLogin():
	loginElements = pageElements('Virtual Admin Log-in Page', parent = '/login')
	if request.method == 'POST':
		if validLogin(request.form):
			usr_name = request.form['email'].split('@')[0]
			return redirect('/dashboard/%s'%usr_name)
		else:
			loginElements.error = 'ERROR: Invalid username/password'
	
	return render_template('loginPage.html', pgElements = loginElements)

@app.route('/signUp', methods = ['GET','POST'])
def signUp():
	signUpElements = pageElements('Virtual Admin Sign-Up Page', parent = '/signUp')
	if request.method == 'POST':
		status = signUpUser(request.form)
		if status:
			loginElements = pageElements('Virtual Admin Sign-Up Page', parent = '/login')
			loginElements.error = status
			return render_template('loginPage.html', pgElements = loginElements)
		else:
			sendEmailConfirmation(request.form)
			return render_template('signUpConfirmationPage.html')
	else:
		return render_template('loginPage.html', pgElements = signUpElements)

@app.route('/dashboard/<name>/updateAsana')
def runUpdateAsana(name = None):
	res = q.enqueue(updateAsana, 'debug', 'debug')
	# updateAsana()
	homeElements = pageElements('Virtual Admin Dashboard')	#Redirect page
	return redirect('/dashboard/%s'%name)
	# return render_template('dashboardPage.html', pgElements = homeElements)

if __name__ == '__main__':
	app.debug = True
	app.run()

