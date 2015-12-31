import copy
import gpxpy
import json
import math
from trail_analyzer import *

class TrailGraph(object):
	def __init__(self, track_collection):
		self.tc = track_collection
		self.is_record_data = True if type(track_collection) == RecordData else False
		# create copy of track_collection object and reduce points to 100m interval
		self.tc100 = copy.deepcopy(track_collection)
		self.tc100.gpx.reduce_points(None, 100)

	def get_profile_graph(self):
		# profile graph (with 3d speed)
		if not self.is_record_data:
			return self.get_profile_graph_no_speed()
		dist_data = self.tc100.construct_distance_series_data()
		profile_data = [[k/1000, int(p.elevation), (s.dist_3d)/(s.time/60.0)] for (k,(p,s)) in dist_data]
		return json.dumps(profile_data)

	def get_profile_graph_no_speed(self):
		# profile graph (without speed)
		dist_data = self.tc100.construct_distance_series_data()
		profile_data = [[k/1000, int(p.elevation)] for (k,(p,s)) in dist_data]
		return json.dumps(profile_data)

	def get_gv_curv_graph(self):
		def gv_conv(gv, vhg, dsc=False):
			if dsc:
				return json.dumps([[-int(g)+vhg, v] for g,v in gv.iteritems()])
			else:
				return json.dumps([[int(g)+vhg, v] for g,v in gv.iteritems()])
		# GV curv plot
		if not self.is_record_data or not self.tc.gv_analysis:
			return "{}"
		vhg = self.tc.gv_analysis.get("vh_max_grade")
		gv_curv_data = (
			gv_conv(self.tc.gv_analysis.get("asc_data").get("filtered_gv"), vhg),
			gv_conv(self.tc.gv_analysis.get("dsc_data").get("filtered_gv"), vhg, True),
			gv_conv(self.tc.gv_analysis.get("asc_data").get("fitted_gv"), vhg),
			gv_conv(self.tc.gv_analysis.get("dsc_data").get("fitted_gv"), vhg, True)
		)
		return gv_curv_data

	def get_vertical_gv_curv_graph(self):
		def gv_conv(gv, vhg, dsc=False):
			if dsc:
				return json.dumps([[-int(g)+vhg, v] for g,v in gv.iteritems()])
			else:
				return json.dumps([[int(g)+vhg, v] for g,v in gv.iteritems()])
		# GV curv plot
		if not self.is_record_data or not self.tc.gv_analysis:
			return "{}"
		vhg = self.tc.gv_analysis.get("vh_max_grade")
		gv_curv_data = (
			gv_conv(self.tc.gv_analysis.get("asc_data").get("filtered_vertical_gv"), vhg),
			gv_conv(self.tc.gv_analysis.get("dsc_data").get("filtered_vertical_gv"), vhg, True),
			gv_conv(self.tc.gv_analysis.get("asc_data").get("fitted_vertical_gv"), vhg),
			gv_conv(self.tc.gv_analysis.get("dsc_data").get("fitted_vertical_gv"), vhg, True)
		)
		return gv_curv_data

	def get_grade_dist_graph(self, prev_data_json=None):
		grade_dict = self.tc.construct_grade_dictionary()
		grade_list = [k for k in sorted(grade_dict.keys()) if k < 40 and k > -40]
		# grade v.s. 3d distance
		grade_dist_data = [[k, grade_dict[k].total_distance_3d()] for k in grade_list]
		if prev_data_json:
			prev_data = json.loads(prev_data_json)
			prev_data_dict = {d[0]:d[1] for d in prev_data}
			for gd in grade_dist_data:
				gd.append(prev_data_dict.get(gd[0], 0))
		return json.dumps(grade_dist_data)

	def get_grade_time_graph(self, prev_data_json=None):
		grade_dict = self.tc.construct_grade_dictionary()
		grade_list = [k for k in sorted(grade_dict.keys()) if k < 40 and k > -40]
		# grade v.s. time
		grade_time_data = [[k, grade_dict[k].total_time()/60] for k in grade_list]
		if prev_data_json:
			prev_data = json.loads(prev_data_json)
			prev_data_dict = {d[0]:d[1] for d in prev_data}
			for gd in grade_dist_data:
				gd.append(prev_data_dict.get(gd[0], 0))
		return json.dumps(grade_time_data)

	def generate_map_data(self):
		route_coordinates = []
		min_long = 180.0
		max_long = -180.0
		min_lat = 85.0
		max_lat = -85.0
		for point in self.tc100.gpx.walk(only_points=True):
			# save coorinates as a list
			coordinates = (point.latitude, point.longitude)
			route_coordinates.append(coordinates)
			# save min/max coordinates
			if point.longitude < min_long:
				min_long = point.longitude
			if point.longitude > max_long:
				max_long = point.longitude
			if point.latitude < min_lat:
				min_lat = point.latitude
			if point.latitude > max_lat:
				max_lat = point.latitude
		return (route_coordinates, (min_lat, max_lat, min_long, max_long))
