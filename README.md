Trail Route Analytics: analyzes Trail Routes and Activities
===========================================================

Trail Route Analytics is a web appcalition that analyzes trail route and activities. Currently, it only supports GPX file input but is capable of running Grade-Velocity analysis to extract performance metrics or estimate activity time based on such metrics.


Web Interface
-------------
Trail Route Analytics depends on following components to render web interface

* Flask
* Jinja2
* Bootstrap
* Google Maps
* Google Charts

GPX Parsing
-----------
* [gpxpy](https://github.com/tkrajina/gpxpy) library is used for parsing GPX file.

GV Analysis
-----------
For GV Analysis implemented as part of application, following libraries are used

* numpy
* scipy
* Savitzky-Golay Filter (taken from [Cookbook](http://scipy-cookbook.readthedocs.org/items/SavitzkyGolay.html))

See also
--------
* [Development Blog](http://trail-route-analytics.blogspot.jp/)
* [Demo instance on Heroku](http://trail-route-analytics.herokuapp.com/)

License
-------
Trail Route Analytics is licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0)
