from datetime import date
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from philo.contrib.waldo.tokens import REGISTRATION_TIMEOUT_DAYS


LOGIN_FORM_KEY = 'this_is_the_login_form'
LoginForm = type('LoginForm', (AuthenticationForm,), {
	LOGIN_FORM_KEY: forms.BooleanField(widget=forms.HiddenInput, initial=True)
})


class EmailInput(forms.TextInput):
	input_type = 'email'


class RegistrationForm(UserCreationForm):
	email = forms.EmailField(widget=EmailInput)
	
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