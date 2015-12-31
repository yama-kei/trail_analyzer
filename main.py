import os
import json

from flask import Flask
from flask import request
from flask import render_template

app = Flask(__name__)
app.config['DEBUG'] = True

from gv_analyzer import *
from trail_analyzer import *
from trail_graph import *

"""
Main handler for Trail Route Analytics application
2015/12/11 Keisuke Yamaguchi
"""
@app.route('/')
@app.route('/welcome')
def welcome():
	"""Return Welcome Page"""
	return render_template('welcome.html')

@app.route('/upload')
def upload(msg = None):
	"""Return Upload Page"""
	return render_template('upload.html',
		msg = msg)

def analyze_exec(f, filename):
	"""Receive GPX file in post message and run analysis"""
	try:
		# parse and analyze GPX log
		rd = RecordData(f)
	except TrailAnalyzerException as e:
		return upload(e.args[0])
	# calculate GV curv for activity
	rd.calculate_gv_curv()
	# dump data for metrics
	(dump_header, dump_data) = rd.dump()
	tg = TrailGraph(rd)
	rendering_data = {
		"profile_data": tg.get_profile_graph(),
		"grade_data_dist": tg.get_grade_dist_graph(),
		"grade_data_time": tg.get_grade_time_graph(),
		"grade_velocity_plot": tg.get_gv_curv_graph(),
		"grade_velocity_vertical_plot": tg.get_vertical_gv_curv_graph(),
		"routeCoordinates": tg.generate_map_data(),
		"dump_data": json.dumps(dump_data),
		"dump_header": json.dumps(dump_header)
	}
	return render_template('simple_dump.html',
		dump=dump_data,
		header=dump_header,
		filename=filename,
		data = rendering_data)

@app.route('/analyze_demo', methods=['GET'])
def analyze_demo():
	"""Demo Analyze using local GPX file"""
	f = open("static/tanzawa_main_ridge.gpx", "r")
	return analyze_exec(f, "DEMO")

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
	"""Receive GPX file in post message and run analysis"""
	if request.method == 'POST':
		f = request.files['gpxfile']
		return analyze_exec(f, f.filename)
	else:
		return upload()

@app.route('/gv_analyze', methods=['POST'])
def gv_analyze():
	"""Receive GD/GV data in json format and executes GV data analysis"""
	if request.json:
		gdv_data = request.get_json()
		gd_data = gdv_data.get("gd_data")
		gv_data = gdv_data.get("gv_data")

		# make sure dict is containing "int":"float"
		gd_data = {int(g):float(v) for g,v in gd_data.iteritems()}
		gv_data = {int(g):float(v) for g,v in gv_data.iteritems()}

		# create GvAnalyzer object
		gva = GvAnalyzer(gd_data)

		# execute gv_curv analysis and return result
		return json.dumps(gva.calculate_gv_curv(gv_data))
	else:
		return json.dumps({})

@app.errorhandler(404)
def page_not_found(e):
	"""Return a custom 404 error."""
	return 'Sorry, nothing at this URL.', 404
