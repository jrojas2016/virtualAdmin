'''
Virtual Admin Server for LUL

Description:
	Server handles reminders, agenda
	creation, calendar reminders, etc.
	Use mongodb as database of admins

author(s):
	Jorge Rojas
'''

'''Utility Imports'''
import sys
import uuid
import smtplib
import hashlib
import logging
import datetime
from os import getcwd
sys.path.append(getcwd())
# from optparse import OptionParser
from multiprocessing import Process

'''Web Imports'''
# from worker import conn
from oauth2client import client
from pymongo import MongoClient
from rq import Queue, get_failed_queue
from flask import Flask, request, render_template, redirect, url_for, session

'''App Imports'''
from scripts.updateAsana import updateAsana
from scripts.createAgenda import createAgenda

'''Web & Worker Clients'''
# jobCnt = [0]
#For debug change async to False
# q = Queue(connection = conn, async = True)
# print q.connection
# host_url = 'http://127.0.0.1:5000'
host_url = 'http://virtualadmin.herokuapp.com'
# curr_user = {'usrName':'', 'email':''}
app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

'''MongoDB Client & Collections'''
mongo_client = MongoClient('mongodb://heroku_9n5zjh5h:7rtcqvms12rtrib2lc2ts26ga8@ds045064.mongolab.com:45064/heroku_9n5zjh5h')
va_db = mongo_client['heroku_9n5zjh5h']
#For Localhost use only
# mongo_client = MongoClient()
# va_db = mongo_client['virtual-admin-db']
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
		'{0}/confirm/{1}'.format(host_url, session['usrName']),
		'',
		'Sincerely,',
		'Virtual Admin Team'
	]

	message = '\r\n'.join( msg )

	try:
		server.sendmail( sender, curr_user['email'], message )
		print 'Email sent successfully to %s'%postForm['email']
	except:
		print 'Email failed to send to %s!'%postForm['email']

	server.quit()

def signUpUser(postForm):
	newUser = True
	session['email'] = postForm['email']
	session['usrName'] = postForm['email'].split('@')[0]
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

	chapter = c_chapters.find({ 'email':session['email'] })[0]
	if chapter:
		newUser = False

	if newUser:
		c_chapters.insert_one(post)
		status = None
	elif newUser and usr_psswrd == None:
		status = 'Password is a required field!'
	elif not newUser and usr_psswrd == None:
		status = 'Password is a required field!'
	else:
		status = 'There already exists an account with the email {0}. Please Log in here: {1}/login'.format(usr_email, host_url)

	return status


def validLogin(postForm):
	'''
	Given email and password, authorize user 
	to access Virtual Admin Dashboard
	'''
	usr_name = postForm['email'].split('@')[0]
	psswrd = hashlib.sha512(postForm['password']).hexdigest()
	chapter = c_chapters.find({ 'email':postForm['email'], 'password':psswrd })[0]
	if chapter:	#If entry found do...
		if chapter['email_confirmed'] == True:
			session['usrName'] = usr_name
			session['email'] = postForm['email']
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
	# credentials = client.OAuth2Credentials.from_json(session['credentials'])
	# if credentials.access_token_expired:
	# 	return redirect(url_for('oauth2callback'))

	#createAgenda(projKey, slackChan, gAuthCode)
	p = Process(target=createAgenda, args=('agenda', 'debug', session['credentials'],) )
	p.start()
	# res = q.enqueue(createAgenda, 'agenda', 'debug', session['credentials'], timeout = 300000, job_id = str(jobCnt[0]))
	# jobCnt[0] += 1
	# if res.result == 0:	#DEBUG
	# 	print "Agenda was successfully created!"
	return redirect(url_for('renderDashboard', name = name))

@app.route('/dashboard/<name>')
def renderDashboard(name = None):
	return render_template('dashboardPage.html', parent = '/dashboard', usr = name)

@app.route('/oauth2callback')
def oauth2callback():
	flow = client.flow_from_clientsecrets(
    	'client_secrets.json',
    	scope = 'https://www.googleapis.com/auth/drive',
    	redirect_uri = url_for('oauth2callback', _external = False)
    )
	print request.args	#DEBUG
	if 'code' not in request.args:
		auth_uri = flow.step1_get_authorize_url()
		print auth_uri	#DEBUG
		return redirect(auth_uri)
	else:
		auth_code = request.args.get('code')
		print auth_code	#DEBUG
		session['credentials'] = auth_code
		return redirect(url_for('runCreateAgenda', name = session['usrName']))
	

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
	# updateAsana(projKey, slackChan)
	p = Process(target=updateAsana, args=('deliverables', 'strictly_business',) )
	p.start()
	# res = q.enqueue(updateAsana, 'deliverables', 'debug', timeout = 5000, job_id = str(jobCnt[0]))
	# jobCnt[0] += 1
	# if res.result == 0:	#DEBUG
	# 	print "Update to Asana was successfull!"
	return redirect(url_for('renderDashboard', name = name))

if __name__ == '__main__':
	app.debug = True
	app.logger.addHandler(logging.StreamHandler(sys.stdout))
	app.logger.setLevel(logging.ERROR)
	app.run()

