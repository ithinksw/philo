"""
Penfield supplies two template filters:

.. templatefilter:: monthname

monthname
---------
Returns the name of a month with the supplied numeric value.

.. templatefilter:: apmonthname

apmonthname
-----------
Returns the Associated Press abbreviated month name for the supplied numeric value.

"""
from django import template
from django.utils.dates import MONTHS, MONTHS_AP

register = template.Library()

def monthname(value):
	try:
		value = int(value)
	except:
		pass
	
	try:
		return MONTHS[value]
	except KeyError:
		return value

register.filter('monthname', monthname)

def apmonthname(value):
	try:
		value = int(value)
	except:
		pass
	
	try:
		return MONTHS_AP[value]
	except KeyError:
		return value

register.filter('apmonthname', apmonthname)
