import urlparse

from django import forms
from django.conf.urls.defaults import url, patterns, include
from django.contrib import messages
from django.contrib.auth import authenticate, login, views as auth_views
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator as password_token_generator
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import models
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.defaultfilters import striptags
from django.utils.http import int_to_base36, base36_to_int
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from philo.models import MultiView, Page
from philo.contrib.waldo.forms import WaldoAuthenticationForm, RegistrationForm, UserAccountForm
from philo.contrib.waldo.tokens import registration_token_generator, email_token_generator


class LoginMultiView(MultiView):
	"""
	Handles exclusively methods and views related to logging users in and out.
	"""
	login_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_login_related')
	login_form = WaldoAuthenticationForm
	
	@property
	def urlpatterns(self):
		return patterns('',
			url(r'^login$', self.login, name='login'),
			url(r'^logout$', self.logout, name='logout'),
		)
	
	def set_requirement_redirect(self, request, redirect=None):
		"Figure out where someone should end up after landing on a `requirement` page like the login page."
		if redirect is not None:
			pass
		elif 'requirement_redirect' in request.session:
			return
		else:
			referrer = request.META.get('HTTP_REFERER', None)
		
			if referrer is not None:
				referrer = urlparse.urlparse(referrer)
				host = referrer[1]
				if host != request.get_host():
					referrer = None
				else:
					redirect = '%s?%s' % (referrer[2], referrer[4])
		
			path = request.get_full_path()
			if referrer is None or redirect == path:
				# Default to the index page if we can't find a referrer or
				# if we'd otherwise redirect to where we already are.
				redirect = request.node.get_absolute_url()
		
		request.session['requirement_redirect'] = redirect
	
	def get_requirement_redirect(self, request, default=None):
		redirect = request.session.pop('requirement_redirect', None)
		# Security checks a la django.contrib.auth.views.login
		if not redirect or ' ' in redirect:
			redirect = default
		else:
			netloc = urlparse.urlparse(redirect)[1]
			if netloc and netloc != request.get_host():
				redirect = default
		if redirect is None:
			redirect = request.node.get_absolute_url()
		return redirect
	
	@never_cache
	def login(self, request, extra_context=None):
		"""
		Displays the login form for the given HttpRequest.
		"""
		self.set_requirement_redirect(request)
		
		# Redirect already-authenticated users to the index page.
		if request.user.is_authenticated():
			messages.add_message(request, messages.INFO, "You are already authenticated. Please log out if you wish to log in as a different user.")
			return HttpResponseRedirect(self.get_requirement_redirect(request))
		
		if request.method == 'POST':
			form = self.login_form(request=request, data=request.POST)
			if form.is_valid():
				redirect = self.get_requirement_redirect(request)
				login(request, form.get_user())
				
				if request.session.test_cookie_worked():
					request.session.delete_test_cookie()
				
				return HttpResponseRedirect(redirect)
		else:
			form = self.login_form()
		
		request.session.set_test_cookie()
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
		return self.login_page.render_to_response(request, extra_context=context)
	
	@never_cache
	def logout(self, request, extra_context=None):
		return auth_views.logout(request, request.META.get('HTTP_REFERER', request.node.get_absolute_url()))
	
	def login_required(self, view):
		def inner(request, *args, **kwargs):
			if not request.user.is_authenticated():
				self.set_requirement_redirect(request, redirect=request.path)
				if request.POST:
					messages.add_message(request, messages.ERROR, "Please log in again, because your session has expired.")
				return HttpResponseRedirect(self.reverse('login', node=request.node))
			return view(request, *args, **kwargs)
		
		return inner
	
	class Meta:
		abstract = True


class PasswordMultiView(LoginMultiView):
	"Adds on views for password-related functions."
	password_reset_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_related', blank=True, null=True)
	password_reset_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_confirmation_email_related', blank=True, null=True)
	password_set_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_set_related', blank=True, null=True)
	password_change_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_change_related', blank=True, null=True)
	
	password_change_form = PasswordChangeForm
	password_set_form = SetPasswordForm
	password_reset_form = PasswordResetForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(PasswordMultiView, self).urlpatterns
		
		if self.password_reset_page and self.password_reset_confirmation_email and self.password_set_page:
			urlpatterns += patterns('',
				url(r'^password/reset$', csrf_protect(self.password_reset), name='password_reset'),
				url(r'^password/reset/(?P<uidb36>\w+)/(?P<token>[^/]+)$', self.password_reset_confirm, name='password_reset_confirm'),
			)
		
		if self.password_change_page:
			urlpatterns += patterns('',
				url(r'^password/change$', csrf_protect(self.login_required(self.password_change)), name='password_change'),
			)
		return urlpatterns
	
	def make_confirmation_link(self, confirmation_view, token_generator, user, node, token_args=None, reverse_kwargs=None, secure=False):
		token = token_generator.make_token(user, *(token_args or []))
		kwargs = {
			'uidb36': int_to_base36(user.id),
			'token': token
		}
		kwargs.update(reverse_kwargs or {})
		return node.construct_url(subpath=self.reverse(confirmation_view, kwargs=kwargs), with_domain=True, secure=secure)
	
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
			form = self.password_reset_form(request.POST)
			if form.is_valid():
				current_site = Site.objects.get_current()
				for user in form.users_cache:
					context = {
						'link': self.make_confirmation_link('password_reset_confirm', token_generator, user, request.node, secure=request.is_secure()),
						'user': user,
						'site': current_site,
						'request': request,
						
						# Deprecated... leave in for backwards-compatibility
						'username': user.username
					}
					self.send_confirmation_email('Confirm password reset for account at %s' % current_site.domain, user.email, self.password_reset_confirmation_email, context)
					messages.add_message(request, messages.SUCCESS, "An email has been sent to the address you provided with details on resetting your password.", fail_silently=True)
				return HttpResponseRedirect('')
		else:
			form = self.password_reset_form()
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
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
				form = self.password_set_form(user, request.POST)
				
				if form.is_valid():
					form.save()
					messages.add_message(request, messages.SUCCESS, "Password reset successful.")
					return HttpResponseRedirect(self.reverse('login', node=request.node))
			else:
				form = self.password_set_form(user)
			
			context = self.get_context()
			context.update(extra_context or {})
			context.update({
				'form': form
			})
			return self.password_set_page.render_to_response(request, extra_context=context)
		
		raise Http404
	
	def password_change(self, request, extra_context=None):
		if request.method == 'POST':
			form = self.password_change_form(request.user, request.POST)
			if form.is_valid():
				form.save()
				messages.add_message(request, messages.SUCCESS, 'Password changed successfully.', fail_silently=True)
				return HttpResponseRedirect('')
		else:
			form = self.password_change_form(request.user)
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
		return self.password_change_page.render_to_response(request, extra_context=context)
	
	class Meta:
		abstract = True


class RegistrationMultiView(PasswordMultiView):
	"""Adds on the pages necessary for letting new users register."""
	register_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_related', blank=True, null=True)
	register_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_confirmation_email_related', blank=True, null=True)
	registration_form = RegistrationForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(RegistrationMultiView, self).urlpatterns
		if self.register_page and self.register_confirmation_email:
			urlpatterns += patterns('',
				url(r'^register$', csrf_protect(self.register), name='register'),
				url(r'^register/(?P<uidb36>\w+)/(?P<token>[^/]+)$', self.register_confirm, name='register_confirm')
			)
		return urlpatterns
	
	def register(self, request, extra_context=None, token_generator=registration_token_generator):
		if request.user.is_authenticated():
			return HttpResponseRedirect(request.node.get_absolute_url())
		
		if request.method == 'POST':
			form = self.registration_form(request.POST)
			if form.is_valid():
				user = form.save()
				current_site = Site.objects.get_current()
				context = {
					'link': self.make_confirmation_link('register_confirm', token_generator, user, request.node, secure=request.is_secure()),
					'user': user,
					'site': current_site,
					'request': request
				}
				self.send_confirmation_email('Confirm account creation at %s' % current_site.name, user.email, self.register_confirmation_email, context)
				messages.add_message(request, messages.SUCCESS, 'An email has been sent to %s with details on activating your account.' % user.email, fail_silently=True)
				return HttpResponseRedirect(request.node.get_absolute_url())
		else:
			form = self.registration_form()
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
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
			temp_password = token_generator.make_token(user)
			try:
				user.set_password(temp_password)
				user.save()
				authenticated_user = authenticate(username=user.username, password=temp_password)
				login(request, authenticated_user)
			finally:
				# if anything goes wrong, do our best make sure that the true password is restored.
				user.password = true_password
				user.save()
			return self.post_register_confirm_redirect(request)
		
		raise Http404
	
	def post_register_confirm_redirect(self, request):
		return HttpResponseRedirect(request.node.get_absolute_url())
	
	class Meta:
		abstract = True


class AccountMultiView(RegistrationMultiView):
	"""
	By default, the `account` consists of the first_name, last_name, and email fields
	of the User model. Using a different account model is as simple as writing a form that
	accepts a User instance as the first argument.
	"""
	manage_account_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_manage_account_related', blank=True, null=True)
	email_change_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_email_change_confirmation_email_related', blank=True, null=True, help_text="If this is left blank, email changes will be performed without confirmation.")
	
	account_form = UserAccountForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(AccountMultiView, self).urlpatterns
		if self.manage_account_page:
			urlpatterns += patterns('',
				url(r'^account$', self.login_required(self.account_view), name='account'),
			)
		if self.email_change_confirmation_email:
			urlpatterns += patterns('',
				url(r'^account/email/(?P<uidb36>\w+)/(?P<email>[\w.]+[+][\w.]+)/(?P<token>[^/]+)$', self.email_change_confirm, name='email_change_confirm')
			)
		return urlpatterns
	
	def account_view(self, request, extra_context=None, token_generator=email_token_generator, *args, **kwargs):
		if request.method == 'POST':
			form = self.account_form(request.user, request.POST, request.FILES)
			
			if form.is_valid():
				message = "Account information saved."
				redirect = self.get_requirement_redirect(request, default='')
				if 'email' in form.changed_data and self.email_change_confirmation_email:
					# ModelForms modify their instances in-place during
					# validation, so reset the instance's email to its
					# previous value here, then remove the new value
					# from cleaned_data. We only do this if an email
					# change confirmation email is available.
					request.user.email = form.initial['email']
					
					email = form.cleaned_data.pop('email')
					
					current_site = Site.objects.get_current()
					
					context = {
						'link': self.make_confirmation_link('email_change_confirm', token_generator, request.user, request.node, token_args=[email], reverse_kwargs={'email': email.replace('@', '+')}, secure=request.is_secure()),
						'user': request.user,
						'site': current_site,
						'request': request
					}
					self.send_confirmation_email('Confirm account email change at %s' % current_site.domain, email, self.email_change_confirmation_email, context)
					
					message = "An email has be sent to %s to confirm the email%s." % (email, bool(request.user.email) and " change" or "")
					if not request.user.email:
						message += " You will need to confirm the email before accessing pages that require a valid account."
						redirect = ''
				
				form.save()
				
				if redirect != '':
					message += " Here you go!"
				
				messages.add_message(request, messages.SUCCESS, message, fail_silently=True)
				return HttpResponseRedirect(redirect)
		else:
			form = self.account_form(request.user)
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
		return self.manage_account_page.render_to_response(request, extra_context=context)
	
	def has_valid_account(self, user):
		form = self.account_form(user, {})
		form.data = form.initial
		return form.is_valid()
	
	def account_required(self, view):
		def inner(request, *args, **kwargs):
			if not self.has_valid_account(request.user):
				messages.add_message(request, messages.ERROR, "You need to add some account information before you can access that page.", fail_silently=True)
				if self.manage_account_page:
					self.set_requirement_redirect(request, redirect=request.path)
					redirect = self.reverse('account', node=request.node)
				else:
					redirect = node.get_absolute_url()
				return HttpResponseRedirect(redirect)
			return view(request, *args, **kwargs)
		
		inner = self.login_required(inner)
		return inner
	
	def post_register_confirm_redirect(self, request):
		if self.manage_account_page:
			messages.add_message(request, messages.INFO, 'Welcome! Please fill in some more information.', fail_silently=True)
			return HttpResponseRedirect(self.reverse('account', node=request.node))
		return super(AccountMultiView, self).post_register_confirm_redirect(request)
	
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
			if self.manage_account_page:
				redirect = self.reverse('account', node=request.node)
			else:
				redirect = request.node.get_absolute_url()
			return HttpResponseRedirect(redirect)
		
		raise Http404
	
	class Meta:
		abstract = True