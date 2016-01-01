#!/usr/bin/python
import argparse
import csv
import json
import os
import sys

from trail_analyzer import *

if __name__ == '__main__':
	# load GPX files from given directory and dump json file containing
	# speed v.s. grade data
	parser = argparse.ArgumentParser(description='Trail Analyzer Script')
	parser.add_argument('--input', '-i', type=argparse.FileType('r'), help='GPX log file', required=True)
	parser.add_argument('--output', '-o', type=argparse.FileType('w'), help='Output file (CSV)', default=sys.stdout)
	args = parser.parse_args()

	gv_data = {}
	rd = RecordData(args.input)
	total_dist = rd.gpx.length_2d() / 1000.0
	for interval in range(int(total_dist)):
		if interval+3 > int(total_dist):
			break
		print "calculating interval: 0 to " + str(interval+3) + "km"
		gv_data[interval+3] = rd.calculate_gv_curve(start=0, end=interval+3)

	# remove gv data
	for d, data in gv_data.iteritems():
		del data.get("asc_data")["filtered_gv"]
		del data.get("asc_data")["fitted_gv"]
		del data.get("dsc_data")["filtered_gv"]
		del data.get("dsc_data")["fitted_gv"]

	#DEBUG
	print json.dumps(gv_data, indent=2)

	# only dump interesting figures
	header = ["dist", "vh_max_g", "vh_max", "asc_nth_pg", "asc_gth", "asc_vth", "dsc_nth_pg", "dsc_gth", "dsc_vth"]
	dump_data = []
	for d, data in gv_data.iteritems():
		entry = [d,
			data.get("vh_max_grade"),
			data.get("vh_max_value"),
			data.get("estimated_time_taken_whole"),
			data.get("asc_data")["nth_percentile_grade"],
			data.get("asc_data")["local_min1"],
			data.get("asc_data")["local_min2"],
			data.get("dsc_data")["nth_percentile_grade"],
			data.get("dsc_data")["local_min1"],
			data.get("dsc_data")["local_min2"],
			]
		dump_data.append(entry)

	# output data to CSV file
	writer = csv.writer(args.output)
	writer.writerow(header)
	for d in dump_data:
		writer.writerow(d)
