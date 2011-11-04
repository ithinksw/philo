"""
Waldo provides abstract :class:`.MultiView`\ s to handle several levels of common authentication:

* :class:`LoginMultiView` handles the case where users only need to be able to log in and out.
* :class:`PasswordMultiView` handles the case where users will also need to change their password.
* :class:`RegistrationMultiView` builds on top of :class:`PasswordMultiView` to handle user registration, as well.
* :class:`AccountMultiView` adds account-handling functionality to the :class:`RegistrationMultiView`.

"""

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
	"""Handles exclusively methods and views related to logging users in and out."""
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the login form.
	login_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_login_related')
	#: A django form class which will be used for the authentication process. Default: :class:`.WaldoAuthenticationForm`.
	login_form = WaldoAuthenticationForm
	
	@property
	def urlpatterns(self):
		return patterns('',
			url(r'^login$', self.login, name='login'),
			url(r'^logout$', self.logout, name='logout'),
		)
	
	def set_requirement_redirect(self, request, redirect=None):
		"""Figures out and stores where a user should end up after landing on a page (like the login page) because they have not fulfilled some kind of requirement."""
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
		"""Returns the location which a user should be redirected to after fulfilling a requirement (like logging in)."""
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
		"""Renders the :attr:`login_page` with an instance of the :attr:`login_form` for the given :class:`HttpRequest`."""
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
			form = self.login_form(request)
		
		request.session.set_test_cookie()
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'form': form
		})
		return self.login_page.render_to_response(request, extra_context=context)
	
	@never_cache
	def logout(self, request, extra_context=None):
		"""Logs the given :class:`HttpRequest` out, redirecting the user to the page they just left or to the :meth:`~.Node.get_absolute_url` for the ``request.node``."""
		return auth_views.logout(request, request.META.get('HTTP_REFERER', request.node.get_absolute_url()))
	
	def login_required(self, view):
		"""Wraps a view function to require that the user be logged in."""
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
	"""
	Adds support for password setting, resetting, and changing to the :class:`LoginMultiView`. Password reset support includes handling of a confirmation email.
	
	"""
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the password reset request form.
	password_reset_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_related', blank=True, null=True)
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the password reset confirmation email.
	password_reset_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_reset_confirmation_email_related', blank=True, null=True)
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the password setting form (i.e. the page that users will see after confirming a password reset).
	password_set_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_set_related', blank=True, null=True)
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the password change form.
	password_change_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_password_change_related', blank=True, null=True)
	
	#: The password change form class. Default: :class:`django.contrib.auth.forms.PasswordChangeForm`.
	password_change_form = PasswordChangeForm
	#: The password set form class. Default: :class:`django.contrib.auth.forms.SetPasswordForm`.
	password_set_form = SetPasswordForm
	#: The password reset request form class. Default: :class:`django.contrib.auth.forms.PasswordResetForm`.
	password_reset_form = PasswordResetForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(PasswordMultiView, self).urlpatterns
		
		if self.password_reset_page_id and self.password_reset_confirmation_email_id and self.password_set_page_id:
			urlpatterns += patterns('',
				url(r'^password/reset$', csrf_protect(self.password_reset), name='password_reset'),
				url(r'^password/reset/(?P<uidb36>\w+)/(?P<token>[^/]+)$', self.password_reset_confirm, name='password_reset_confirm'),
			)
		
		if self.password_change_page_id:
			urlpatterns += patterns('',
				url(r'^password/change$', csrf_protect(self.login_required(self.password_change)), name='password_change'),
			)
		return urlpatterns
	
	def make_confirmation_link(self, confirmation_view, token_generator, user, node, token_args=None, reverse_kwargs=None, secure=False):
		"""
		Generates a confirmation link for an arbitrary action, such as a password reset.
		
		:param confirmation_view: The view function which needs to be linked to.
		:param token_generator: Generates a confirmable token for the action.
		:param user: The user who is trying to take the action.
		:param node: The node which is providing the basis for the confirmation URL.
		:param token_args: A list of additional arguments (i.e. besides the user) to be used for token creation.
		:param reverse_kwargs: A dictionary of any additional keyword arguments necessary for correctly reversing the view.
		:param secure: Whether the link should use the https:// or http://.
		
		"""
		token = token_generator.make_token(user, *(token_args or []))
		kwargs = {
			'uidb36': int_to_base36(user.id),
			'token': token
		}
		kwargs.update(reverse_kwargs or {})
		return node.construct_url(subpath=self.reverse(confirmation_view, kwargs=kwargs), with_domain=True, secure=secure)
	
	def send_confirmation_email(self, subject, email, page, extra_context):
		"""
		Sends a confirmation email for an arbitrary action, such as a password reset. If the ``page``'s :class:`.Template` has a mimetype of ``text/html``, then the email will be sent with an HTML alternative version.
		
		:param subject: The subject line of the email.
		:param email: The recipient's address.
		:param page: The page which will be used to render the email body.
		:param extra_context: The context for rendering the ``page``.
		
		"""
		text_content = page.render_to_string(extra_context=extra_context)
		from_email = 'noreply@%s' % Site.objects.get_current().domain
		
		if page.template.mimetype == 'text/html':
			msg = EmailMultiAlternatives(subject, striptags(text_content), from_email, [email])
			msg.attach_alternative(text_content, 'text/html')
			msg.send()
		else:
			send_mail(subject, text_content, from_email, [email])
	
	def password_reset(self, request, extra_context=None, token_generator=password_token_generator):
		"""
		Handles the process by which users request a password reset, and generates the context for the confirmation email. That context will contain:
		
		link
			The confirmation link for the password reset.
		user
			The user requesting the reset.
		site
			The current :class:`Site`.
		request
			The current :class:`HttpRequest` instance.
		
		:param token_generator: The token generator to use for the confirmation link.
		
		"""
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
						'request': request
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
		Checks that ``token``` is valid, and if so, renders an instance of :attr:`password_set_form` with :attr:`password_set_page`.
		
		:param token_generator: The token generator used to check the ``token``.
		
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
		"""Renders an instance of :attr:`password_change_form` with :attr:`password_change_page`."""
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
	"""Adds support for user registration to the :class:`PasswordMultiView`."""
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to display the registration form.
	register_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_related', blank=True, null=True)
	#: A :class:`ForeignKey` to the :class:`.Page` which will be used to render the registration confirmation email.
	register_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_register_confirmation_email_related', blank=True, null=True)
	#: The registration form class. Default: :class:`.RegistrationForm`.
	registration_form = RegistrationForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(RegistrationMultiView, self).urlpatterns
		if self.register_page_id and self.register_confirmation_email_id:
			urlpatterns += patterns('',
				url(r'^register$', csrf_protect(self.register), name='register'),
				url(r'^register/(?P<uidb36>\w+)/(?P<token>[^/]+)$', self.register_confirm, name='register_confirm')
			)
		return urlpatterns
	
	def register(self, request, extra_context=None, token_generator=registration_token_generator):
		"""
		Renders the :attr:`register_page` with an instance of :attr:`registration_form` in the context as ``form``. If the form has been submitted, sends a confirmation email using :attr:`register_confirmation_email` and the same context as :meth:`PasswordMultiView.password_reset`.
		
		:param token_generator: The token generator to use for the confirmation link.
		
		"""
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
		Checks that ``token`` is valid, and if so, logs the user in and redirects them to :meth:`post_register_confirm_redirect`.
		
		:param token_generator: The token generator used to check the ``token``.
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
		"""Returns an :class:`HttpResponseRedirect` for post-registration-confirmation. Default: :meth:`Node.get_absolute_url` for ``request.node``."""
		return HttpResponseRedirect(request.node.get_absolute_url())
	
	class Meta:
		abstract = True


class AccountMultiView(RegistrationMultiView):
	"""Adds support for user accounts on top of the :class:`RegistrationMultiView`. By default, the account consists of the first_name, last_name, and email fields of the User model. Using a different account model is as simple as replacing :attr:`account_form` with any form class that takes an :class:`auth.User` instance as the first argument."""
	#: A :class:`ForeignKey` to the :class:`Page` which will be used to render the account management form.
	manage_account_page = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_manage_account_related', blank=True, null=True)
	#: A :class:`ForeignKey` to a :class:`Page` which will be used to render an email change confirmation email. This is optional; if it is left blank, then email changes will be performed without confirmation.
	email_change_confirmation_email = models.ForeignKey(Page, related_name='%(app_label)s_%(class)s_email_change_confirmation_email_related', blank=True, null=True, help_text="If this is left blank, email changes will be performed without confirmation.")
	
	#: A django form class which will be used to manage the user's account. Default: :class:`.UserAccountForm`
	account_form = UserAccountForm
	
	@property
	def urlpatterns(self):
		urlpatterns = super(AccountMultiView, self).urlpatterns
		if self.manage_account_page_id:
			urlpatterns += patterns('',
				url(r'^account$', self.login_required(self.account_view), name='account'),
			)
		if self.email_change_confirmation_email_id:
			urlpatterns += patterns('',
				url(r'^account/email/(?P<uidb36>\w+)/(?P<email>[\w.]+[+][\w.]+)/(?P<token>[^/]+)$', self.email_change_confirm, name='email_change_confirm')
			)
		return urlpatterns
	
	def account_view(self, request, extra_context=None, token_generator=email_token_generator, *args, **kwargs):
		"""
		Renders the :attr:`manage_account_page` with an instance of :attr:`account_form` in the context as ``form``. If the form has been posted, the user's email was changed, and :attr:`email_change_confirmation_email` is not ``None``, sends a confirmation email to the new email to make sure it exists before making the change. The email will have the same context as :meth:`PasswordMultiView.password_reset`.
		
		:param token_generator: The token generator to use for the confirmation link. 
		
		"""
		if request.method == 'POST':
			form = self.account_form(request.user, request.POST, request.FILES)
			
			if form.is_valid():
				message = "Account information saved."
				redirect = self.get_requirement_redirect(request, default='')
				if form.email_changed() and self.email_change_confirmation_email:
					email = form.reset_email()
					
					current_site = Site.objects.get_current()
					
					context = {
						'link': self.make_confirmation_link('email_change_confirm', token_generator, request.user, request.node, token_args=[email], reverse_kwargs={'email': email.replace('@', '+')}, secure=request.is_secure()),
						'user': request.user,
						'site': current_site,
						'request': request
					}
					self.send_confirmation_email('Confirm account email change at %s' % current_site.domain, email, self.email_change_confirmation_email, context)
					
					message = "An email has be sent to %s to confirm the email%s." % (email, " change" if bool(request.user.email) else "")
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
		"""Returns ``True`` if the ``user`` has a valid account and ``False`` otherwise."""
		form = self.account_form(user, {})
		form.data = form.initial
		return form.is_valid()
	
	def account_required(self, view):
		"""Wraps a view function to allow access only to users with valid accounts and otherwise redirect them to the :meth:`account_view`."""
		def inner(request, *args, **kwargs):
			if not self.has_valid_account(request.user):
				messages.add_message(request, messages.ERROR, "You need to add some account information before you can access that page.", fail_silently=True)
				if self.manage_account_page:
					self.set_requirement_redirect(request, redirect=request.path)
					redirect = self.reverse('account', node=request.node)
				else:
					redirect = request.node.get_absolute_url()
				return HttpResponseRedirect(redirect)
			return view(request, *args, **kwargs)
		
		inner = self.login_required(inner)
		return inner
	
	def post_register_confirm_redirect(self, request):
		"""Automatically redirects users to the :meth:`account_view` after registration."""
		if self.manage_account_page:
			messages.add_message(request, messages.INFO, 'Welcome! Please fill in some more information.', fail_silently=True)
			return HttpResponseRedirect(self.reverse('account', node=request.node))
		return super(AccountMultiView, self).post_register_confirm_redirect(request)
	
	def email_change_confirm(self, request, extra_context=None, uidb36=None, token=None, email=None, token_generator=email_token_generator):
		"""
		Checks that ``token`` is valid, and if so, changes the user's email.
		
		:param token_generator: The token generator used to check the ``token``.
		
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
			self.account_form.set_email(user, email)
			messages.add_message(request, messages.SUCCESS, 'Email changed successfully.')
			if self.manage_account_page:
				redirect = self.reverse('account', node=request.node)
			else:
				redirect = request.node.get_absolute_url()
			return HttpResponseRedirect(redirect)
		
		raise Http404
	
	class Meta:
		abstract = True