'''
Virtual Admin Server for LUL

Description:
	Server handles reminders, agenda
	creation, calendar reminders, etc.
	Use mongodb as database of admins

author(s):
	Jorge Rojas

TODO:
1- Implement Admin Settings
	a- Make app work with database API Tokens
2- Include SMS reminders using Twilio
	see link -> https://www.twilio.com/docs/libraries/python
3- Add server to make reminders and agenda creation automatic
	a- Implement "cron" jobs for both agendas and reminders (separate server)
4- Cleanup code
	- Create mongoDB util script
	- Delete unnecessary code
	- Comment
5- Update README.rst
	- Include setup (finding and generating API keys)
6- Optimize agenda creation script
'''

'''Utility Imports'''
import sys
import uuid
import hashlib
import logging
import datetime
from os import getcwd
sys.path.append(getcwd())
from multiprocessing import Process

'''Web Imports'''
from pymongo import MongoClient
from oauth2client.client import OAuth2WebServerFlow
from flask import Flask, request, render_template, redirect, url_for, session

'''App Imports'''
from scripts.updateAsana import updateAsana
from scripts.createAgenda import createAgenda
from scripts.utilities import sendEmailConfirmation

'''Web & Worker Clients'''
host_url = 'http://127.0.0.1:5000'
# host_url = 'http://virtualadmin.herokuapp.com'
app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

'''MongoDB Client & Collections'''
# mongo_client = MongoClient('mongodb://heroku_9n5zjh5h:7rtcqvms12rtrib2lc2ts26ga8@ds045064.mongolab.com:45064/heroku_9n5zjh5h')
# va_db = mongo_client['heroku_9n5zjh5h']
#For Localhost use only
mongo_client = MongoClient()
va_db = mongo_client['virtual-admin-db']
c_chapters = va_db['chapters']

def signUpUser(postForm):
	newUser = True
	session['usrName'] = postForm['email'].split('@')[0]
	session['password'] = hashlib.sha512(postForm['password']).hexdigest()
	post = {
		'email': postForm['email'],
		'name': session['usrName'],
		'password': session['password'],
		'joined_on': datetime.datetime.utcnow(),
		'email_confirmed': False,
		'gfolder_link':None,
		'w_agenda_date':None,
		'integrations': {
			'asana': {
				'auth_token':None		
			},
			'gdrive': {
				'client_id':None,
				'client_secret':None,
				'scope':None,
				'redirect_uri':None	
			},
			'slack':{
				'auth_token':None,
				'webhook_url':None
			},
			'twilio':{
				'accnt_sid':None,
				'auth_token':None
			}
		},
		'members': {
			'Add-member': {
				'email': None,
				'phone_num': None,
				'reminder_pref': None
			}
		},
		'organization': None
	}

	try:
		chapter = c_chapters.find({ 'email':postForm['email'] })[0]
	except IndexError:
		chapter = None

	if chapter:
		newUser = False

	if newUser:
		c_chapters.insert_one(post)
		status = None
	elif newUser and postForm['password'] == None:
		status = 'Password is a required field!'
	elif not newUser and postForm['password'] == None:
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

	try:
		chapter = c_chapters.find({ 'email':postForm['email'], 'password':psswrd })[0]
	except IndexError:
		chapter = None

	if chapter:	#If entry found do...
		if chapter['email_confirmed'] == True:
			session['usrName'] = usr_name
			session['password'] = psswrd
			return True
		else:
			return False
	else:
		return False

'''WEB PAGE RENDERING'''
@app.route('/')
def renderLanding():
	return render_template('landingPage.html')

@app.route('/dashboard/<usrName>')
def renderDashboard(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	return render_template('dashboardPage.html', parent = '/dashboard', usr = usrName)

@app.route('/login', methods = ['GET', 'POST'])
def renderLogin(err = None):
	error = None
	if request.method == 'POST':
		if validLogin(request.form):
			return redirect(url_for('renderDashboard', usrName = session['usrName']))
		else:
			error = 'Invalid username/password!\nPlease check your credentials.'
	
	return render_template('loginPage.html', parent = url_for('renderLogin'), err = error)

@app.route('/api-settings/<usrName>')
def renderAPISettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	user = c_chapters.find({ 'name':usrName })[0]
	usrAPIs = user['integrations']

	return render_template('integration_api_settings.html', usr = usrName, usrAPIs = usrAPIs)

@app.route('/admin-settings/<usrName>')
def renderAdminSettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	user = c_chapters.find({ 'name':usrName })[0]
	usrMembers = user['members']
	usrLink = user['gfolder_link']
	usrDate = user['w_agenda_date']

	return render_template('admin_settings.html', usr = usrName, members = usrMembers, usrLink = usrLink, usrDate = usrDate)

'''LOGIN & AUTH URLS'''
@app.route('/oauth2callback')
def oauth2callback():

	chapter = c_chapters.find({ 'name':session['usrName'] })[0]
	gdrive_tokens = chapter['integrations']['gdrive']
	print gdrive_tokens['redirect_uri']
	try:
		flow = OAuth2WebServerFlow(
	    	client_id = gdrive_tokens['client_id'],
	    	client_secret = gdrive_tokens['client_secret'],
	    	scope = gdrive_tokens['scope'],
	    	redirect_uri = gdrive_tokens['redirect_uri']
	    )
	except TypeError:
		msg = 'There is an error with your gdrive API tokens! Please review the credentials.'
		print msg	#DEBUG
		return redirect(url_for('renderAPISettings', usrName = session['usrName'], msg = msg ))
	
	# print request.args	#DEBUG
	if 'code' not in request.args:
		auth_uri = flow.step1_get_authorize_url()
		# print auth_uri	#DEBUG
		return redirect(auth_uri)
	else:
		auth_code = request.args.get('code')
		# print auth_code	#DEBUG
		session['code'] = auth_code
		return redirect(url_for('runCreateAgenda', usrName = session['usrName'] ))

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

@app.route('/signUp', methods = ['GET','POST'])
def signUp():
	if request.method == 'POST':
		status = signUpUser(request.form)
		if status:
			return redirect(url_for('renderLogin', err = status))
		else:
			sendEmailConfirmation(request.form['email'], session['usrName'], host_url)
			return render_template('signUpConfirmationPage.html')
	else:
		return render_template('loginPage.html', parent = url_for('signUp'))

'''API FUNCTIONS'''
@app.route('/setGoogleFolder/<usrName>', methods = ['POST'])
def updateShareableLink(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	gfolder_link = request.form['gfolder_link']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{
			"$set": {
				"gfolder_link": gfolder_link
			}
		}
	)

	print request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'gFolder Link has been successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAdminSettings', usrName = usrName, msg = msg))

@app.route('/members/<usrName>/<memberName>', methods = ['POST'])
def updateMemberDetails(usrName = None, memberName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	if memberName == 'Add-member':
		memberName = request.form['member_name']

	# print request.args	#DEBUG
	email = request.form['email']
	phone_num = request.form['phone_num']
	pref = request.form['reminder_pref']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": { 
				"members.{0}.email".format(memberName) : email,
				"members.{0}.phone_num".format(memberName) : phone_num,
				"members.{0}.reminder_pref".format(memberName) : pref,
			}
		}
	)

	print request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'member settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAdminSettings', usrName = usrName, msg = msg))


@app.route('/integrations/<usrName>/asana', methods = ['POST'])
def updateAsanaSettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	print request.args
	auth_token = request.form['auth_token']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": { "integrations.asana.auth_token" : auth_token }
		}
	)

	print request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'asana settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/gdrive', methods = ['POST'])
def updateGdriveSettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	client_id = request.form['client_id']
	client_secret = request.form['client_secret']
	scope = request.form['scope']
	redirect_uri = request.form['redirect_uri']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": {
						"integrations.gdrive.client_id": client_id, 
						"integrations.gdrive.client_secret": client_secret,
						"integrations.gdrive.scope": scope,
						"integrations.gdrive.redirect_uri": redirect_uri,
					}
		}
	)
	
	print request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'gdrive settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/slack', methods = ['POST'])
def updateSlackSettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	auth_token = request.form['auth_token']
	webhook_url = request.form['webhook_url']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": { 
						"integrations.slack.auth_token": auth_token,
						"integrations.slack.webhook_url": webhook_url
					} 
		}
	)

	print request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'slack settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/twilio', methods = ['POST'])
def updateTwilioSettings(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	sid = request.form['accnt_sid']
	auth_token = request.form['auth_token']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": {
						"integrations.twilio.accnt_sid" : sid,
						"integrations.twilio.auth_token" : auth_token 
					}
		}
	)

	print res	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'twilio settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return redirect(url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/dashboard/<usrName>/createAgenda')
def runCreateAgenda(usrName = None):
	if 'password' not in session:
		#Avoid login bypass
		return redirect(url_for('renderLogin'))
	elif 'code' not in session:
		return redirect(url_for('oauth2callback'))

	chapter = c_chapters.find({ 'name':usrName })[0]
	asana_auth = chapter['integrations']['asana']['auth_token']
	slack_webhook = chapter['integrations']['slack']['webhook_url']

	p = Process(target=createAgenda, args=('agenda', 'debug', session['code'], asana_auth, slack_webhook) )
	p.start()
	return redirect(url_for('renderDashboard', usrName = usrName))

@app.route('/dashboard/<usrName>/updateAsana')
def runUpdateAsana(usrName = None):
	if 'password' not in session:
		return redirect(url_for('renderLogin'))

	chapter = c_chapters.find({ 'name':usrName })[0]
	asana_auth = chapter['integrations']['asana']['auth_token']
	slack_auth = chapter['integrations']['slack']['auth_token']
	slack_webhook = chapter['integrations']['slack']['webhook_url']

	p = Process(target=updateAsana, args=('deliverables', 'debug', slack_auth, slack_webhook, asana_auth) )
	p.start()
	return redirect(url_for('renderDashboard', usrName = usrName))

if __name__ == '__main__':
	app.debug = True
	app.logger.addHandler(logging.StreamHandler(sys.stdout))
	app.logger.setLevel(logging.ERROR)
	app.run()

