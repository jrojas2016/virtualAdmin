import openpyxl
import datetime
from optparse import OptionParser

def main():

	columns = { 'task_id': 0, 'created_at': 1, 'completed_at': 2, 
						'last_modified': 3, 'name': 4, 'assignee': 5, 
						'due_date': 6, 'tags': 7, 'Notes': 8, 'projects': 9}

	filter_options = columns.keys()

	parser = OptionParser()

	parser.add_option( "--file",
					dest="asanaFile",
					default = None,
					help="Exported CSV file from Asana" )

	parser.add_option( "--filter",
					dest = "filterArg",
					default = None,
					help = "Column to filter. Choose from below: \n\n %s"%filter_options )

	(options, args) = parser.parse_args()

	if options.asanaFile == None:
		print 'Must provide a --file argument!'
		exit()

	if not options.asanaFile.endswith( '.xlsx' ):
		print 'Must provide a .xlsx file'
		exit()

	if options.filterArg == None:
		print 'Must provide a --filter argument!'
		exit()

	if options.filterArg not in columns.keys():
		print 'Filter argument not supported! Please choose from list below: \n\n %s'%filter_options
		exit()

	asanaFile = options.asanaFile
	# filterArg = options.filterArg
	arg_to_parse = columns[ options.filterArg ]

	try:
		# tasks_file = open( asanaFile, 'rb' )
		tasks_sheet = openpyxl.load_workbook( asanaFile ).get_active_sheet()
	except IOError:
		print 'There was an error openning file: %s'%asanaFile
		exit()

	for cur_row in tasks_sheet.iter_rows():
		for cur_cell_index, cur_cell in enumerate( cur_row ):
			if cur_cell_index == arg_to_parse:
				if cur_cell.value == None:
					print cur_row[ columns[ 'assignee' ] ].value

if __name__ == '__main__':
	main()


