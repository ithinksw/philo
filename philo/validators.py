import re

from django.core.exceptions import ValidationError
from django.template import Template, Parser, Lexer, TOKEN_BLOCK, TOKEN_VAR, TemplateSyntaxError
from django.utils import simplejson as json
from django.utils.html import escape, mark_safe
from django.utils.translation import ugettext_lazy as _

from philo.utils.templates import LOADED_TEMPLATE_ATTR


#: Tags which are considered insecure and are therefore always disallowed by secure :class:`TemplateValidator` instances.
INSECURE_TAGS = (
	'load',
	'extends',
	'include',
	'debug',
)


def json_validator(value):
	"""Validates whether ``value`` is a valid json string."""
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


def linebreak_iter(template_source):
	# Cribbed from django/views/debug.py:18
	yield 0
	p = template_source.find('\n')
	while p >= 0:
		yield p+1
		p = template_source.find('\n', p+1)
	yield len(template_source) + 1


class TemplateValidator(object): 
	"""
	Validates whether a string represents valid Django template code.
	
	:param allow: ``None`` or an iterable of tag names which are explicitly allowed. If provided, tags whose names are not in the iterable will cause a ValidationError to be raised if they are used in the template code.
	:param disallow: ``None`` or an iterable of tag names which are explicitly allowed. If provided, tags whose names are in the iterable will cause a ValidationError to be raised if they are used in the template code. If a tag's name is in ``allow`` and ``disallow``, it will be disallowed.
	:param secure: If the validator is set to secure, it will automatically disallow the tag names listed in :const:`INSECURE_TAGS`. Defaults to ``True``.
	
	"""
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
			if hasattr(e, 'source') and isinstance(e, TemplateSyntaxError):
				origin, (start, end) = e.source
				template_source = origin.reload()
				upto = 0
				for num, next in enumerate(linebreak_iter(template_source)):
					if start >= upto and end <= next:
						raise ValidationError(mark_safe("Template code invalid: \"%s\" (%s:%d).<br />%s" % (escape(template_source[start:end]), origin.loadname, num, e)))
					upto = next
			raise ValidationError("Template code invalid. Error was: %s: %s" % (e.__class__.__name__, e))
	
	def validate_template(self, template_string):
		# We want to tokenize like normal, then use a custom parser.
		lexer = Lexer(template_string, None)
		tokens = lexer.tokenize()
		parser = TemplateValidationParser(tokens, self.allow, self.disallow, self.secure)
		
		for node in parser.parse():
			template = getattr(node, LOADED_TEMPLATE_ATTR, None)