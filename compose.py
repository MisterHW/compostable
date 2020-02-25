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
	
	
def calculate_expr(fstr, values, default, symbols = {}):	
	for idx, val in enumerate(values):
		fstr = fstr.replace("{%d}" % (idx + 1), format_number(val))
	for key, val in symbols.items():
		fstr = fstr.replace(key, val)
	try:
		res = str(eval(fstr))
	except:
		res = default
		
	return res
	

class ExprProcessingRule():
	def __init__(self, analytical_expr, merge_operator = None, boolean_expr = None):
		self.merge_operator  = merge_operator
		self.analytical_expr = analytical_expr
		self.boolean_expr    = boolean_expr if (boolean_expr != None) else 'True'
		
	
class IterativeTableProcessor():
	def __init__(self, column_configurations, block_length):
		self.block_length = block_length
		self.line_counter = 0
		self.relative_counter = 0
		self.column_configurations = column_configurations
		# regex pattern for command parsing
		# optional group0 = block processing operator | None 
		# group1 = arithmetic expression with placeholders | ''
		# optional group2 = parent group for "when" keyword and match4 | None
		# optional group3 = boolean expression | None 
		self.command_pattern = re.compile('^\s*(min|max|stddev|average|median|once|list|sum)?\s*(.*?)(?=when\s*|$)(when\s*(\S.*))?')
		# examples:
		# "{4}"
		#	1:{4}
		#	"	sum {1}"
		#	0:sum
		#	1:{1}
		# "1.0 when True"
		#	1:1.0
		#	2:when True
		#	3:True
		# "average {12}*12/math.PI when (i%1==0) or i < 8"
		#	0:average
		#	1:{12}*12/math.PI 
		#	2:when (i%1==0) or i < 8
		#	3:(i%1==0) or i < 8
		
		# parse column configuration
		self.column_rules = []
		for idx, col_cfg in enumerate(self.column_configurations):
			if isinstance(col_cfg[0], int):
				self.column_rules.append(ExprProcessingRule(analytical_expr = "{%d}" % col_cfg[0]))
			else:
				m = self.command_pattern.match(str(col_cfg[0]))
				g = m.groups()	
				self.column_rules.append(ExprProcessingRule(analytical_expr = g[1], merge_operator = g[0], boolean_expr = g[3]))				
		self._clear_output_cells()
			
	def _clear_output_cells(self):
		self.outp_cells = [[] for i in range(len(self.column_configurations))]
		self.relative_counter = 0
		
	def merged_by_rules(self):
		if (self.relative_counter == 0) or (sum(map(len, self.outp_cells)) == 0):
			return None
		else:	
			res = ['NaN' for i in range(len(self.column_rules))]	
			for idx, rule in enumerate(self.column_rules):
				try:
					# operators listed in self.command_pattern
					if (rule.merge_operator == None) or (rule.merge_operator == 'once'):
						# select first item (default)
						if len(self.outp_cells[idx]) > 0:
							res[idx] = str(self.outp_cells[idx][0])
							if (self.block_length > 1) and not (rule.merge_operator == 'once'):
								print("Warning: column %d has no explicit selection operator and block length is > 1.")
								print("Per block, only the first item from each column will be output. Use 'once' if it's deliberate.")
					if rule.merge_operator == 'min':
						# TODO
						continue 
					elif rule.merge_operator == 'max':
						# TODO
						continue
					elif rule.merge_operator == 'stddev':
						# TODO
						continue
					elif rule.merge_operator == 'average':
						if len(self.outp_cells[idx]) > 0:
							res[idx] = str(sum(map(float, self.outp_cells[idx])) / len(self.outp_cells[idx]))
					elif rule.merge_operator == 'median':
						# TODO
						continue
					elif rule.merge_operator == 'list':
						res[idx] = "[%s]" % "; ".join(self.outp_cells[idx])
					elif rule.merge_operator == 'sum':
						res[idx] = str(sum(map(float, self.outp_cells[idx])))
				except Exception as e:
					print("Error in merged_by_rules():")
					print(e)
					pass
					
		return res

	def process_line(self, line_cells):
		self.line_counter = self.line_counter + 1
		self.relative_counter = self.relative_counter + 1	
		indices = {"{i}":str(self.relative_counter - 1), "{I}":str(self.line_counter - 1)}
		for idx, rule in enumerate(self.column_rules):
			try:
				# conditionally (rule.boolean_expr) accumulate values and apply rule.merge_operator.
				# using calculate_expr() allows "1", "True" and functions, e.g. '{1}/{2} < 4.5' 
				# to be evaluated as powerful conditional selections.
				if calculate_expr("("+rule.boolean_expr + ") == True", line_cells, "False", indices) == "True":
					self.outp_cells[idx].append(calculate_expr(rule.analytical_expr, line_cells, 'NaN', indices))
			except Exception as e:
				print("Error in process_line():")
				print(e)
				# default is 'NaN'
				pass
				
		if self.relative_counter >= self.block_length:
			res = self.merged_by_rules()
			self._clear_output_cells()
			return res
		else:
			return None
		
	def process_eof(self):
		return self.merged_by_rules()
		
			
def create_from_cheleiha_static(input_filename, output_filename, columns_config, block_length = 1):
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
	if block_length > 1:
		outp.write('%sline block length : %d%s\n' % (output_headerline_prefix, block_length, output_headerline_suffix))
		
	for idx, col_cfg in enumerate(columns_config):
		if isinstance(col_cfg[0], int):
			outp.write('%scolumn %d : original column %s (%s)%s\n' % (output_headerline_prefix, idx + 1,  col_cfg[1], col_cfg[0], output_headerline_suffix))
		else:
			outp.write('%scolumn %d : (%s) - expression %s%s\n' % (output_headerline_prefix, idx + 1, col_cfg[1], repr(col_cfg[0]), output_headerline_suffix))
		
	# import data, process and write output
	
	ITP = IterativeTableProcessor(columns_config, block_length)
	
	if output_data_first_line != '':
		outp.write('%s\n' % (output_data_first_line))
		
	input_is_header = True
	data_line_index = 0
	
	for line in inp:
		if line.strip() == '':
			continue
		if input_is_header:
			if last_headerline_pattern.match(line):
				input_is_header = False
				data_line_index = 0
				continue
		else:
			inp_cells  = [c.strip() for c in line.split(input_cell_separator)]
			outp_cells = ITP.process_line(inp_cells)
			if outp_cells != None:
				outp.write('%s\n' % (output_cell_separator.join(outp_cells)))
			
	outp_cells = ITP.process_eof()
	if outp_cells != None:
		outp.write('%s\n' % (output_cell_separator.join(outp_cells)))
			
	inp.close()
	outp.close()
	return True 



