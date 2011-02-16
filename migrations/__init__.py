from south.creator.freezer import prep_for_freeze
from django.conf import settings
from django.db import models


person_model = getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User')


def freeze_person_model():
	try:
		app_label, model = person_model.split('.')
	except ValueError:
		raise ValueError("Invalid PHILO_PERSON_MODULE definition: %s" % person_model)
	
	model = models.get_model(app_label, model.lower())
	
	if model is None:
		raise ValueError("PHILO_PERSON_MODULE not found: %s" % person_model)
	
	return prep_for_freeze(model)


frozen_person = freeze_person_model()