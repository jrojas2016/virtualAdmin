'''
Slackbot Reminders:
Remind LULAASIT group the given message

author(s):
	Jorge Rojas
'''
import json
import urllib, urllib2
from optparse import OptionParser

def sendReminder( chan, msg ):
	url = 'https://lulaasit.slack.com/services/hooks/slackbot?token=gFMRIyVYBBAM8iv6rjgM0PBX&channel=%23' + chan
	req = urllib2.Request(url, msg)
	response = urllib2.urlopen(req)
	res = response.read()
	print res

def main():

	parser = OptionParser()

	parser.add_option( "--chan",
					dest="channel",
					default="general",
					help="Slack channel to post message")

	parser.add_option( "--msg",
					dest="msg",
					default = "Asana has been updated. Please provide an update on the tasks assigned to you!",
					help="Reminder to send to slack" )

	(options, args) = parser.parse_args()

	msg = options.msg
	chan = options.channel

	sendReminder( chan, msg )

if __name__ == '__main__':
	main()