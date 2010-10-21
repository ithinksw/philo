from django.utils.translation import ugettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.template import Template, Parser, Lexer, TOKEN_BLOCK, TOKEN_VAR, TemplateSyntaxError
from django.utils import simplejson as json
import re
from philo.utils import LOADED_TEMPLATE_ATTR


INSECURE_TAGS = (
	'load',
	'extends',
	'include',
	'debug',
)


class RedirectValidator(RegexValidator):
	"""Based loosely on the URLValidator, but no option to verify_exists"""
	regex = re.compile(
		r'^(?:https?://' # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
		r'localhost|' #localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?' # optional port
		r'(?:/?|[/?#]?\S+)|'
		r'[^?#\s]\S*)$',
		re.IGNORECASE)
	message = _(u'Enter a valid absolute or relative redirect target')


class URLLinkValidator(RegexValidator):
	"""Based loosely on the URLValidator, but no option to verify_exists"""
	regex = re.compile(
		r'^(?:https?://' # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
		r'localhost|' #localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?' # optional port
		r'|)' # also allow internal links
		r'(?:/?|[/?#]?\S+)$', re.IGNORECASE)
	message = _(u'Enter a valid absolute or relative redirect target')


def json_validator(value):
	try:
		json.loads(value)
	except Exception, e:
		raise ValidationError(u'JSON decode error: %s' % e)


class TemplateValidationParser(Parser):
	def __init__(self, tokens, allow=None, disallow=None, secure=True):
		super(TemplateValidationParser, self).__init__(tokens)
		
		allow, disallow = set(allow or []), set(disallow or [])
		
		if secure:
			disallow |= set(INSECURE_TAGS)
		
		self.allow, self.disallow, self.secure = allow, disallow, secure
	
	def parse(self, parse_until=None):
		if parse_until is None:
			parse_until = []
		
		nodelist = self.create_nodelist()
		while self.tokens:
			token = self.next_token()
			# We only need to parse var and block tokens.
			if token.token_type == TOKEN_VAR:
				if not token.contents:
					self.empty_variable(token)
				
				filter_expression = self.compile_filter(token.contents)
				var_node = self.create_variable_node(filter_expression)
				self.extend_nodelist(nodelist, var_node,token)
			elif token.token_type == TOKEN_BLOCK:
				if token.contents in parse_until:
					# put token back on token list so calling code knows why it terminated
					self.prepend_token(token)
					return nodelist
				
				try:
					command = token.contents.split()[0]
				except IndexError:
					self.empty_block_tag(token)
				
				if (self.allow and command not in self.allow) or (self.disallow and command in self.disallow):
					self.disallowed_tag(command)
				
				self.enter_command(command, token)
				
				try:
					compile_func = self.tags[command]
				except KeyError:
					self.invalid_block_tag(token, command, parse_until)
				
				try:
					compiled_result = compile_func(self, token)
				except TemplateSyntaxError, e:
					if not self.compile_function_error(token, e):
						raise
				
				self.extend_nodelist(nodelist, compiled_result, token)
				self.exit_command()
		
		if parse_until:
			self.unclosed_block_tag(parse_until)
		
		return nodelist
	
	def disallowed_tag(self, command):
		if self.secure and command in INSECURE_TAGS:
			raise ValidationError('Tag "%s" is not permitted for security reasons.' % command)
		raise ValidationError('Tag "%s" is not permitted here.' % command)


class TemplateValidator(object): 
	def __init__(self, allow=None, disallow=None, secure=True):
		self.allow = allow
		self.disallow = disallow
		self.secure = secure
	
	def __call__(self, value):
		try:
			self.validate_template(value)
		except ValidationError:
			raise
		except Exception, e:
			raise ValidationError("Template code invalid. Error was: %s: %s" % (e.__class__.__name__, e))
	
	def validate_template(self, template_string):
		# We want to tokenize like normal, then use a custom parser.
		lexer = Lexer(template_string, None)
		tokens = lexer.tokenize()
		parser = TemplateValidationParser(tokens, self.allow, self.disallow, self.secure)
		
		for node in parser.parse():
			template = getattr(node, LOADED_TEMPLATE_ATTR, None)