'''
Personalized Emailer:
Send personalized emails to a list of receivers

Author(s): 
	Jorge Rojas

Comments:
	- Look for receiverList.xlsx to populate 
	receiver name (Column A), and receiver email (Column B)

	- Look for emailWriter.txt to change the subject and body
	of the email to send. 

	- Do not remove the "Subject:" label

Revisions:
	2.0 - Generalized script to read 
	email content from emailWriter.txt file

	1.0 - Added support for arbitrary email subject line
'''
import smtplib
import openpyxl
from optparse import OptionParser

#Dictionary of receiver names and emails
receivers = {}

#Ensure name_col allings with name column in excel sheet
name_col = 'A'

#Ensure email_col alligns with email column in excel sheet
email_col = 'B'

#Complete excel worksheet
wb = openpyxl.load_workbook(filename = 'receiverList.xlsx')

#Ensure receiver_sheet has the same name as the sheet in the excel file
receiver_sheet = wb['Sheet 1'] 

def sendPersonalEmail( receivers ):
	'''
	Send personalized email to each email address in receiver:
	receivers - dictionary -- name/email key/value pair to receive email 
	'''
	sender = raw_input("Account email: ")
	sender_password = raw_input("Type password for %s email account: "%sender)
	try:
		server = smtplib.SMTP("smtp.gmail.com",587)
		server.starttls()
		server.login(sender, sender_password)
	except:
		print 'Unable to log in as %s, please check your login credentials'%sender
		exit(0)

	for cur_receiver in receivers.keys():
		isBody = False
		new_line_cnt = 0
		msg = [ 'From: %s'%sender, 'To: %s'%receivers[cur_receiver] ]
		emailFile = open('emailWriter.txt', 'r')

		for cur_line in emailFile.readlines():
			if cur_line.find('{receiverName}') >= 0:
				line = cur_line.replace('{receiverName}', '{0}')
				msg.append( line.format(cur_receiver) )
			else:
				if cur_line == '\n':
					line = cur_line.replace('\n', '')
					msg.append( line )
				else:
					msg.append( cur_line )
				
		message = '\r\n'.join( msg )

		try:
			server.sendmail( sender, [receivers[cur_receiver]], message )
			print 'Email sent successfully to %s'%cur_receiver
		except:
			print 'Email failed to send to %s!'%cur_receiver

	server.quit()

def main():
	parser = OptionParser()

	parser.add_option( "-d",
					dest="debugReceiver",
					default = None,
					help="Email address for debug")

	(options, args) = parser.parse_args()

	if options.debugReceiver == None:
		receiver_cnt = 1
		while receiver_sheet[name_col + '%s'%receiver_cnt].value is not None:
			if receiver_sheet[email_col + '%s'%receiver_cnt].value is not None:
				# print receiver_sheet[name_col + '%s'%receiver_cnt].value #DEBUG
				receivers[receiver_sheet[name_col + '%s'%receiver_cnt].value] = receiver_sheet[email_col + '%s'%receiver_cnt].value
			receiver_cnt += 1
	else:
		if options.debugReceiver.find('@') == -1:
			print 'Please provide an valid email address in the -d argument e.g. me@domain.com'
			exit(0)
		else:
			receivers["MailBot"] = options.debugReceiver

	sendPersonalEmail( receivers )

if __name__ == '__main__':
	main()

