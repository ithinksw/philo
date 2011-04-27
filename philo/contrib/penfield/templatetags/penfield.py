from django import template
from django.utils.dates import MONTHS, MONTHS_AP

register = template.Library()

def monthname(value):
	monthnum = int(value)
	if 1 <= monthnum <= 12:
		return MONTHS[monthnum]
	else:
		return value

register.filter('monthname', monthname)

def apmonthname(value):
	monthnum = int(value)
	if 1 <= monthnum <= 12:
		return MONTHS_AP[monthnum]
	else:
		return value

register.filter('apmonthname', apmonthname)
