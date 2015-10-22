LUL Virtual Administrator

Description:
	Semi-automted administrative system for
	chapters to use. Includes a task reminder, 
	agenda creator, and personalized email sender.

Requirements:
	- Python 2.7: https://www.python.org/download/releases/2.7/

	- PyDrive: https://pypi.python.org/pypi/PyDrive
		1. Instructions: https://github.com/jay0lee/GAM/wiki/Creating-client_secrets.json-and-oauth2service.json

		2. Google API Console: https://console.developers.google.com/

	- python-docx: https://python-docx.readthedocs.org/en/latest/

	- All members must have an Asana account

	- All members should have a team domain in Slack with the following integrations
		1. Asana
		2. Slack API Tester
			a. Allows script to read data from the slack team domain
		3. Incoming WebHooks 
			a. Allows script to post on a particular channel through a bot account

Setup:
	- TBI
