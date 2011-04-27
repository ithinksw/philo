import sys
import traceback

from django import template
from django.conf import settings
from django.db import connection
from django.template import loader
from django.template.loaders import cached
from django.test import TestCase
from django.test.utils import setup_test_template_loader

from philo.contrib.penfield.models import Blog, BlogView, BlogEntry
from philo.exceptions import AncestorDoesNotExist
from philo.models import Node, Page, Template


class TemplateTestCase(TestCase):
	fixtures = ['test_fixtures.json']
	
	def test_templates(self):
		"Tests to make sure that embed behaves with complex includes and extends"
		template_tests = self.get_template_tests()
		
		# Register our custom template loader. Shamelessly cribbed from django/tests/regressiontests/templates/tests.py:384.
		cache_loader = setup_test_template_loader(
			dict([(name, t[0]) for name, t in template_tests.iteritems()]),
			use_cached_loader=True,
		)
		
		failures = []
		tests = template_tests.items()
		tests.sort()
		
		# Turn TEMPLATE_DEBUG off, because tests assume that.
		old_td, settings.TEMPLATE_DEBUG = settings.TEMPLATE_DEBUG, False
		
		# Set TEMPLATE_STRING_IF_INVALID to a known string.
		old_invalid = settings.TEMPLATE_STRING_IF_INVALID
		expected_invalid_str = 'INVALID'
		
		# Run tests
		for name, vals in tests:
			xx, context, result = vals
			try:
				test_template = loader.get_template(name)
				output = test_template.render(template.Context(context))
			except Exception:
				exc_type, exc_value, exc_tb = sys.exc_info()
				if exc_type != result:
					tb = '\n'.join(traceback.format_exception(exc_type, exc_value, exc_tb))
					failures.append("Template test %s -- FAILED. Got %s, exception: %s\n%s" % (name, exc_type, exc_value, tb))
				continue
			if output != result:
				failures.append("Template test %s -- FAILED. Expected %r, got %r" % (name, result, output))
		
		# Cleanup
		settings.TEMPLATE_DEBUG = old_td
		settings.TEMPLATE_STRING_IF_INVALID = old_invalid
		loader.template_source_loaders = old_template_loaders
		
		self.assertEqual(failures, [], "Tests failed:\n%s\n%s" % ('-'*70, ("\n%s\n" % ('-'*70)).join(failures)))
	
	
	def get_template_tests(self):
		# SYNTAX --
		# 'template_name': ('template contents', 'context dict', 'expected string output' or Exception class)
		blog = Blog.objects.all()[0]
		return {
			# EMBED INCLUSION HANDLING
			
			'embed01': ('{{ embedded.title|safe }}', {'embedded': blog}, blog.title),
			'embed02': ('{{ embedded.title|safe }}{{ var1 }}{{ var2 }}', {'embedded': blog}, blog.title),
			'embed03': ('{{ embedded.title|safe }} is a lie!', {'embedded': blog}, '%s is a lie!' % blog.title),
			
			# Simple template structure with embed
			'simple01': ('{% embed penfield.blog with "embed01" %}{% embed penfield.blog 1 %}Simple{% block one %}{% endblock %}', {'blog': blog}, '%sSimple' % blog.title),
			'simple02': ('{% extends "simple01" %}', {}, '%sSimple' % blog.title),
			'simple03': ('{% embed penfield.blog with "embed000" %}', {}, settings.TEMPLATE_STRING_IF_INVALID),
			'simple04': ('{% embed penfield.blog 1 %}', {}, settings.TEMPLATE_STRING_IF_INVALID),
			'simple05': ('{% embed penfield.blog with "embed01" %}{% embed blog %}', {'blog': blog}, blog.title),
			
			# Kwargs
			'kwargs01': ('{% embed penfield.blog with "embed02" %}{% embed penfield.blog 1 var1="hi" var2=lo %}', {'lo': 'lo'}, '%shilo' % blog.title),
			
			# Filters/variables
			'filters01': ('{% embed penfield.blog with "embed02" %}{% embed penfield.blog 1 var1=hi|first var2=lo|slice:"3" %}', {'hi': ["These", "words"], 'lo': 'lower'}, '%sTheselow' % blog.title),
			'filters02': ('{% embed penfield.blog with "embed01" %}{% embed penfield.blog entry %}', {'entry': 1}, blog.title),
			
			# Blocky structure
			'block01': ('{% block one %}Hello{% endblock %}', {}, 'Hello'),
			'block02': ('{% extends "simple01" %}{% block one %}{% embed penfield.blog 1 %}{% endblock %}', {}, "%sSimple%s" % (blog.title, blog.title)),
			'block03': ('{% extends "simple01" %}{% embed penfield.blog with "embed03" %}{% block one %}{% embed penfield.blog 1 %}{% endblock %}', {}, "%sSimple%s is a lie!" % (blog.title, blog.title)),
			
			# Blocks and includes
			'block-include01': ('{% extends "simple01" %}{% embed penfield.blog with "embed03" %}{% block one %}{% include "simple01" %}{% embed penfield.blog 1 %}{% endblock %}', {}, "%sSimple%sSimple%s is a lie!" % (blog.title, blog.title, blog.title)),
			'block-include02': ('{% extends "simple01" %}{% block one %}{% include "simple04" %}{% embed penfield.blog with "embed03" %}{% include "simple04" %}{% embed penfield.blog 1 %}{% endblock %}', {}, "%sSimple%s%s is a lie!%s is a lie!" % (blog.title, blog.title, blog.title, blog.title)),
			
			# Tests for more complex situations...
			'complex01': ('{% block one %}{% endblock %}complex{% block two %}{% endblock %}', {}, 'complex'),
			'complex02': ('{% extends "complex01" %}', {}, 'complex'),
			'complex03': ('{% extends "complex02" %}{% embed penfield.blog with "embed01" %}', {}, 'complex'),
			'complex04': ('{% extends "complex03" %}{% block one %}{% embed penfield.blog 1 %}{% endblock %}', {}, '%scomplex' % blog.title),
			'complex05': ('{% extends "complex03" %}{% block one %}{% include "simple04" %}{% endblock %}', {}, '%scomplex' % blog.title),
		}


class NodeURLTestCase(TestCase):
	"""Tests the features of the node_url template tag."""
	urls = 'philo.urls'
	fixtures = ['test_fixtures.json']
	
	def setUp(self):
		if 'south' in settings.INSTALLED_APPS:
			from south.management.commands.migrate import Command
			command = Command()
			command.handle(all_apps=True)
		
		self.templates = [
				("{% node_url %}", "/root/second/"),
				("{% node_url for node2 %}", "/root/second2/"),
				("{% node_url as hello %}<p>{{ hello|slice:'1:' }}</p>", "<p>root/second/</p>"),
				("{% node_url for nodes|first %}", "/root/"),
				("{% node_url with entry %}", settings.TEMPLATE_STRING_IF_INVALID),
				("{% node_url with entry for node2 %}", "/root/second2/2010/10/20/first-entry"),
				("{% node_url with tag for node2 %}", "/root/second2/tags/test-tag/"),
				("{% node_url with date for node2 %}", "/root/second2/2010/10/20"),
				("{% node_url entries_by_day year=date|date:'Y' month=date|date:'m' day=date|date:'d' for node2 as goodbye %}<em>{{ goodbye|upper }}</em>", "<em>/ROOT/SECOND2/2010/10/20</em>"),
				("{% node_url entries_by_month year=date|date:'Y' month=date|date:'m' for node2 %}", "/root/second2/2010/10"),
				("{% node_url entries_by_year year=date|date:'Y' for node2 %}", "/root/second2/2010/"),
		]
		
		nodes = Node.objects.all()
		blog = Blog.objects.all()[0]
		
		self.context = template.Context({
			'node': nodes.get(slug='second'),
			'node2': nodes.get(slug='second2'),
			'nodes': nodes,
			'entry': BlogEntry.objects.all()[0],
			'tag': blog.entry_tags.all()[0],
			'date': blog.entry_dates['day'][0]
		})
	
	def test_nodeurl(self):
		for string, result in self.templates:
			self.assertEqual(template.Template(string).render(self.context), result)

class TreePathTestCase(TestCase):
	urls = 'philo.urls'
	fixtures = ['test_fixtures.json']
	
	def setUp(self):
		if 'south' in settings.INSTALLED_APPS:
			from south.management.commands.migrate import Command
			command = Command()
			command.handle(all_apps=True)
	
	def assertQueryLimit(self, max, expected_result, *args, **kwargs):
		# As a rough measure of efficiency, limit the number of queries required for a given operation.
		settings.DEBUG = True
		call = kwargs.pop('callable', Node.objects.get_with_path)
		try:
			queries = len(connection.queries)
			if isinstance(expected_result, type) and issubclass(expected_result, Exception):
				self.assertRaises(expected_result, call, *args, **kwargs)
			else:
				self.assertEqual(call(*args, **kwargs), expected_result)
			queries = len(connection.queries) - queries
			if queries > max:
				raise AssertionError('"%d" unexpectedly not less than or equal to "%s"' % (queries, max))
		finally:
			settings.DEBUG = False
	
	def test_get_with_path(self):
		root = Node.objects.get(slug='root')
		third = Node.objects.get(slug='third')
		second2 = Node.objects.get(slug='second2')
		fifth = Node.objects.get(slug='fifth')
		e = Node.DoesNotExist
		
		# Empty segments
		self.assertQueryLimit(0, root, '', root=root)
		self.assertQueryLimit(0, e, '')
		self.assertQueryLimit(0, (root, None), '', root=root, absolute_result=False)
		
		# Absolute result
		self.assertQueryLimit(1, third, 'root/second/third')
		self.assertQueryLimit(1, third, 'second/third', root=root)
		self.assertQueryLimit(1, third, 'root//////second/third///')
		
		self.assertQueryLimit(1, e, 'root/secont/third')
		self.assertQueryLimit(1, e, 'second/third')
		
		# Non-absolute result (binary search)
		self.assertQueryLimit(2, (second2, 'sub/path/tail'), 'root/second2/sub/path/tail', absolute_result=False)
		self.assertQueryLimit(3, (second2, 'sub/'), 'root/second2/sub/', absolute_result=False)
		self.assertQueryLimit(2, e, 'invalid/path/1/2/3/4/5/6/7/8/9/1/2/3/4/5/6/7/8/9/0', absolute_result=False)
		self.assertQueryLimit(1, (root, None), 'root', absolute_result=False)
		self.assertQueryLimit(2, (second2, None), 'root/second2', absolute_result=False)
		self.assertQueryLimit(3, (third, None), 'root/second/third', absolute_result=False)
		
		# with root != None
		self.assertQueryLimit(1, (second2, None), 'second2', root=root, absolute_result=False)
		self.assertQueryLimit(2, (third, None), 'second/third', root=root, absolute_result=False)
		
		# Preserve trailing slash
		self.assertQueryLimit(2, (second2, 'sub/path/tail/'), 'root/second2/sub/path/tail/', absolute_result=False)
		
		# Speed increase for leaf nodes - should this be tested?
		self.assertQueryLimit(1, (fifth, 'sub/path/tail/len/five'), 'root/second/third/fourth/fifth/sub/path/tail/len/five', absolute_result=False)
	
	def test_get_path(self):
		root = Node.objects.get(slug='root')
		root2 = Node.objects.get(slug='root')
		third = Node.objects.get(slug='third')
		second2 = Node.objects.get(slug='second2')
		fifth = Node.objects.get(slug='fifth')
		e = AncestorDoesNotExist
		
		self.assertQueryLimit(0, 'root', callable=root.get_path)
		self.assertQueryLimit(0, '', root2, callable=root.get_path)
		self.assertQueryLimit(1, 'root/second/third', callable=third.get_path)
		self.assertQueryLimit(1, 'second/third', root, callable=third.get_path)
		self.assertQueryLimit(1, e, third, callable=second2.get_path)
		self.assertQueryLimit(1, '? - ?', root, ' - ', 'title', callable=third.get_path)
