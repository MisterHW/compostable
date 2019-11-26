#!python 3

# compose.py transforms table-formatted data.
# 
# input header end sequence: ignored
# input header end sequence: last_headerline_pattern = re.compile('--Nr\.--.*')
# input value separator    : '|' (with or without ' ' or '\t' padding)
# input decimal separator  : ',' or '.' (non-numeric values are skipped)
#
# output header start sequence: output_header_first_line = '# [header]\n'
# output header end sequence  : output_data_first_line = '# [data]\n'
# output value separator      : output_cell_separator = '\t'
# output decimal separator    : '.'
#
# compose.py is used with a user-specified definition for the new columns.
# Example caller script:
# 
#	import compose # compose.py in the same folder as this script
#	# output column definitions
#	#
#	# use (X, "description") to copy source column X (count starts at 1),
#	# use ("{X}*0.123 + {Y}*4", "description") to specify a function 
#	#	applied per line to items of columns {X} and {Y}.
#	# note: other functions are also supported, like math.sin() 
#	#	and in-built functions (see compose.py code).
#	columns = [
#		("{3}-0.5", "T_case k-type TC"),
#		("RTD({11}/0.001, 1000)", "CH8 HS V(PT1000)@0.001A"),
#		( 5, "CH2 V_DS"),
#		]
#	# call compose.py
#	success = compose.create_from_cheleiha_static(input_fn, output_fn, columns)
#

import re
import os
import math
		
##################################################################
		
# built-in formula for Pt resistor thermometer devices
def RTD(R, R0):
	# quadratic resistance approximation over 0°C < T < 850°C,
	# for Pt RTD with alpha = 0.00385,
	# see https://en.wikipedia.org/wiki/Resistance_thermometer
	# Input: resistance in Ohm (e.g. RTD(R, 1000) for a PT1000 element; 
	# returns: Temperature in °C.
	A = 3.9083E-3 # [1/°C]
	B = -5.775E-7 # [1/°C²]
	r = float(R)/float(R0)
	T = (-A + math.sqrt(A**2 - 4 * B * (1 - r))) / (2 * B)
	return T

##################################################################	


def format_number(s):
	res = None 
	try:
		s_decp = s.replace(',', '.')
		tmp = float(s_decp)
		res = s_decp
	except ValueError:
		res = s
	return res
	
	
def calculate_expr(fstr, values, default):
	for idx, val in enumerate(values):
		fstr = fstr.replace("{%d}" % (idx + 1), format_number(val))

	try:
		res = str(eval(fstr))
	except:
		res = default
		
	return res
	

def create_from_cheleiha_static(input_filename, output_filename, columns_config):
	# input format-specific definitions
	
	last_headerline_pattern = re.compile('--Nr\.--.*')
	input_cell_separator = '|'
	
	# output format definitions
	
	output_cell_separator = '\t'
	output_header_first_line = '# [header]'
	output_headerline_prefix = '# '
	output_headerline_suffix = ''
	output_data_first_line = '# [data]'

	# file handling and checks
	
	inp = None 
	try:
		# attempt to open input file first. If this fails,
		# there is no point in creating output.
		inp = open(input_filename, 'r') 
	except Exception as e:
		print(e)
		return False 

	outp = None
	try:
		# attempt to create output file. If that fails,
		# report error and return.
		outp = open(output_filename, 'w+')
	except Exception as e:
		print(e)
		inp.close()
		return False 

	# write new header
	
	if output_header_first_line != '':
		outp.write('%s\n' % (output_header_first_line))

	outp.write('%ssource : "%s"%s\n' % (output_headerline_prefix, os.path.basename(input_filename), output_headerline_suffix))
	for idx, col_cfg in enumerate(columns_config):
		if isinstance(col_cfg[0], int):
			outp.write('%scolumn %d : original column %s (%s)%s\n' % (output_headerline_prefix, idx + 1, col_cfg[0], col_cfg[1], output_headerline_suffix))
		else:
			outp.write('%scolumn %d : expression %s (%s)%s\n' % (output_headerline_prefix, idx + 1, repr(col_cfg[0]), col_cfg[1], output_headerline_suffix))
	
	# import data, process and write output
	
	if output_data_first_line != '':
		outp.write('%s\n' % (output_data_first_line))
		
	input_is_header = True
	
	for line in inp:
		if input_is_header:
			if last_headerline_pattern.match(line):
				input_is_header = False
				continue
		else:
			inp_cells  = [c.strip() for c in line.split(input_cell_separator)]
			outp_cells = ['NaN' for i in range(len(columns_config))]
			for idx, col_cfg in enumerate(columns_config):
				try:
					if isinstance(col_cfg[0], int):
						outp_cells[idx] = format_number(inp_cells[col_cfg[0] - 1])
					elif isinstance(col_cfg[0], str):
						outp_cells[idx] = calculate_expr(col_cfg[0], inp_cells, 'NaN')
					else:
						pass 
				except Exception as e:
					print(e)
					# default is 'NaN'
					pass
			outp.write('%s\n' % (output_cell_separator.join(outp_cells)))
	inp.close()
	outp.close()
	return True 