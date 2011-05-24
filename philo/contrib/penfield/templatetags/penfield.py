"""
Penfield supplies two template filters to handle common use cases for blogs and newsletters.

"""
from django import template
from django.utils.dates import MONTHS, MONTHS_AP


register = template.Library()


@register.filter
def monthname(value):
	"""Returns the name of a month with the supplied numeric value."""
	try:
		value = int(value)
	except:
		pass
	
	try:
		return MONTHS[value]
	except KeyError:
		return value


@register.filter
def apmonthname(value):
	"""Returns the Associated Press abbreviated month name for the supplied numeric value."""
	try:
		value = int(value)
	except:
		pass
	
	try:
		return MONTHS_AP[value]
	except KeyError:
		return value