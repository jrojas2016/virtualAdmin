'''
Update Asana
asks for updates on pending tasks

author(s):
	Jorge Rojas
'''

'''Utility Imports'''
import sys

import json
import urllib
import smtplib
# import personalEmailer
from datetime import datetime
from optparse import OptionParser
from utilities import curl, info, taskPending, getAuthToken

receivers = []
receiver_names = []

#Global variables, consider changing during cleanup
slack_members = []
slack_auth_token = []
slack_webhook_url = []
asana_auth_token = []

def getSlackUsers():
	user_list_url = 'https://slack.com/api/users.list?token={0}'.format(slack_auth_token[0])
	slack_users = curl( user_list_url )
	j_slack_users = json.loads( slack_users )
	# print j_slack_users
	for member in j_slack_users['members']:
		slack_members.append( member )

def getAsanaUser( taskStructDict ):

	user_id = taskStructDict[ 'assignee' ][ 'id' ]
	user_url = 'https://app.asana.com/api/1.0/users/{0}'.format(user_id)
	user = curl( user_url, authToken = asana_auth_token[0] )
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
	task_story = curl( story_url, data, asana_auth_token[0] )
	j_task_story = json.loads( task_story )[ 'data' ]
	print 'POST Successful: %s.'%j_task_story[ 'text' ]

	sendSlackReminder( user_name, user_email, task_name, channel )

def sendSlackReminder( userName, userEmail, taskName, channel):
	'''
	Remind the user via Slack mention
	'''

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
				slack_res = curl( slack_webhook_url[0], '{"channel": "#' + channel + '", "username": "ReminderBot", "text":' + slack_reminder_msg + ', "icon_emoji": ":mega:"}')
				print 'Successfully sent reminder to %s.'%userName
			except:
				print 'Failed to send reminder to %s.'%userName

def sendSMSReminder(userPhonNumber, taskName):
	#TODO
	pass

def getAsanaTasks( channel, projectUrl ):
	all_tasks = curl( projectUrl, authToken = asana_auth_token[0] )
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

def updateAsana(projKey, slackChan, slackAuthToken, slackWebhook, asanaAuthToken):
	info('function: updateAsana')
	proj_key = projKey
	channel = slackChan

	projects = {'debug': '54999242167362', 'deliverables': '24426061282606'}
	project_url = 'https://app.asana.com/api/1.0/projects/%s/tasks?opt_fields=due_on,assignee,name,completed'%projects[ proj_key ]
	
	slack_auth_token.append( slackAuthToken )
	slack_webhook_url.append( slackWebhook )
	asana_auth_token.append( getAuthToken( asanaAuthToken ) )
	
	getSlackUsers()
	getAsanaTasks( channel, project_url )

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


