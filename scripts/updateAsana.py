'''
Update Asana
asks for updates on pending tasks

author(s):
	Jorge Rojas
'''

'''Utility Imports'''
import sys
import time
import urllib
import smtplib
import json, base64
# import personalEmailer
from datetime import datetime
from utilities import curl, info
from optparse import OptionParser

receivers = []
receiver_names = []

current_milli_time = lambda: int( round( time.time() * 1000 ) )
slack_auth_token = 'xoxp-4946444601-6490187520-35379050275-6c6aaef4ab'
asana_auth_token = base64.encodestring( '3IOlvKIK.qCLaoBd9o9vQzENWfspMQUl:' ).replace( '\n', '' )

def getSlackUsers():
	user_list_url = 'https://slack.com/api/users.list?token=%s'%slack_auth_token
	# slack_webhook_url = 'https://hooks.slack.com/services/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'
	slack_users = curl( user_list_url )
	j_slack_users = json.loads( slack_users )
	# print j_slack_users
	return j_slack_users['members']

slack_members = getSlackUsers()

def taskPending( taskDueDate ):
	#1 day = 86,400,000 ms
	if taskDueDate - current_milli_time() < 172800000:
		return True
	else:
		return False

def getAsanaUser( taskStructDict ):

	user_id = taskStructDict[ 'assignee' ][ 'id' ]
	user_url = 'https://app.asana.com/api/1.0/users/%s'%user_id
	user = curl( user_url, authToken = asana_auth_token )
	j_user = json.loads( user )

	return j_user[ 'data' ][ 'name' ], j_user[ 'data' ][ 'email' ]

def remindUser( channel, taskStructDict, status ):

	global receivers, receiver_names

	task_id = taskStructDict[ 'id' ]
	task_name = taskStructDict[ 'name' ]
	user_name, user_email = getAsanaUser( taskStructDict )
	receivers.append( str( user_email ) )
	receiver_names.append( str( user_name ) )
	# print 'Name: %s >> Email: %s'%( user_name, user_email )	#DEBUG

	story_url = 'https://app.asana.com/api/1.0/tasks/%s/stories'%task_id
	data = urllib.urlencode( { 'text': 'Please provide an update regarding this task and update the due date accordingly!' } )
	task_story = curl( story_url, data, asana_auth_token )
	j_task_story = json.loads( task_story )[ 'data' ]
	print 'POST Successful: %s.'%j_task_story[ 'text' ]

	sendSlackReminder( user_name, user_email, task_name, channel )

def sendSlackReminder( userName, userEmail, taskName, channel):
	'''
	Remind the user via Slack mention
	'''
	slack_webhook_url = 'https://hooks.slack.com/services/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'

	for cur_user in slack_members:
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
				print 'Successfully sent reminder to %s.'%userName
			except:
				print 'Failed to send reminder to %s.'%userName

def sendSMSReminder(userPhonNumber, taskName):
	#TODO
	pass

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
		cur_task_name = cur_task[ 'name' ]
		cur_task_due = cur_task['due_on']
		cur_task_assignee = cur_task['assignee']
		cur_task_completed = cur_task['completed']

		if not cur_task_completed and cur_task_assignee is not None and cur_task_due is not None:
			#Converting date to milliseconds since epoch
			epoch = datetime.utcfromtimestamp( 0 )
			cur_task_due = datetime.strptime( cur_task_due, '%Y-%m-%d' )
			delta_t = cur_task_due - epoch
			cur_task_millis_due = delta_t.total_seconds() * 1000.0
			# print cur_task_millis_due #Debugging only

			if taskPending( cur_task_millis_due ):
				remindUser( channel, cur_task, status = 'pending' )

def updateAsana(projKey, slackChan):
	info('function: updateAsana')
	proj_key = projKey
	channel = slackChan

	projects = {'debug': '54999242167362', 'deliverables': '24426061282606'}
	project_url = 'https://app.asana.com/api/1.0/projects/%s/tasks?opt_fields=due_on,assignee,name,completed'%projects[ proj_key ]

	getAsanaTasks( asana_auth_token, channel, project_url )

if __name__ == '__main__':
	parser = OptionParser()

	parser.add_option( "--projKey",
					dest="projKey",
					default = "debug",
					help="Asana Project Key: debug or deliverables. Default value is debug")

	parser.add_option( "--chan",
					dest="chan",
					default = "debug",
					help="Slack channel name. Do not include the pound (#) sign. Default value is debug")

	(options, args) = parser.parse_args()
	proj_key = options.projKey
	chan = options.chan
	updateAsana(proj_key, chan)


