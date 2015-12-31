import json
import math
import numpy as np
import scipy.optimize
import savitzky_golay

"""
Grade-Velocity Analyzer
2015/12/05 Keisuke Yamaguchi
-
Analyzes Grade v.s. Velocity data derived from GPS log data for mountaineering activities where variation in grade (%) would affect speed of the activity. Supported type of activities are:
	- Trail Running
	- Speed Hiking
	- Hiking
"""


class GvAnalyzer(object):
	percentile = 0.95
	def __init__(self, grade_distance_data):
		self.grade_distance_data = grade_distance_data

	def _find_max_horizontal_speed(self, h_speed):
		# find Vh(peak)
		max_vh = 0
		max_vh_g = 0
		for g, vh in h_speed.iteritems():
			if vh > max_vh:
				max_vh = vh
				max_vh_g = g
		return max_vh_g

	def _get_grade_data_percentile_by_dist(self, grade_data):
		# calculate X percentile data for grade data by time
		dist_data = {math.fabs(g):val for g,val in grade_data.iteritems()}
		total_dist = 0
		# get total dist
		for ag,dist in dist_data.iteritems():
			total_dist += dist
		# find n-th percentile grade by 3d distance (starting from 0)
		accumulated_dist = 0
		for ag,dist in sorted(dist_data.iteritems()):
			accumulated_dist += dist
			if accumulated_dist / total_dist > self.percentile:
				return ag

	def calculate_gv_curv(self, grade_velocity_data):
		"""
		Calculate Grade v.s. Velocity Curve
		"""
		# Apply low-pass filter using savitzky-golay
		def apply_low_pass_filter(gv_series):
			def apply_savitzky_golay(series):
				result = savitzky_golay.savitzky_golay(np.array(series), 31, 3)
				return result.tolist()
			speed_data = [v for g,v in sorted(gv_series.iteritems())]
			s_speed_data = apply_savitzky_golay(speed_data)
			gv_series = {g:s_speed_data[i] for i,g in enumerate(sorted(gv_series.keys()))}
			return gv_series

		# calculate n-th percentile grade
		asc_gd = {g:obj for g,obj in self.grade_distance_data.iteritems() if g >= 0}
		dsc_gd = {g:obj for g,obj in self.grade_distance_data.iteritems() if g <= 0}
		self.asc_ag = self._get_grade_data_percentile_by_dist(asc_gd)
		self.dsc_ag = self._get_grade_data_percentile_by_dist(dsc_gd)
		# construct grade-velocity dicst only including n-th percentile data
		gv_dict = {g:v for g,v in grade_velocity_data.iteritems() if g < self.asc_ag and g > -self.dsc_ag}
		# smooth gv curve
		filtered_gv_dict = apply_low_pass_filter(gv_dict)

		# find max horizontal speed (and save grade, h_speed, v_speed)
		max_vh_g = self._find_max_horizontal_speed(filtered_gv_dict)
		# if abs(dsc_ag - max_vh_g) < 3 -> set max_vh_g as "dsc_ag + 3"
		self.max_vh_g = max_vh_g if math.fabs(self.dsc_ag - max_vh_g) > 3 else self.dsc_ag + 3
		self.max_vh_val = filtered_gv_dict[self.max_vh_g]

		# construct gv curv
		self.gv_data = GVData()
		self.gv_data.add_gv_data(filtered_gv_dict, self.max_vh_g, self.max_vh_val)
		
		# return filterd_gv, vh_max_g, vh_max, coefficients
		result = {
			"vh_max_grade": self.max_vh_g,
			"vh_max_value": self.max_vh_val,
			"asc_data": self.gv_data.asc_data.dump_data(),
			"dsc_data": self.gv_data.dsc_data.dump_data(),
		}
		# TODO: combine raw data
		result.get("asc_data").update({"nth_percentile_grade": self.asc_ag})
		result.get("dsc_data").update({"nth_percentile_grade": self.dsc_ag})
		return result

	# estimate() should take offset and other parameters
	def estimate_time(self):
		gd_hd_dict = {g:obj.total_distance() for g,obj in self.grade_distance_data.iteritems()}
		t = self.gv_data.estimate_time(gd_hd_dict)
		return t


class GV_Modeller(object):
    """
    Recreate Grade Velocity Curve from known parameters
    input = Metrics parameters -> recreate GV Data
    """
    def __init__(self, vhpeak, adc, aac, ddc, dac):
        pass


class GVData(object):
	"""
	Grade Velocity data that represents GV data structure
	"""
	def __init__(self, offset_g=0, vhpeak=0, adc=0, ddc=0):
		self.offset_g = offset_g
		self.vhpeak = vhpeak
		self.adc = adc
		self.ddc = ddc

	def add_gv_data(self, gv_data, offset, vhpeak):
		# construct GV curves based on a real data
		def split_gv_data(data_dict, splitting_grade):
			# Split gv data by splitting grade
			asc_v = {g:v for g,v in data_dict.iteritems() if g >= splitting_grade}
			dsc_v = {g:v for g,v in data_dict.iteritems() if g <= splitting_grade}
			return (asc_v, dsc_v)

		self.offset = offset # grade offset
		self.vhpeak = vhpeak
		(asc_vh_gv, dsc_vh_gv) = split_gv_data(gv_data, offset)
		self.asc_data = GVCurvePoly(asc_vh_gv, offset, vhpeak, True)
		self.dsc_data = GVCurvePoly(dsc_vh_gv, offset, vhpeak)

		# save interesting values
		self.asc_coefficients = self.asc_data.coefficients
		self.dsc_coefficients = self.dsc_data.coefficients

	def estimate_time(self, gd_data):
		# estimate time taken based on grade v.s. 3D distance data
        # need to convert 3D distance data to horizontal speed
		total_time = 0
		for g, dist in gd_data.iteritems():
            # use cos(g) = D3d/Dh
            h_dist = dist * math.tan(math.radians(g))
			offsetted_grade = math.fabs(g - self.offset_g)
			if g >= self.offset_g:
				vh = exp_func(offsetted_grade, self.aac, self.adc)
			else:
				vh = exp_func(offsetted_grade, self.dac, self.ddc)
			time_taken = h_dist / ((1000 * vh / 60) / 60)
			total_time += time_taken
		return total_time


# model function for GV curve
def exp_func(x, a, b):
	global vh_peak
	return vh_peak + a * np.power(x, 3) - b * np.power(x, 2)


class GVCurve(object):
	def __init__(self, gv_data, offset, vhpeak, is_ascent=False):
		self.offset = offset # grade offset
		self.vhpeak = vhpeak
		self.data = {int(math.fabs(g-offset)):math.fabs(v) for g,v in gv_data.iteritems()}
		#np.seterr(all='ignore')
		self.is_ascent = is_ascent
		self.coefficients = []
		self.local_min = []
		
		# execute curve fitting
		self.curve_fitting()

	def curve_fitting(self):
		if len(self.data) < 3:
			print "Curv Fitting is not supported with this data!"
			return None

		global vh_peak
		vh_peak = self.vhpeak
		xs = np.array([g for g,v in sorted(self.data.iteritems())])
		ys = np.array([v for g,v in sorted(self.data.iteritems())])
		self.curve_fit(vh_peak, xs, ys)
		
	def get_vspeed_filtered(self):
		return {g:(v*math.tan(math.radians(g+self.offset if self.is_ascent else -g+self.offset)) * 1000 / 60) for g,v in self.data.iteritems()}

	def get_vspeed_fitted(self):
		return {g:(v*math.tan(math.radians(g+self.offset if self.is_ascent else -g+self.offset)) * 1000 / 60) for g,v in self.get_fitted().iteritems()}

	def dump_data(self):
		coefficients = {
			"coefficient"+str(i+1):val for i, val in enumerate(self.coefficients)
		}
		local_min = {
			"local_min"+str(i+1):val for i, val in enumerate(self.local_min)
		}
		data = {
			"filtered_gv": {g:v for g,v in self.data.iteritems()},
			"fitted_gv": self.get_fitted(),
			"filtered_vertical_gv": self.get_vspeed_filtered(),
			"fitted_vertical_gv": self.get_vspeed_fitted(),
		}
		data.update(coefficients)
		data.update(local_min)
		return data


class GVCurvePoly(GVCurve):
	def curve_fit(self, vh_peak, xs, ys):
		popt, pcov = scipy.optimize.curve_fit(exp_func, xs, ys)
		a = popt
		self.coefficients = [a[0], a[1]]
		self.find_local_minimum()

	def find_local_minimum(self):
		# differentiated equation leads to x = (2 * b) / (3 * a)
		# where x = grade that local minimum occurs
		x = (2 * self.coefficients[1]) / (3 * self.coefficients[0])
		g = x+self.offset if self.is_ascent else -x+self.offset
		v_val_at_local_minimum = exp_func(x, self.coefficients[0], self.coefficients[1])
		v_speed = v_val_at_local_minimum * math.tan(math.radians(g)) * 1000 / 60 # km/h -> m/min
		self.local_min = [g, v_speed]
		
		"""
		# DEBUG: re-calculate coefficients
		# in: vhpeak, self.local_min[0], self.local_min[1]
		coefficient0 = -2 * (v_val_at_local_minimum - self.vhpeak) / np.power(x, 3)
		coefficient1 = -3 * (v_val_at_local_minimum - self.vhpeak) / np.power(x, 2)
		self.coefficients_recal = [coefficient0, coefficient1]
		"""

	def get_fitted(self):
		return {g:exp_func(g, self.coefficients[0], self.coefficients[1]) for g in self.data.keys()}
