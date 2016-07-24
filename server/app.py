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
	b- Implement more permanent session
2- Include SMS reminders using Twilio
	see link -> https://www.twilio.com/docs/libraries/python
3- Add server to make reminders and agenda creation automatic
	a- Implement "cron" jobs for both agendas and reminders (separate server)
4- Cleanup code
	- Create mongoDB util script
	- Create ApiUtil script with all API functions
	- Delete unnecessary code
	- Comment
5- Update README.rst
	- Include setup (finding and generating API keys)
6- Optimize agenda creation script
'''

'''Utility Imports'''
import sys
import logging
from os import getcwd
sys.path.append(getcwd())
from multiprocessing import Process

'''Web Imports'''
import flask as fl
from pymongo import MongoClient
import oauth2client.client as client

'''App Imports'''
import scripts.Utils as ut
import scripts.ApiUtils as au

'''Web & Worker Clients'''
host_url = 'http://127.0.0.1:5000'
# host_url = 'http://virtualadmin.herokuapp.com'
app = fl.Flask(__name__)
app.secret_key = ut.generateAppKey()
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

'''MongoDB Client & Collections'''
#For Localhost use only
mongo_client = MongoClient()
va_db = mongo_client['virtual-admin-db']
c_chapters = va_db['chapters']

def signUpUser(postForm):
	newUser = True
	fl.session['usrName'] = postForm['email'].split('@')[0]
	fl.session['password'] = ut.hashPassword(postForm['password'])
	post = {
		'email': postForm['email'],
		'name': fl.session['usrName'],
		'password': fl.session['password'],
		'joined_on': ut.dateNow(),
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
				'auth_token':None,
				'twilio_num':None,
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
	psswrd = ut.hashPassword(postForm['password'])

	try:
		chapter = c_chapters.find({ 'email':postForm['email'], 'password':psswrd })[0]
	except IndexError:
		chapter = None

	if chapter:	#If entry found do...
		if chapter['email_confirmed'] == True:
			fl.session['usrName'] = usr_name
			fl.session['password'] = psswrd
			return True
		else:
			return False
	else:
		return False

'''WEB PAGE RENDERING'''
@app.route('/')
def renderLanding():
	return fl.render_template('landingPage.html')

@app.route('/dashboard/<usrName>')
def renderDashboard(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	return fl.render_template('dashboardPage.html', parent = '/dashboard', usr = usrName)

@app.route('/login', methods = ['GET', 'POST'])
def renderLogin(err = None):
	error = None
	if fl.request.method == 'POST':
		if validLogin(fl.request.form):
			return fl.redirect(fl.url_for('renderDashboard', usrName = fl.session['usrName']))
		else:
			error = 'Invalid username/password!\nPlease check your credentials.'
	
	return fl.render_template('loginPage.html', parent = fl.url_for('renderLogin'), err = error)

@app.route('/api-settings/<usrName>')
def renderAPISettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	user = c_chapters.find({ 'name':usrName })[0]
	usrAPIs = user['integrations']

	return fl.render_template('integration_api_settings.html', usr = usrName, usrAPIs = usrAPIs)

@app.route('/admin-settings/<usrName>')
def renderAdminSettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	user = c_chapters.find({ 'name':usrName })[0]
	usrMembers = user['members']
	usrLink = user['gfolder_link']
	usrDate = user['w_agenda_date']

	return fl.render_template('admin_settings.html', usr = usrName, members = usrMembers, usrLink = usrLink, usrDate = usrDate)

'''LOGIN & AUTH URLS'''
@app.route('/oauth2callback')
def oauth2callback():

	chapter = c_chapters.find({ 'name':fl.session['usrName'] })[0]
	gdrive_tokens = chapter['integrations']['gdrive']
	print gdrive_tokens['redirect_uri']

	try:
		# flow = client.flow_from_clientsecrets('client_secrets.json',	#DEBUG
		# 					scope='https://www.googleapis.com/auth/drive',
		# 					redirect_uri='http://127.0.0.1:5000/oauth2callback')
		flow = client.OAuth2WebServerFlow(
			client_id = gdrive_tokens['client_id'],
			client_secret = gdrive_tokens['client_secret'],
			scope = gdrive_tokens['scope'],
			redirect_uri = gdrive_tokens['redirect_uri']
		)
	except TypeError:
		msg = 'There is an error with your gdrive API tokens! Please review the credentials.'
		print msg	#DEBUG
		return fl.redirect(fl.url_for('renderAPISettings', usrName = fl.session['usrName'], msg = msg ))
	
	# print fl.request.args	#DEBUG
	if 'code' not in fl.request.args:
		auth_uri = flow.step1_get_authorize_url()
		# print auth_uri	#DEBUG
		return fl.redirect(auth_uri)
	else:
		auth_code = fl.request.args.get('code')
		# print auth_code	#DEBUG
		fl.session['code'] = auth_code
		return fl.redirect(fl.url_for('runCreateAgenda', usrName = fl.session['usrName'] ))

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

	return fl.redirect(fl.url_for('renderLogin'))

@app.route('/signUp', methods = ['GET','POST'])
def signUp():
	if fl.request.method == 'POST':
		status = signUpUser(fl.request.form)
		if status:
			return fl.redirect(fl.url_for('renderLogin', err = status))
		else:
			ut.sendEmailConfirmation(fl.request.form['email'], fl.session['usrName'], host_url)
			return fl.render_template('signUpConfirmationPage.html')
	else:
		return fl.render_template('loginPage.html', parent = fl.url_for('signUp'))

'''API FUNCTIONS'''
@app.route('/setGoogleFolder/<usrName>', methods = ['POST'])
def updateShareableLink(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	gfolder_link = fl.request.form['gfolder_link']
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

	print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'gFolder Link has been successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAdminSettings', usrName = usrName, msg = msg))

@app.route('/members/<usrName>/<memberName>', methods = ['POST'])
def updateMemberDetails(usrName = None, memberName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	# print fl.request.args	#DEBUG
	if memberName == 'Add-member':
		memberName = fl.request.form['member_name']

	email = fl.request.form['email']
	phone_num = fl.request.form['phone_num']
	pref = fl.request.form['reminder_pref']
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

	# print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'member settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAdminSettings', usrName = usrName, msg = msg))

@app.route('/members/<usrName>/remove', methods = ['POST'])
def removeMember(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	memberName = fl.request.form['member_name']

	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$unset": { 
				"members.{0}".format(memberName) : "",
			}
		}
	)

	# print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'member settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAdminSettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/asana', methods = ['POST'])
def updateAsanaSettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	print fl.request.args
	auth_token = fl.request.form['auth_token']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": { "integrations.asana.auth_token" : auth_token }
		}
	)

	# print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'asana settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/gdrive', methods = ['POST'])
def updateGdriveSettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	client_id = fl.request.form['client_id']
	client_secret = fl.request.form['client_secret']
	scope = fl.request.form['scope']
	redirect_uri = fl.request.form['redirect_uri']
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
	
	# print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'gdrive settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/slack', methods = ['POST'])
def updateSlackSettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	auth_token = fl.request.form['auth_token']
	webhook_url = fl.request.form['webhook_url']
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

	# print fl.request	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'slack settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/integrations/<usrName>/twilio', methods = ['POST'])
def updateTwilioSettings(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	sid = fl.request.form['accnt_sid']
	auth_token = fl.request.form['auth_token']
	twilio_num = fl.request.form['twilio_num']
	res = c_chapters.update(
		{
			"name": usrName
		},
		{ 
			"$set": {
						"integrations.twilio.accnt_sid" : sid,
						"integrations.twilio.auth_token" : auth_token, 
						"integrations.twilio.twilio_num" : twilio_num
					}
		}
	)

	# print res	#DEBUG
	msg = ''
	if res['updatedExisting'] == True:
		msg = 'twilio settings were successfully updated!'
		print msg
	else:
		msg = 'Failed to update settings!'
		print msg

	return fl.redirect(fl.url_for('renderAPISettings', usrName = usrName, msg = msg))

@app.route('/dashboard/<usrName>/createAgenda')
def runCreateAgenda(usrName = None):
	if 'password' not in fl.session:
		#Avoid login bypass
		return fl.redirect(fl.url_for('renderLogin'))
	elif 'code' not in fl.session:
		return fl.redirect(fl.url_for('oauth2callback'))

	chapter = c_chapters.find({ 'name':usrName })[0]

	p = Process(target=au.createAgenda, args=('agenda', 'debug', fl.session['code'], chapter) )
	p.start()
	return fl.redirect(fl.url_for('renderDashboard', usrName = usrName))

@app.route('/dashboard/<usrName>/updateAsana')
def runUpdateAsana(usrName = None):
	if 'password' not in fl.session:
		return fl.redirect(fl.url_for('renderLogin'))

	chapter = c_chapters.find({ 'name':usrName })[0]
	asana_tokens = chapter['integrations']['asana']
	slack_tokens = chapter['integrations']['slack']

	p = Process(target=au.updateAsana, args=('deliverables', 'debug', chapter) )
	p.start()
	return fl.redirect(fl.url_for('renderDashboard', usrName = usrName))

if __name__ == '__main__':
	app.debug = True
	app.logger.addHandler(logging.StreamHandler(sys.stdout))
	app.logger.setLevel(logging.ERROR)
	app.run()

