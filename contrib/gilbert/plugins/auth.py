from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from .base import Plugin
from ..extdirect import ext_action, ext_method
from ..models import UserPreferences


@ext_action(name='auth')
class Auth(Plugin):
	@property
	def index_js_urls(self):
		return super(Auth, self).index_js_urls + [
			settings.STATIC_URL + 'gilbert/plugins/auth.js',
		]
	
	@property
	def icon_names(self):
		return super(Auth, self).icon_names + [
			'user-silhouette',
			'mask',
			'key--pencil',
			'door-open-out',
		]
	
	@ext_method
	def whoami(self, request):
		user = request.user
		return user.get_full_name() or user.username
	
	@ext_method
	def logout(self, request):
		logout(request)
		return True
	
	@ext_method
	def get_passwd_form(self, request):
		return PasswordChangeForm(request.user).as_extdirect()
	
	@ext_method(form_handler=True)
	def save_passwd_form(self, request):
		form = PasswordChangeForm(request.user, data=request.POST)
		if form.is_valid():
			form.save()
			return True, None
		else:
			return False, form.errors
	
	@ext_method
	def get_preferences(self, request):
		user_preferences, created = UserPreferences.objects.get_or_create(user=request.user)
		
		return user_preferences.preferences
	
	@ext_method
	def set_preferences(self, request, preferences):
		user_preferences, created = UserPreferences.objects.get_or_create(user=request.user)
		user_preferences.preferences = preferences
		
		user_preferences.save()
		return True
	
	@ext_method
	def get_preference(self, request, key):
		preferences = self.get_preferences(request)
		return preferences.get(key, None)
	
	@ext_method
	def set_preference(self, request, key, value):
		preferences = self.get_preferences(request)
		preferences[key] = value
		return self.set_preferences(request, preferences)