from django import forms
from django.conf.urls.defaults import url, patterns, include
from django.contrib import messages
from django.contrib.auth import authenticate, login, views as auth_views
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.http import int_to_base36, base36_to_int
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from philo.models import MultiView, Page
from philo.contrib.waldo.forms import LOGIN_FORM_KEY, LoginForm, RegistrationForm
from philo.contrib.waldo.tokens import default_token_generator


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
	register_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_related')
	register_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_confirmation_email_related')
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^login/$', self.login, name='login'),
			url(r'^logout/$', self.logout, name='logout')
		)
		urlpatterns += patterns('',
			url(r'^password/reset/$', csrf_protect(self.password_reset), name='password_reset'),
			url(r'^password/reset/(?P<uidb36>\w+)/(?P<token>[^/]+)/$',
				self.password_reset_confirm, name='password_reset_confirm')
		)
		urlpatterns += patterns('',
			url(r'^register/$', csrf_protect(self.register), name='register'),
			url(r'^register/(?P<uidb36>\w+)/(?P<token>[^/]+)/$',
				self.register_confirm, name='register_confirm')
		)
		return urlpatterns
	
	def get_context(self, extra_dict=None):
		context = {}
		context.update(extra_dict or {})
		return context
	
	def display_login_page(self, request, message, node=None, extra_context=None):
		request.session.set_test_cookie()
		
		redirect = request.META.get('HTTP_REFERER', None)
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
		return self.login_page.render_to_response(node, request, extra_context=context)
	
	def login(self, request, node=None, extra_context=None):
		"""
		Displays the login form for the given HttpRequest.
		"""
		context = self.get_context(extra_context)
		
		from django.contrib.auth.models import User
		
		# If this isn't already the login page, display it.
		if not request.POST.has_key(LOGIN_FORM_KEY):
			if request.POST:
				message = _("Please log in again, because your session has expired.")
			else:
				message = ""
			return self.display_login_page(request, message, node, context)

		# Check that the user accepts cookies.
		if not request.session.test_cookie_worked():
			message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
			return self.display_login_page(request, message, node, context)
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
			return self.display_login_page(request, message, node, context)

		# The user data is correct; log in the user in and continue.
		else:
			if user.is_active:
				login(request, user)
				redirect = request.session.pop('redirect')
				return HttpResponseRedirect(redirect)
			else:
				return self.display_login_page(request, ERROR_MESSAGE, node, context)
	login = never_cache(login)
	
	def logout(self, request):
		return auth_views.logout(request, request.META['HTTP_REFERER'])
	
	def login_required(self, view):
		def inner(request, node=None, *args, **kwargs):
			if not request.user.is_authenticated():
				login_url = reverse('login', urlconf=self).strip('/')
				return HttpResponseRedirect('%s%s/' % (node.get_absolute_url(), login_url))
			return view(request, node=node, *args, **kwargs)
		
		return inner
	
	def send_confirmation_email(self, subject, email, page, extra_context):
		message = page.render_to_string(extra_context=extra_context)
		from_email = 'noreply@%s' % Site.objects.get_current().domain
		send_mail(subject, message, from_email, [email])
	
	def password_reset(self, request, node=None, extra_context=None):
		pass
	
	def password_reset_confirm(self, request, node=None, extra_context=None):
		pass
	
	def register(self, request, node=None, extra_context=None, token_generator=default_token_generator):
		if request.user.is_authenticated():
			return HttpResponseRedirect(node.get_absolute_url())
		
		if request.method == 'POST':
			form = RegistrationForm(request.POST)
			if form.is_valid():
				user = form.save()
				current_site = Site.objects.get_current()
				token = default_token_generator.make_token(user)
				link = 'http://%s/%s/%s/' % (current_site.domain, node.get_absolute_url().strip('/'), reverse('register_confirm', urlconf=self, kwargs={'uidb36': int_to_base36(user.id), 'token': token}).strip('/'))
				context = {
					'link': link
				}
				self.send_confirmation_email('Confirm account creation at %s' % current_site.name, user.email, self.register_confirmation_email, context)
				messages.add_message(request, messages.SUCCESS, 'An email has been sent to %s with details on activating your account.' % user.email)
				return HttpResponseRedirect('')
		else:
			form = RegistrationForm()
		
		context = self.get_context({'form': form})
		context.update(extra_context or {})
		return self.register_page.render_to_response(node, request, extra_context=context)
	
	def register_confirm(self, request, node=None, extra_context=None, uidb36=None, token=None):
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
		if default_token_generator.check_token(user, token):
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
			return self.post_register_confirm_redirect(request, node)
		
		raise Http404
	
	def post_register_confirm_redirect(self, request, node):
		return HttpResponseRedirect(node.get_absolute_url())
	
	class Meta:
		abstract = True


class AccountMultiView(LoginMultiView):
	"""
	Subclasses may define an account_profile model, fields from the User model
	to include in the account, and fields from the account profile to use in
	the account.
	"""
	manage_account_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_manage_account_page')
	user_fields = ['first_name', 'last_name', 'email']
	required_user_fields = user_fields
	account_profile = None
	account_profile_fields = None
	
	@property
	def urlpatterns(self):
		urlpatterns = super(AccountMultiView, self).urlpatterns
		urlpatterns += patterns('',
			url(r'^account/$', self.login_required(self.account_view), name='account')
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
	
	def account_view(self, request, node=None, extra_context=None):
		if request.method == 'POST':
			form_instances = self.get_account_form_instances(request.user, request.POST)
			
			for form in form_instances:
				if not form.is_valid():
					break
			else:
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
		return self.manage_account_page.render_to_response(node, request, extra_context=context)
	
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
				messages.add_message(request, messages.ERROR, "You need to add some account information before you can post listings.")
				return self.account_view(request, *args, **kwargs)
			return view(request, *args, **kwargs)
		
		inner = self.login_required(inner)
		return inner
	
	def post_register_confirm_redirect(self, request, node):
		messages.add_message(request, messages.INFO, 'Welcome! Please fill in some more information.')
		return HttpResponseRedirect('/%s/%s/' % (node.get_absolute_url().strip('/'), reverse('account', urlconf=self).strip('/')))
	
	class Meta:
		abstract = True