import json
import socket
import urllib2
#import requests

class GvAnalyzerClient(object):
	"""
	GV Analyzer Client
	"""
	def __init__(self, gd_data):
		self.base_url = "https://damp-retreat-1145.herokuapp.com/"
		self.base_url = "http://127.0.0.1:5000/"
		self.gd_data = gd_data
		socket.setdefaulttimeout(15)

	def analyze(self, gv_data):
		"""Invoke analyze API of GV Analyzer"""
		url = self.base_url + "gv_analyze"
		gdv_data = json.dumps({"gd_data":self.gd_data, "gv_data":gv_data})
		req = urllib2.Request(url)
		req.add_header('Content-Type', 'application/json')
		req.add_header('Accept', 'application/json')
		try:
			res = urllib2.urlopen(req, gdv_data)
			response = json.loads(res.read())
			return response
		except Exception as e:
			return {"Error":str(e)}
		"""
		#requests version:
		headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json'}
		try:
			r = requests.post(url, data = gdv_data, headers = headers)
			return r.json()
		except requests.exceptions.RequestException as e:
			return {"Error":str(e)}
		"""

"""
def gva():
	url = "http://127.0.0.1:5000/analyze"
	#url = "https://damp-retreat-1145.herokuapp.com/analyze"
	headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json'}
	r = requests.post(url, data = open("event.json", "rb"), headers = headers)
	print json.dumps(r.json(), indent=4)
"""