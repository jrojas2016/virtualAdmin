'''
Update Asana
asks for updates on pending tasks

author(s):
	Jorge Rojas
'''
import time
import smtplib
import json, base64
import urllib, urllib2
# import personalEmailer
from datetime import datetime
from optparse import OptionParser

receivers = []
receiver_names = []

current_milli_time = lambda: int( round( time.time() * 1000 ) )
slack_auth_token = 'xoxp-4946444601-6490187520-12150502211-608959dc10'
asana_auth_token = base64.encodestring( '3IOlvKIK.qCLaoBd9o9vQzENWfspMQUl:' ).replace( '\n', '' )

def taskPending( taskDueDate ):
	#3 days = 259200000 ms
	if taskDueDate - current_milli_time() < 259200000:
		return True
	elif taskDueDate - current_milli_time() > 259200000:
		return False

def taskOverdue( taskDueDate ):
	if taskDueDate < current_milli_time():
		return True
	else:
		return False

def getUser( taskStructDict ):

	user_id = taskStructDict[ 'assignee' ][ 'id' ]
	user_name = taskStructDict[ 'assignee' ][ 'name' ]

	user_url = 'https://app.asana.com/api/1.0/users/%s?opt_pretty'%user_id

	user = curl( user_url, authToken = asana_auth_token )
	j_user = json.loads( user )

	return j_user[ 'data' ][ 'name' ], j_user[ 'data' ][ 'email' ]

def curl( url, data = None, authToken = None ):

	if data is not None:
		req = urllib2.Request( url, data )
	else:
		req = urllib2.Request( url )

	if authToken is not None:
		req.add_header( 'Authorization', 'Basic %s'%authToken )

	response = urllib2.urlopen( req )
	res = response.read()
	return res

def remindUser( channel, taskStructDict, status ):

	global receivers, receiver_names

	task_id = taskStructDict[ 'id' ]
	task_name = taskStructDict[ 'name' ]
	user_name, user_email = getUser( taskStructDict )
	receivers.append( str( user_email ) )
	receiver_names.append( str( user_name ) )
	# print 'Name: %s >> Email: %s'%( user_name, user_email )

	story_url = 'https://app.asana.com/api/1.0/tasks/%s/stories'%task_id
	data = urllib.urlencode( { 'text': 'Please provide an update regarding this task and update the due date accordingly!' } )
	task_story = curl( story_url, data, asana_auth_token )
	j_task_story = json.loads( task_story )[ 'data' ]
	print 'POST Successful: %s'%j_task_story[ 'text' ]

	sendSlackReminder( user_name, user_email, task_name, channel )
	# personalEmailer.sendEmailReminder( user_name, user_email, task_name, status )

def sendSlackReminder( userName, userEmail, taskName, channel):
	'''
	Remind the user via Slack mention
	'''

	user_list_url = 'https://slack.com/api/users.list?token=%s'%slack_auth_token
	slack_webhook_url = 'https://hooks.slack.com/services/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'

	slack_users = curl( user_list_url )
	j_slack_users = json.loads( slack_users )

	for cur_user in j_slack_users['members']:
		'''
		cur_user -> dictionary with user data
		'''
		cur_user_id = cur_user['id']	#Used for the mention
		cur_user_name = cur_user['name']
		cur_user_email = cur_user['profile']['email']

		if cur_user_email == userEmail:
			slack_reminder_msg = '"Hey <@%s|%s>, this Asana task is pending: %s"'%( cur_user_id, cur_user_name, taskName )
			try:
				slack_res = curl( slack_webhook_url, '{"channel": "#' + channel + '", "username": "ReminderBot", "text":' + slack_reminder_msg + ', "icon_emoji": ":mega:"}')
				print slack_res
				print 'Successfully sent reminder to %s'%userName
			except:
				print 'Failed to send reminder to %s'%userName


def getAsanaTasks( authToken, channel, projectUrl ):
	all_tasks = curl( projectUrl, authToken = authToken )
	j_all_tasks = json.loads( all_tasks )
	
	for cur_task in j_all_tasks[ 'data' ]:
		'''
		Current Task >> dict
		keys:
			task id, name
		notes:
			does not contain all task attributes;
			need to curl the task id first
		'''
		#Filter out labels or sections
		if not cur_task[ 'name' ].endswith( ':' ):
			cur_task_name = cur_task[ 'name' ]
			cur_task_id = cur_task[ 'id' ]

			task_url = 'https://app.asana.com/api/1.0/tasks/%s'%cur_task_id
			
			cur_task_struct = curl( task_url, authToken = authToken )
			j_cur_task_struct = json.loads( cur_task_struct )
			j_cur_task = j_cur_task_struct[ 'data' ]

			if not j_cur_task[ 'completed' ] and j_cur_task[ 'due_on' ] is not None and j_cur_task[ 'assignee' ] is not None:
				#Converting date to milliseconds since epoch
				epoch = datetime.utcfromtimestamp( 0 )
				cur_task_due = datetime.strptime( j_cur_task[ 'due_on' ], '%Y-%m-%d' )
				delta_t = cur_task_due - epoch
				cur_task_millis_due = delta_t.total_seconds() * 1000.0
				# print cur_task_millis_due #Debugging only

				if taskPending( cur_task_millis_due ) or taskOverdue( cur_task_millis_due ):
					remindUser( channel, j_cur_task, status = 'pending' )

def updateAsana(projKey, chan):

	proj_key = projKey
	channel = chan

	projects = {'debug': '54999242167362', 'deliverables': '24426061282606'}
	project_url = 'https://app.asana.com/api/1.0/projects/%s/tasks'%projects[ proj_key ]

	getAsanaTasks( asana_auth_token, channel, project_url )

if __name__ == '__main__':
	updateAsana()


