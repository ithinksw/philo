from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from philo.contrib.waldo.tokens import REGISTRATION_TIMEOUT_DAYS


class EmailInput(forms.TextInput):
	"""Displays an HTML5 email input on browsers which support it and a normal text input on other browsers."""
	input_type = 'email'


class RegistrationForm(UserCreationForm):
	"""
	Handles user registration. If :mod:`recaptcha_django` is installed on the system and :class:`recaptcha_django.middleware.ReCaptchaMiddleware` is in :setting:`settings.MIDDLEWARE_CLASSES`, then a recaptcha field will automatically be added to the registration form.
	
	.. seealso:: `recaptcha-django <http://code.google.com/p/recaptcha-django/>`_
	
	"""
	#: An :class:`EmailField` using the :class:`EmailInput` widget.
	email = forms.EmailField(widget=EmailInput)
	try:
		from recaptcha_django import ReCaptchaField
	except ImportError:
		pass
	else:
		if 'recaptcha_django.middleware.ReCaptchaMiddleware' in settings.MIDDLEWARE_CLASSES:
			recaptcha = ReCaptchaField()
	
	def clean_username(self):
		username = self.cleaned_data['username']
		
		# Trivial case: if the username doesn't exist, go for it!
		try:
			user = User.objects.get(username=username)
		except User.DoesNotExist:
			return username
		
		if not user.is_active and (date.today() - user.date_joined.date()).days > REGISTRATION_TIMEOUT_DAYS and user.last_login == user.date_joined:
			# Then this is a user who has not confirmed their registration and whose time is up. Delete the old user and return the username.
			user.delete()
			return username
		
		raise ValidationError(_("A user with that username already exists."))
	
	def clean_email(self):
		if User.objects.filter(email__iexact=self.cleaned_data['email']):
			raise ValidationError(_('This email is already in use. Please supply a different email address'))
		return self.cleaned_data['email']
	
	def save(self):
		username = self.cleaned_data['username']
		email = self.cleaned_data['email']
		password = self.cleaned_data['password1']
		new_user = User.objects.create_user(username, email, password)
		new_user.is_active = False
		new_user.save()
		return new_user


class UserAccountForm(forms.ModelForm):
	"""Handles a user's account - by default, :attr:`auth.User.first_name`, :attr:`auth.User.last_name`, :attr:`auth.User.email`."""
	first_name = User._meta.get_field('first_name').formfield(required=True)
	last_name = User._meta.get_field('last_name').formfield(required=True)
	email = User._meta.get_field('email').formfield(required=True, widget=EmailInput)
	
	def __init__(self, user, *args, **kwargs):
		kwargs['instance'] = user
		super(UserAccountForm, self).__init__(*args, **kwargs)
	
	def email_changed(self):
		"""Returns ``True`` if the email field changed value and ``False`` if it did not, or if there is no email field on the form. This method must be supplied by account forms used with :mod:`~philo.contrib.waldo`."""
		return 'email' in self.changed_data
	
	def reset_email(self):
		"""
		ModelForms modify their instances in-place during :meth:`_post_clean`; this method resets the email value to its initial state and returns the altered value. This is a method on the form to allow unusual behavior such as storing email on a :class:`UserProfile`.
		
		"""
		email = self.instance.email
		self.instance.email = self.initial['email']
		self.cleaned_data.pop('email')
		return email
	
	@classmethod
	def set_email(cls, user, email):
		"""
		Given a valid instance and an email address, correctly set the email address for that instance and save the changes. This is a class method in order to allow unusual behavior such as storing email on a :class:`UserProfile`.
		
		"""
		user.email = email
		user.save()
		
	
	class Meta:
		model = User
		fields = ('first_name', 'last_name', 'email')


class WaldoAuthenticationForm(AuthenticationForm):
	"""Handles user authentication. Checks that the user has not mistakenly entered their email address (like :class:`django.contrib.admin.forms.AdminAuthenticationForm`) but does not require that the user be staff."""
	ERROR_MESSAGE = _("Please enter a correct username and password. Note that both fields are case-sensitive.")
	
	def clean(self):
		username = self.cleaned_data.get('username')
		password = self.cleaned_data.get('password')
		message = self.ERROR_MESSAGE
		
		if username and password:
			self.user_cache = authenticate(username=username, password=password)
			if self.user_cache is None:
				if u'@' in username:
					# Maybe they entered their email? Look it up, but still raise a ValidationError.
					try:
						user = User.objects.get(email=username)
					except (User.DoesNotExist, User.MultipleObjectsReturned):
						pass
					else:
						if user.check_password(password):
							message = _("Your e-mail address is not your username. Try '%s' instead.") % user.username
				raise ValidationError(message)
			elif not self.user_cache.is_active:
				raise ValidationError(message)
		self.check_for_test_cookie()
		return self.cleaned_data