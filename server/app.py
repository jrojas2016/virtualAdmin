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
import json, base64
from rq import Queue
from sys import path
from os import getcwd
from worker import conn
path.append(getcwd())
from oauth2client import client
from pymongo import MongoClient
from scripts.updateAsana import updateAsana
from scripts.createAgendaFromAsana import createAgenda
from flask import Flask, request, render_template, redirect, url_for, session, escape

app = Flask(__name__)
app.secret_key = '\x14\n\x92\xb1V\x98\xad\xb8u^\xd3v\x8a\x07\x82\xcd\xd4-l\x84#\x8bw/'
q = Queue(connection=conn)

'''MongoDB Client & Collections'''
client = MongoClient('mongodb://heroku_9n5zjh5h:7rtcqvms12rtrib2lc2ts26ga8@ds045064.mongolab.com:45064/heroku_9n5zjh5h')
va_db = client['heroku_9n5zjh5h']
c_chapters = va_db['chapters']

def sendEmailConfirmation(postForm):
	#Implement email confirmation after sign-up
	sender = 'va.test2016@gmail.com'
	passwrd = 'VAsorullit0'
	server = smtplib.SMTP("smtp.gmail.com",587)
	server.starttls()
	server.login(sender, passwrd)
	msg = [ 
		'From: %s'%sender, 
		'To: %s'%session['email'],
		'Subject: Virtual Admin - Email Confirmation',
		'',
		'Thanks for joining Virtual Admin. To confirm your email please click the link below:',
		'',
		'http://virtualadmin.herokuapp.com/confirm/%s'%session['usrName'],
		'',
		'Sincerely,',
		'Virtual Admin Team'
	]

	message = '\r\n'.join( msg )

	try:
		server.sendmail( sender, session['email'], message )
		print 'Email sent successfully to %s'%postForm['email']
	except:
		print 'Email failed to send to %s!'%postForm['email']

	server.quit()

def signUpUser(postForm):
	newUser = True
	session['email'] = postForm['email']
	session['usrName'] = usr_email.split('@')[0]
	usr_psswrd = postForm['password']
	post = {
		'email': session['email'],
		'name': session['usrName'],
		'password': hashlib.sha512(usr_psswrd).hexdigest(),
		'joined-on': datetime.datetime.utcnow(),
		'email_confirmed': False,
		'integrations': [ None ],
		'organization': None
	}

	for cur_chapter in c_chapters.find():
		if cur_chapter['email'] == session['email']:
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
	usr_name = postForm['email'].split('@')[0]
	session['usrName'] = usr_name
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
	return render_template('landingPage.html')

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
		return

	return redirect(url_for('renderLogin'))

@app.route('/dashboard/<name>/createAgenda')
def runCreateAgenda(name = None):
	if 'credentials' not in session:
		return redirect(url_for('oauth2callback'))
	credentials = client.OAuth2Credentials.from_json(session['credentials'])
	if credentials.access_token_expired:
		return redirect(url_for('oauth2callback'))

	drive = GoogleDrive(session['credentials'])

	# createAgenda(projKey, drive)
	res = q.enqueue(createAgenda, 'debug', drive, timeout=500)
	return redirect(url_for('renderDashboard', name = session['usrName']))

@app.route('/dashboard/<name>')
def renderDashboard(name = None):
	return render_template('dashboardPage.html', parent = '/dashboard', usr = name)

@app.route('/oauth2callback')
def oauth2callback():
	flow = client.flow_from_clientsecrets(
		getcwd() + '/client_secrets.json',
		scope='https://www.googleapis.com/auth/drive',
		redirect_uri=url_for('oauth2callback', _external=True)
	)

	if 'code' not in request.args:
		auth_uri = flow.step1_get_authorize_url()
		return redirect(auth_uri)
	else:
		auth_code = request.args.get('code')
		print auth_code
		# credentials = flow.step2_exchange(auth_code)
		session['credentials'] = json.loads(auth_code)
		return redirect(flask.url_for('runCreateAgenda', name = session['usrName']))
	

@app.route('/login', methods = ['GET', 'POST'])
def renderLogin(err = None):
	error = None
	if request.method == 'POST':
		if validLogin(request.form):
			return redirect(url_for('renderDashboard', name = session['usrName']))
		else:
			error = 'Invalid username/password!\nPlease check your credentials.'
	
	return render_template('loginPage.html', parent = url_for('renderLogin'), err = error)

@app.route('/signUp', methods = ['GET','POST'])
def signUp():
	if request.method == 'POST':
		status = signUpUser(request.form)
		if status:
			return redirect(url_for('renderLogin', err = status))
		else:
			sendEmailConfirmation(request.form)
			return render_template('signUpConfirmationPage.html')
	else:
		return render_template('loginPage.html', parent = url_for('signUp'))

@app.route('/dashboard/<name>/updateAsana')
def runUpdateAsana(name = None):
	# updateAsana(projKey, chan)
	res = q.enqueue(updateAsana, 'debug', 'debug', timeout=500)
	return redirect(url_for('renderDashboard', name = session['usrName']))

if __name__ == '__main__':
	app.debug = True
	app.run()

