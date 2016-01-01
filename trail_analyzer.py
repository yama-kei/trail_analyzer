import json
import gpxpy

from gv_analyzer import *

"""
Trail Route Analyzer
2015/5/15 Keisuke Yamaguchi
- 
Analyzes GPS log data for mountaineering activities where variation in grade (%) would
affect speed of the activity. Supported type of activities are:
	- Trail Running
	- Speed Hiking
	- Hiking
"""

# base class for Trail Analyzer Exception
class TrailAnalyzerException(Exception):
	pass

class TrailAnalyzerNoTimeDataException(TrailAnalyzerException):
	pass

class TrailAnalyzerNoGpxFileException(TrailAnalyzerException):
	pass

def dump_time(seconds):
	# dumps time (in seconds) in HH:MM:SS syntax
	m, s = divmod(seconds, 60)
	h, m = divmod(m, 60)
	return "%d:%02d:%02d" % (h, m, s)

class TrackSegment(object):
	# segment class, holoing infomration about point A to B
	def __init__(self, previous, current):
		self.dist = current.distance_2d(previous)
		self.dist_3d = current.distance_3d(previous)
		self.time = current.time_difference(previous)
		if current.elevation and previous.elevation:
			self.alt = current.elevation - previous.elevation
			self.grade = previous.elevation_angle(current)
		else:
			self.alt = None
			self.grade = None

	def is_long_time_gap(self):
		# if the time gap is more than 10min
		if self.time:
			return self.time > 10*60

	def is_stop(self):
		# if the speed is less than 0.2km/h (=3.33m/min)
		if self.time:
			return (self.dist_3d/self.time) < (3.33/60)

	def is_jump(self):
		# if the 3d speed is more than 24km/h (=400m/min)
		if self.time:
			return (self.dist_3d/self.time) > (400/60)

	def is_climb(self, climb_threshold=5):
		# if grade > threshold
		if self.grade:
			return self.grade > climb_threshold

	def is_descent(self, climb_threshold=5):
		# if grade < threshold
		if self.grade:
			return self.grade < -climb_threshold

	def is_valid_segment(self):
		# is this segment valid for calculation purposes?
		if not self.time:
			return True
		else:
			if not self.grade:
				return False
			else:
				return not (self.is_long_time_gap() or self.is_stop() or self.is_jump())


class TrackList(list):
	"""
	Extends list to store track data.
	"""
	def __init__(self, segments=[], has_time=True):
		self.has_time = has_time
		for s in segments:
			self.append(s)

	def calc_total(self, attr):
		# calculate total value of a given attribute
		total = 0.0
		for s in self:
			total += getattr(s, attr)
		return total

	def total_distance(self):
		return self.calc_total("dist")
	
	def total_distance_3d(self):
		return self.calc_total("dist_3d")

	def total_altitude_gain(self):
		return self.calc_total("alt")

	def total_time(self):
		if self.has_time:
			return self.calc_total("time")

	def avg_horizontal_speed(self):
		if self.has_time:
			return (self.calc_total("dist")/1000.0) / (self.calc_total("time")/60.0/60.0)

	def avg_vertical_speed(self):
		if self.has_time:
			return (60.06*self.calc_total("alt")) / (self.calc_total("time"))

	def h_speed_list(self):
		if self.has_time:
			return [(getattr(o, "dist")/1000.0)/(getattr(o, "time")/60.0/60.0) for o in self]

	def v_speed_list(self):
		if self.has_time:
			return [(60.06*getattr(o, "alt")/(getattr(o, "time"))) for o in self]

	def append(self, s):
		if not self.has_time:
			# route data without time
			list.append(self, s)
		elif s.is_valid_segment():
			# filter out spike/stop/time gap
			list.append(self, s)
		else:
			#print "ignored segment. time: " + str(s.time) + " dist(3d): " + str(s.dist_3d) + " speed: " + str((s.dist_3d/1000.0)/(s.time/3600.0))
			pass


class TrackCollection(object):
	"""
	Class that load GPX file and keep TrackList of the route
	"""
	track_data = None
	has_time = True
	stopped_time = 0.0
	def __init__(self, input=None, interval=10):
		self.gpx = None
		self.interval = interval
		if not self.track_data:
			self.track_data = TrackList([])
		if input:
			self.gpx = self.load(input)
			self.track_data += self.construct_segment_data(self.gpx)

	def load(self, input):
		try:
			gpx = gpxpy.parse(input)
		except:
			raise TrailAnalyzerException("GPX parse error.")
		# reduce point interval
		gpx.reduce_points(None, self.interval)
		gpx.smooth()
		return gpx

	def add_data(self, input):
		gpx = self.load(input)
		if not self.gpx:
			self.gpx = gpx
		self.track_data += self.construct_segment_data(gpx)

	def construct_segment_data(self, gpx, start=None, end=None):
		# construct segment data by going through gpx track data
		# to be removed from TrackCollection
		track_data = TrackList([])
		previous_point = None
		total_distance = 0
		
		# convert start/end from km to m
		start = start * 1000 if start else None
		end = end * 1000 if end else None
		
		for point in gpx.walk(only_points=True):
			if previous_point:
				track = TrackSegment(previous_point, point)
				total_distance += track.dist
				#print "total distance: " + str(total_distance)
				if start and total_distance < start:
					# before start dist -> skip
					pass
				if end and total_distance > end:
					# passed end dist -> end loop
					break
				track_data.append(track)
				if self.has_time:
					# save total stopped time
					if track.is_stop():
						self.stopped_time += track.time
			previous_point = point
		return track_data

	def construct_grade_dictionary(self, track_data=None):
		grade_dict = {}
		track_data = self.track_data if track_data is None else track_data
		for track in track_data:
			g = int(round(track.grade))
			if g in grade_dict.keys():
				grade_dict[g].append(track)
			else:
				grade_dict[g] = TrackList([track])
		return grade_dict

	def construct_distance_series_data(self):
		distance_series = []
		distance = 0
		previous_point = None
		for point in self.gpx.walk(only_points=True):
			if previous_point:
				track = TrackSegment(previous_point, point)
				if track.is_valid_segment():
					distance += track.dist
					distance_series.append((distance, (point, track)))
			previous_point = point
		return distance_series

	def dump(self):
		track_data_dict = {}
		track_data_header = {
			"length_2d":"Total Distance(km)",
			"length_3d":"Total Moving Distance(km)",
			"ascent":"Total Ascent(m)",
			"descent":"Total Descent(m)",
			"moving_distance":"Moving Distance(km)",
			#"estimated_stopped_time":"Estimated Stopped Time(min)",
			#"estimated_total_time":"Estimated Total Time(min)",
		}
		# overall stat
		track_data_dict["length_2d"] = self.gpx.length_2d() / 1000.0
		track_data_dict["length_3d"] = self.gpx.length_3d() /1000.0
		uphill, downhill = self.gpx.get_uphill_downhill()
		track_data_dict["ascent"] = uphill
		track_data_dict["descent"] = -downhill
		return (track_data_header, track_data_dict)

	"""
	def estimate_time(self):
		# take GV curve parameters to estimate time taken
		gd = self.construct_grade_dictionary()
		# pass 3D distance
		gd_hd_dict = {g:obj.total_distance() for g,obj in gd.iteritems()}
		t = self.gv_data.estimate_time(gd_hd_dict)
		return t
	"""


class RecordData(TrackCollection):
	gv_analysis = {}
	def calculate_gv_curve(self, start=None, end=None):
		"""
		Calculate Grade v.s. Velocity Curve
		by calling GV Analyzer library
		"""
		total_dist = int(self.gpx.length_2d() / 1000.0)
		print "start: " + str(start) + " end: " + str(end) + " total_dist: " + str(total_dist)
		start = start if start and start >= 0 and start < total_dist else None
		end = end if end and end > (start if start else 0) and end < total_dist else None
		print "start: " + str(start) + " end: " + str(end)
		if start or end:
			track_data = self.construct_segment_data(self.gpx, start, end)
			gd = self.construct_grade_dictionary(track_data = track_data)
		else:
			gd = self.construct_grade_dictionary()
		gd_dist_dict = {int(g):obj.total_distance_3d() for g,obj in gd.iteritems()}
		gd_h_speed_dict = {int(g):obj.avg_horizontal_speed() for g,obj in gd.iteritems()}
		# instantiate GVAnalyzer object
		gva = GvAnalyzer(gd_dist_dict)
		analyzed_data = gva.calculate_gv_curve(gd_h_speed_dict)
		if "vh_max_grade" in analyzed_data.keys() and not (start or end):
			self.gv_analysis = analyzed_data

		# run time taken estimation against entire course
		gd_data_whole = {int(g):obj.total_distance_3d() for g,obj in self.construct_grade_dictionary().iteritems()}
		t = gva.estimate_time(gd_data_whole)
		analyzed_data["estimated_time_taken_whole"] = t

		return analyzed_data

	def dump(self):
		track_data_dict = {}
		track_data_header = {
			"start_time":"Start Time",
			"end_time":"End Time",
			"moving_time":"Moving Time",
			"stopped_time":"Stopped Time",
			"total_time":"Total Time",
			"moving_distance":"Moving Distance(km)",
			"stopped_distance":"Stopped Distance(km)",
			"moving_time2":"Moving Time",
			"stopped_time2":"Stopped Time",
			"stopped_time_ratio":"Stopped Time Ratio (%)",
			# GV analysis data
			"vh_max_g":"Max Horizontal Speed Grade (%)",
			"vh_max_v":"Max Horizontal Speed (km/h)",
			"asc_c1":"Ascent Speed Factor 1",
			"asc_c2":"Ascent Speed Factor 2",
			"dsc_c1":"Descent Speed Factor 1",
			"dsc_c2":"Descent Speed Factor 2",
			"asc_min_g":"Ascent Threshold Grade (%)",
			"asc_min_v":"Ascent Threshold Velocity (m/min)",
			"asc_nth_percentile":"Ascent Nth Percentile Grade (%)",
			"dsc_min_g":"Descent Threshold Grade (%)",
			"dsc_min_v":"Descent Threshold Velocity (m/min)",
			"dsc_nth_percentile":"Descent Nth Percentile Grade (%)",
			"dsc_asc_ratio":"Descent/Ascent Threshold Velocity Ratio",
			"estimated_moving_time":"Estimated Moving Time",
		}
		# overall stat
		start_time, end_time = self.gpx.get_time_bounds()
		track_data_dict["start_time"] = str(start_time)
		track_data_dict["end_time"] = str(end_time)
		moving_time, stopped_time, moving_distance, stopped_distance, max_speed = self.gpx.get_moving_data()
		track_data_dict["moving_time"] = dump_time(moving_time)
		track_data_dict["stopped_time"] = dump_time(stopped_time)
		total_time = moving_time + stopped_time
		track_data_dict["total_time"] = dump_time(moving_time + stopped_time)
		track_data_dict["moving_distance"] = moving_distance / 1000.0
		track_data_dict["stopped_distance"] = stopped_distance / 1000.0
		# trail route data
		stopped_time2 = self.stopped_time
		track_data_dict["stopped_time2"] = dump_time(stopped_time2)
		track_data_dict["moving_time2"] = dump_time(total_time - stopped_time2)
		stopped_time_ratio = (100*stopped_time2 / total_time) if total_time != 0 else 0.0
		track_data_dict["stopped_time_ratio"] = stopped_time_ratio

		if self.gv_analysis:
			track_data_dict["vh_max_g"] = self.gv_analysis.get("vh_max_grade")
			track_data_dict["vh_max_v"] = self.gv_analysis.get("vh_max_value")
			track_data_dict["asc_c1"] = self.gv_analysis.get("asc_data").get("coefficient1") * 1000
			track_data_dict["dsc_c1"] = self.gv_analysis.get("dsc_data").get("coefficient1") * 1000
			track_data_dict["asc_c2"] = self.gv_analysis.get("asc_data").get("coefficient2", 0) * 1000
			track_data_dict["dsc_c2"] = self.gv_analysis.get("dsc_data").get("coefficient2", 0) * 1000
			track_data_dict["asc_min_g"] = self.gv_analysis.get("asc_data").get("local_min1")
			track_data_dict["dsc_min_g"] = self.gv_analysis.get("dsc_data").get("local_min1")
			track_data_dict["asc_min_v"] = self.gv_analysis.get("asc_data").get("local_min2")
			track_data_dict["dsc_min_v"] = self.gv_analysis.get("dsc_data").get("local_min2")
			track_data_dict["asc_nth_percentile"] = self.gv_analysis.get("asc_data").get("nth_percentile_grade")
			track_data_dict["dsc_nth_percentile"] = self.gv_analysis.get("dsc_data").get("nth_percentile_grade")
			track_data_dict["dsc_asc_ratio"] = track_data_dict["dsc_min_v"] / track_data_dict["asc_min_v"]
			track_data_dict["estimated_moving_time"] = dump_time(self.gv_analysis.get("estimated_time_taken"))

		# get route data and update dictionary
		(dump_header, dump_data) = super(RecordData, self).dump()
		track_data_header.update(dump_header)
		track_data_dict.update(dump_data)

		return (track_data_header, track_data_dict)
