#!python3

# active metadata file / conversion script to create processable data files from "CheLeiHa Static" format
# copy and modify this file 
#
# input  filename convention: same name as this file, different extension (.txt)
# output filename convention: prefix 'data_' + input filename
# output columns: specified below as a list of tuples. 
import os
try:
	import compose
except ImportError:
	print("error: missing 'compose.py' - this file should have been supplied along with this script (same folder).\n"+\
	"As a custom tool it is not provided as a package, but you might be able to find a copy somewhere on your drive.")
	exit(1)

input_fn = os.path.splitext(__file__)[0] + '.txt'
fn_head, fn_tail = os.path.split(input_fn)
output_fn = fn_head + '\\data_' + fn_tail
print("output: %s" % output_fn)

# output column definitions
#
# use (X, "description") to copy source column X (count starts at 1),
# use ("{X}*0.123 + {Y}*4", "description") to specify a function 
#	applied per line to items of columns {X} and {Y}.
# note: other functions are also supported, like math.sin() 
#	and in-built functions (see compose.py code).

columns = [
	("average {3}", "NTC drive current (A)"),
	("average {4} when {i} % 2 == 0", "IGBT2 sense (V)"),
	("average {4} when {i} % 2 == 1", "D2 sense (V)"),
	]

compose.create_from_cheleiha_static(input_fn, output_fn, columns, block_length = 64)
# os.startfile(output_fn, 'open')