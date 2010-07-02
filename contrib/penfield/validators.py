from django.core.exceptions import ValidationError


def validate_pagination_count(x):
	if x not in range(1, 10000):
		raise ValidationError('Please enter an integer between 1 and 9999.')