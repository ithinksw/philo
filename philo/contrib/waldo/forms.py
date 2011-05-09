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
	input_type = 'email'


class RegistrationForm(UserCreationForm):
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
	first_name = User._meta.get_field('first_name').formfield(required=True)
	last_name = User._meta.get_field('last_name').formfield(required=True)
	email = User._meta.get_field('email').formfield(required=True, widget=EmailInput)
	
	def __init__(self, user, *args, **kwargs):
		kwargs['instance'] = user
		super(UserAccountForm, self).__init__(*args, **kwargs)
	
	class Meta:
		model = User
		fields = ('first_name', 'last_name', 'email')


class WaldoAuthenticationForm(AuthenticationForm):
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
	
	def check_for_test_cookie(self):
		# This method duplicates the Django 1.3 AuthenticationForm method.
		if self.request and not self.request.session.test_cookie_worked():
			raise forms.ValidationError(
				_("Your Web browser doesn't appear to have cookies enabled. "
				  "Cookies are required for logging in."))