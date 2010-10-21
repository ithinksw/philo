from django import forms
from django.conf.urls.defaults import url, patterns, include
from django.contrib import messages
from django.contrib.auth import authenticate, login, views as auth_views
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator as password_token_generator
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.defaultfilters import striptags
from django.utils.http import int_to_base36, base36_to_int
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from philo.models import MultiView, Page
from philo.contrib.waldo.forms import LOGIN_FORM_KEY, LoginForm, RegistrationForm
from philo.contrib.waldo.tokens import registration_token_generator, email_token_generator
import urlparse


ERROR_MESSAGE = ugettext_lazy("Please enter a correct username and password. Note that both fields are case-sensitive.")


def get_field_data(obj, fields):
	if fields == None:
		fields = [field.name for field in obj._meta.fields if field.editable]
	
	return dict([(field.name, field.value_from_object(obj)) for field in obj._meta.fields if field.name in fields])


class LoginMultiView(MultiView):
	"""
	Handles login, registration, and forgotten passwords. In other words, this
	multiview provides exclusively view and methods related to usernames and
	passwords.
	"""
	login_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_login_related')
	password_reset_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_related')
	password_reset_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_confirmation_email_related')
	password_set_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_set_related')
	password_change_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_change_related', blank=True, null=True)
	register_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_related')
	register_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_confirmation_email_related')
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^login/$', self.login, name='login'),
			url(r'^logout/$', self.logout, name='logout'),
			
			url(r'^password/reset/$', csrf_protect(self.password_reset), name='password_reset'),
			url(r'^password/reset/(?P<uidb36>\w+)/(?P<token>[^/]+)/$', self.password_reset_confirm, name='password_reset_confirm'),
			
			url(r'^register/$', csrf_protect(self.register), name='register'),
			url(r'^register/(?P<uidb36>\w+)/(?P<token>[^/]+)/$', self.register_confirm, name='register_confirm')
		)
		
		if self.password_change_page:
			urlpatterns += patterns('',
				url(r'^password/change/$', csrf_protect(self.login_required(self.password_change)), name='password_change'),
			)
		
		return urlpatterns
	
	def get_context(self, extra_dict=None):
		context = {}
		context.update(extra_dict or {})
		return context
	
	def display_login_page(self, request, message, extra_context=None):
		request.session.set_test_cookie()
		
		referrer = request.META.get('HTTP_REFERER', None)
		
		if referrer is not None:
			referrer = urlparse.urlparse(referrer)
			host = referrer[1]
			if host != request.get_host():
				referrer = None
			else:
				redirect = '%s?%s' % (referrer[2], referrer[4])
		
		if referrer is None:
			redirect = request.node.get_absolute_url()
		
		path = request.get_full_path()
		if redirect != path:
			if redirect is None:
				redirect = '/'.join(path.split('/')[:-2])
			request.session['redirect'] = redirect
		
		if request.POST:
			form = LoginForm(request.POST)
		else:
			form = LoginForm()
		context = self.get_context({
			'message': message,
			'form': form
		})
		context.update(extra_context or {})
		return self.login_page.render_to_response(request, extra_context=context)
	
	def login(self, request, extra_context=None):
		"""
		Displays the login form for the given HttpRequest.
		"""
		if request.user.is_authenticated():
			return HttpResponseRedirect(request.node.get_absolute_url())
		
		context = self.get_context(extra_context)
		
		from django.contrib.auth.models import User
		
		# If this isn't already the login page, display it.
		if not request.POST.has_key(LOGIN_FORM_KEY):
			if request.POST:
				message = _("Please log in again, because your session has expired.")
			else:
				message = ""
			return self.display_login_page(request, message, context)

		# Check that the user accepts cookies.
		if not request.session.test_cookie_worked():
			message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
			return self.display_login_page(request, message, context)
		else:
			request.session.delete_test_cookie()
		
		# Check the password.
		username = request.POST.get('username', None)
		password = request.POST.get('password', None)
		user = authenticate(username=username, password=password)
		if user is None:
			message = ERROR_MESSAGE
			if username is not None and u'@' in username:
				# Mistakenly entered e-mail address instead of username? Look it up.
				try:
					user = User.objects.get(email=username)
				except (User.DoesNotExist, User.MultipleObjectsReturned):
					message = _("Usernames cannot contain the '@' character.")
				else:
					if user.check_password(password):
						message = _("Your e-mail address is not your username."
									" Try '%s' instead.") % user.username
					else:
						message = _("Usernames cannot contain the '@' character.")
			return self.display_login_page(request, message, context)

		# The user data is correct; log in the user in and continue.
		else:
			if user.is_active:
				login(request, user)
				try:
					redirect = request.session.pop('redirect')
				except KeyError:
					redirect = request.node.get_absolute_url()
				return HttpResponseRedirect(redirect)
			else:
				return self.display_login_page(request, ERROR_MESSAGE, context)
	login = never_cache(login)
	
	def logout(self, request):
		return auth_views.logout(request, request.META['HTTP_REFERER'])
	
	def login_required(self, view):
		def inner(request, *args, **kwargs):
			if not request.user.is_authenticated():
				login_url = reverse('login', urlconf=self).strip('/')
				return HttpResponseRedirect('%s%s/' % (request.node.get_absolute_url(), login_url))
			return view(request, *args, **kwargs)
		
		return inner
	
	def send_confirmation_email(self, subject, email, page, extra_context):
		text_content = page.render_to_string(extra_context=extra_context)
		from_email = 'noreply@%s' % Site.objects.get_current().domain
		
		if page.template.mimetype == 'text/html':
			msg = EmailMultiAlternatives(subject, striptags(text_content), from_email, [email])
			msg.attach_alternative(text_content, 'text/html')
			msg.send()
		else:
			send_mail(subject, text_content, from_email, [email])
	
	def password_reset(self, request, extra_context=None, token_generator=password_token_generator):
		if request.user.is_authenticated():
			return HttpResponseRedirect(request.node.get_absolute_url())
		
		if request.method == 'POST':
			form = PasswordResetForm(request.POST)
			if form.is_valid():
				current_site = Site.objects.get_current()
				for user in form.users_cache:
					token = token_generator.make_token(user)
					link = 'http://%s/%s/%s/' % (current_site.domain, request.node.get_absolute_url().strip('/'), reverse('password_reset_confirm', urlconf=self, kwargs={'uidb36': int_to_base36(user.id), 'token': token}).strip('/'))
					context = {
						'link': link,
						'username': user.username
					}
					self.send_confirmation_email('Confirm password reset for account at %s' % current_site.domain, user.email, self.password_reset_confirmation_email, context)
					messages.add_message(request, messages.SUCCESS, "An email has been sent to the address you provided with details on resetting your password.", fail_silently=True)
				return HttpResponseRedirect('')
		else:
			form = PasswordResetForm()
		
		context = self.get_context({'form': form})
		context.update(extra_context or {})
		return self.password_reset_page.render_to_response(request, extra_context=context)
	
	def password_reset_confirm(self, request, extra_context=None, uidb36=None, token=None, token_generator=password_token_generator):
		"""
		Checks that a given hash in a password reset link is valid. If so,
		displays the password set form.
		"""
		assert uidb36 is not None and token is not None
		try:
			uid_int = base36_to_int(uidb36)
		except:
			raise Http404
		
		user = get_object_or_404(User, id=uid_int)
		
		if token_generator.check_token(user, token):
			if request.method == 'POST':
				form = SetPasswordForm(user, request.POST)
				
				if form.is_valid():
					form.save()
					messages.add_message(request, messages.SUCCESS, "Password reset successful.")
					return HttpResponseRedirect('/%s/%s/' % (request.node.get_absolute_url().strip('/'), reverse('login', urlconf=self).strip('/')))
			else:
				form = SetPasswordForm(user)
			
			context = self.get_context({'form': form})
			return self.password_set_page.render_to_response(request, extra_context=context)
		
		raise Http404
	
	def password_change(self, request, extra_context=None):
		if request.method == 'POST':
			form = PasswordChangeForm(request.user, request.POST)
			if form.is_valid():
				form.save()
				messages.add_message(request, messages.SUCCESS, 'Password changed successfully.', fail_silently=True)
				return HttpResponseRedirect('')
		else:
			form = PasswordChangeForm(request.user)
		
		context = self.get_context({'form': form})
		context.update(extra_context or {})
		return self.password_change_page.render_to_response(request, extra_context=context)
	
	def register(self, request, extra_context=None, token_generator=registration_token_generator):
		if request.user.is_authenticated():
			return HttpResponseRedirect(request.node.get_absolute_url())
		
		if request.method == 'POST':
			form = RegistrationForm(request.POST)
			if form.is_valid():
				user = form.save()
				current_site = Site.objects.get_current()
				token = token_generator.make_token(user)
				link = 'http://%s/%s/%s/' % (current_site.domain, request.node.get_absolute_url().strip('/'), reverse('register_confirm', urlconf=self, kwargs={'uidb36': int_to_base36(user.id), 'token': token}).strip('/'))
				context = {
					'link': link
				}
				self.send_confirmation_email('Confirm account creation at %s' % current_site.name, user.email, self.register_confirmation_email, context)
				messages.add_message(request, messages.SUCCESS, 'An email has been sent to %s with details on activating your account.' % user.email, fail_silently=True)
				return HttpResponseRedirect(request.node.get_absolute_url())
		else:
			form = RegistrationForm()
		
		context = self.get_context({'form': form})
		context.update(extra_context or {})
		return self.register_page.render_to_response(request, extra_context=context)
	
	def register_confirm(self, request, extra_context=None, uidb36=None, token=None, token_generator=registration_token_generator):
		"""
		Checks that a given hash in a registration link is valid and activates
		the given account. If so, log them in and redirect to
		self.post_register_confirm_redirect.
		"""
		assert uidb36 is not None and token is not None
		try:
			uid_int = base36_to_int(uidb36)
		except:
			raise Http404
		
		user = get_object_or_404(User, id=uid_int)
		if token_generator.check_token(user, token):
			user.is_active = True
			true_password = user.password
			try:
				user.set_password('temp_password')
				user.save()
				authenticated_user = authenticate(username=user.username, password='temp_password')
				login(request, authenticated_user)
			finally:
				# if anything goes wrong, ABSOLUTELY make sure that the true password is restored.
				user.password = true_password
				user.save()
			return self.post_register_confirm_redirect(request)
		
		raise Http404
	
	def post_register_confirm_redirect(self, request):
		return HttpResponseRedirect(request.node.get_absolute_url())
	
	class Meta:
		abstract = True


class AccountMultiView(LoginMultiView):
	"""
	Subclasses may define an account_profile model, fields from the User model
	to include in the account, and fields from the account profile to use in
	the account.
	"""
	manage_account_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_manage_account_related')
	email_change_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_email_change_confirmation_email_related')
	user_fields = ['first_name', 'last_name', 'email']
	required_user_fields = user_fields
	account_profile = None
	account_profile_fields = None
	
	@property
	def urlpatterns(self):
		urlpatterns = super(AccountMultiView, self).urlpatterns
		urlpatterns += patterns('',
			url(r'^account/$', self.login_required(self.account_view), name='account'),
			url(r'^account/email/(?P<uidb36>\w+)/(?P<email>[\w.]+[+][\w.]+)/(?P<token>[^/]+)/$', self.email_change_confirm, name='email_change_confirm')
		)
		return urlpatterns
	
	def get_account_forms(self):
		user_form = forms.models.modelform_factory(User, fields=self.user_fields)
		
		if self.account_profile is None:
			profile_form = None
		else:
			profile_form = forms.models.modelform_factory(self.account_profile, fields=self.account_profile_fields or [field.name for field in self.account_profile._meta.fields if field.editable and field.name != 'user'])
		
		for field_name, field in user_form.base_fields.items():
			if field_name in self.required_user_fields:
				field.required = True
		return user_form, profile_form
	
	def get_account_form_instances(self, user, data=None):
		form_instances = []
		user_form, profile_form = self.get_account_forms()
		if data is None:
			form_instances.append(user_form(instance=user))
			if profile_form:
				form_instances.append(profile_form(instance=self.account_profile._default_manager.get_or_create(user=user)[0]))
		else:
			form_instances.append(user_form(data, instance=user))
			if profile_form:
				form_instances.append(profile_form(data, instance=self.account_profile._default_manager.get_or_create(user=user)[0]))
		
		return form_instances
	
	def account_view(self, request, extra_context=None, token_generator=email_token_generator, *args, **kwargs):
		if request.method == 'POST':
			form_instances = self.get_account_form_instances(request.user, request.POST)
			current_email = request.user.email
			
			for form in form_instances:
				if not form.is_valid():
					break
			else:
				# When the user_form is validated, it changes the model instance, i.e. request.user, in place.
				email = request.user.email
				if current_email != email:
					
					request.user.email = current_email
					
					for form in form_instances:
						form.cleaned_data.pop('email', None)
					
					current_site = Site.objects.get_current()
					token = token_generator.make_token(request.user, email)
					link = 'http://%s/%s/%s/' % (current_site.domain, request.node.get_absolute_url().strip('/'), reverse('email_change_confirm', urlconf=self, kwargs={'uidb36': int_to_base36(request.user.id), 'email': email.replace('@', '+'), 'token': token}).strip('/'))
					context = {
						'link': link
					}
					self.send_confirmation_email('Confirm account email change at %s' % current_site.domain, email, self.email_change_confirmation_email, context)
					messages.add_message(request, messages.SUCCESS, "An email has be sent to %s to confirm the email change." % email)
					
				for form in form_instances:
					form.save()
				messages.add_message(request, messages.SUCCESS, "Account information saved.", fail_silently=True)
				return HttpResponseRedirect('')
		else:
			form_instances = self.get_account_form_instances(request.user)
		
		context = self.get_context({
			'forms': form_instances
		})
		context.update(extra_context or {})
		return self.manage_account_page.render_to_response(request, extra_context=context)
	
	def has_valid_account(self, user):
		user_form, profile_form = self.get_account_forms()
		forms = []
		forms.append(user_form(data=get_field_data(user, self.user_fields)))
		
		if profile_form is not None:
			profile = self.account_profile._default_manager.get_or_create(user=user)[0]
			forms.append(profile_form(data=get_field_data(profile, self.account_profile_fields)))
		
		for form in forms:
			if not form.is_valid():
				return False
		return True
	
	def account_required(self, view):
		def inner(request, *args, **kwargs):
			if not self.has_valid_account(request.user):
				if not request.method == "POST":
					messages.add_message(request, messages.ERROR, "You need to add some account information before you can access this page.", fail_silently=True)
				return self.account_view(request, *args, **kwargs)
			return view(request, *args, **kwargs)
		
		inner = self.login_required(inner)
		return inner
	
	def post_register_confirm_redirect(self, request):
		messages.add_message(request, messages.INFO, 'Welcome! Please fill in some more information.', fail_silently=True)
		return HttpResponseRedirect('/%s/%s/' % (request.node.get_absolute_url().strip('/'), reverse('account', urlconf=self).strip('/')))
	
	def email_change_confirm(self, request, extra_context=None, uidb36=None, token=None, email=None, token_generator=email_token_generator):
		"""
		Checks that a given hash in an email change link is valid. If so, changes the email and redirects to the account page.
		"""
		assert uidb36 is not None and token is not None and email is not None
		
		try:
			uid_int = base36_to_int(uidb36)
		except:
			raise Http404
		
		user = get_object_or_404(User, id=uid_int)
		
		email = '@'.join(email.rsplit('+', 1))
		
		if email == user.email:
			# Then short-circuit.
			raise Http404
		
		if token_generator.check_token(user, email, token):
			user.email = email
			user.save()
			messages.add_message(request, messages.SUCCESS, 'Email changed successfully.')
			return HttpResponseRedirect('/%s/%s/' % (request.node.get_absolute_url().strip('/'), reverse('account', urlconf=self).strip('/')))
		
		raise Http404
	
	class Meta:
		abstract = True