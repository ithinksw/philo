"""
Based on :mod:`django.contrib.auth.tokens`. Supports the following settings:

:setting:`WALDO_REGISTRATION_TIMEOUT_DAYS`
	The number of days a registration link will be valid before expiring. Default: 1.

:setting:`WALDO_EMAIL_TIMEOUT_DAYS`
	The number of days an email change link will be valid before expiring. Default: 1.

"""

from hashlib import sha1
from datetime import date

from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int
from django.contrib.auth.tokens import PasswordResetTokenGenerator


REGISTRATION_TIMEOUT_DAYS = getattr(settings, 'WALDO_REGISTRATION_TIMEOUT_DAYS', 1)
EMAIL_TIMEOUT_DAYS = getattr(settings, 'WALDO_EMAIL_TIMEOUT_DAYS', 1)


class RegistrationTokenGenerator(PasswordResetTokenGenerator):
	"""Strategy object used to generate and check tokens for the user registration mechanism."""
	
	def check_token(self, user, token):
		"""Check that a registration token is correct for a given user."""
		# If the user is active, the hash can't be valid.
		if user.is_active:
			return False
		
		# Parse the token
		try:
			ts_b36, hash = token.split('-')
		except ValueError:
			return False
		
		try:
			ts = base36_to_int(ts_b36)
		except ValueError:
			return False
		
		# Check that the timestamp and uid have not been tampered with.
		if self._make_token_with_timestamp(user, ts) != token:
			return False
		
		# Check that the timestamp is within limit
		if (self._num_days(self._today()) - ts) > REGISTRATION_TIMEOUT_DAYS:
			return False
		
		return True
	
	def _make_token_with_timestamp(self, user, timestamp):
		ts_b36 = int_to_base36(timestamp)
		
		# By hashing on the internal state of the user and using state that is
		# sure to change, we produce a hash that will be invalid as soon as it
		# is used.
		hash = sha1(settings.SECRET_KEY + unicode(user.id) + unicode(user.is_active) + user.last_login.strftime('%Y-%m-%d %H:%M:%S') + unicode(timestamp)).hexdigest()[::2]
		return '%s-%s' % (ts_b36, hash)


registration_token_generator = RegistrationTokenGenerator()


class EmailTokenGenerator(PasswordResetTokenGenerator):
	"""Strategy object used to generate and check tokens for a user email change mechanism."""
	
	def make_token(self, user, email):
		"""Returns a token that can be used once to do an email change for the given user and email."""
		return self._make_token_with_timestamp(user, email, self._num_days(self._today()))
	
	def check_token(self, user, email, token):
		if email == user.email:
			return False
		
		# Parse the token
		try:
			ts_b36, hash = token.split('-')
		except ValueError:
			return False
		
		try:
			ts = base36_to_int(ts_b36)
		except ValueError:
			return False
		
		# Check that the timestamp and uid have not been tampered with.
		if self._make_token_with_timestamp(user, email, ts) != token:
			return False
		
		# Check that the timestamp is within limit
		if (self._num_days(self._today()) - ts) > EMAIL_TIMEOUT_DAYS:
			return False
		
		return True
	
	def _make_token_with_timestamp(self, user, email, timestamp):
		ts_b36 = int_to_base36(timestamp)
		
		hash = sha1(settings.SECRET_KEY + unicode(user.id) + user.email + email + unicode(timestamp)).hexdigest()[::2]
		return '%s-%s' % (ts_b36, hash)


email_token_generator = EmailTokenGenerator()