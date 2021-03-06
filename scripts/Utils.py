'''
Utilities:
	Utility functions for 
	Virtual Admin application

author(s):
	Jorge Rojas
'''

import os
import time
import uuid
import base64
import urllib2
import hashlib
import smtplib
from datetime import datetime

dateNow = lambda: datetime.utcnow()
timeNow = lambda: datetime.fromtimestamp( time.time() )
currentMilliTime = lambda: int( round( time.time() * 1000 ) )

generateAppKey = lambda: str(uuid.uuid4())
hashPassword = lambda psswrd: hashlib.sha512( psswrd ).hexdigest()
encodeAuthToken = lambda token: base64.encodestring( token ).replace( '\n', '' )


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

def getDeltaTimeMilli( dueDate ):
	epoch = datetime.utcfromtimestamp( 0 )
	dueTime = datetime.strptime( dueDate, '%Y-%m-%d' )
	delta_t = dueTime - epoch
	delta_time_milli = delta_t.total_seconds() * 1000.0

	return delta_time_milli

def info(title):
    print title
    if hasattr(os, 'getppid'):  # only available on Unix
        print 'parent process:', os.getppid()
    print 'process id:', os.getpid()

def sendEmailConfirmation(email, usrName, hostUrl):
	#Implement email confirmation after sign-up
	sender = 'va.test2016@gmail.com'
	passwrd = 'xxxxxxxx'
	server = smtplib.SMTP("smtp.gmail.com",587)
	server.starttls()
	server.login(sender, passwrd)
	msg = [ 
		'From: {0}'.format(sender), 
		'To: {0}'.format(email),
		'Subject: Virtual Admin - Email Confirmation',
		'',
		'Thanks for joining Virtual Admin. To confirm your email please click on the link below:',
		'',
		'{0}/confirm/{1}'.format(hostUrl, usrName),
		'',
		'Sincerely,',
		'Virtual Admin Team'
	]

	message = '\r\n'.join( msg )

	try:
		server.sendmail( sender, email, message )
		print 'Email sent successfully to {0}'.format(email)
	except:
		print 'Email failed to send to {0}!'.format(email)

	server.quit()

def taskPending( taskDueDate ):
	#1 day = 86,400,000 ms
	if taskDueDate - currentMilliTime() < 172800000:
		return True
	else:
		return False

if __name__ == '__main__':
	pass

