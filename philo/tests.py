import sys
import traceback

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.template import loader
from django.template.loaders import cached
from django.test import TestCase
from django.test.utils import setup_test_template_loader, restore_template_loaders
from django.utils.datastructures import SortedDict

from philo.exceptions import AncestorDoesNotExist
from philo.models import Node, Page, Template, Tag


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
		restore_template_loaders()
		
		self.assertEqual(failures, [], "Tests failed:\n%s\n%s" % ('-'*70, ("\n%s\n" % ('-'*70)).join(failures)))
	
	
	def get_template_tests(self):
		# SYNTAX --
		# 'template_name': ('template contents', 'context dict', 'expected string output' or Exception class)
		embedded = Tag.objects.get(pk=1)
		return {
			# EMBED INCLUSION HANDLING
			
			'embed01': ('{{ embedded.name|safe }}', {'embedded': embedded}, embedded.name),
			'embed02': ('{{ embedded.name|safe }}{{ var1 }}{{ var2 }}', {'embedded': embedded}, embedded.name),
			'embed03': ('{{ embedded.name|safe }} is a lie!', {'embedded': embedded}, '%s is a lie!' % embedded.name),
			
			# Simple template structure with embed
			'simple01': ('{% embed philo.tag with "embed01" %}{% embed philo.tag 1 %}Simple{% block one %}{% endblock %}', {'embedded': embedded}, '%sSimple' % embedded.name),
			'simple02': ('{% extends "simple01" %}', {}, '%sSimple' % embedded.name),
			'simple03': ('{% embed philo.tag with "embed000" %}', {}, settings.TEMPLATE_STRING_IF_INVALID),
			'simple04': ('{% embed philo.tag 1 %}', {}, settings.TEMPLATE_STRING_IF_INVALID),
			'simple05': ('{% embed philo.tag with "embed01" %}{% embed embedded %}', {'embedded': embedded}, embedded.name),
			
			# Kwargs
			'kwargs01': ('{% embed philo.tag with "embed02" %}{% embed philo.tag 1 var1="hi" var2=lo %}', {'lo': 'lo'}, '%shilo' % embedded.name),
			
			# Filters/variables
			'filters01': ('{% embed philo.tag with "embed02" %}{% embed philo.tag 1 var1=hi|first var2=lo|slice:"3" %}', {'hi': ["These", "words"], 'lo': 'lower'}, '%sTheselow' % embedded.name),
			'filters02': ('{% embed philo.tag with "embed01" %}{% embed philo.tag entry %}', {'entry': 1}, embedded.name),
			
			# Blocky structure
			'block01': ('{% block one %}Hello{% endblock %}', {}, 'Hello'),
			'block02': ('{% extends "simple01" %}{% block one %}{% embed philo.tag 1 %}{% endblock %}', {}, "%sSimple%s" % (embedded.name, embedded.name)),
			'block03': ('{% extends "simple01" %}{% embed philo.tag with "embed03" %}{% block one %}{% embed philo.tag 1 %}{% endblock %}', {}, "%sSimple%s is a lie!" % (embedded.name, embedded.name)),
			
			# Blocks and includes
			'block-include01': ('{% extends "simple01" %}{% embed philo.tag with "embed03" %}{% block one %}{% include "simple01" %}{% embed philo.tag 1 %}{% endblock %}', {}, "%sSimple%sSimple%s is a lie!" % (embedded.name, embedded.name, embedded.name)),
			'block-include02': ('{% extends "simple01" %}{% block one %}{% include "simple04" %}{% embed philo.tag with "embed03" %}{% include "simple04" %}{% embed philo.tag 1 %}{% endblock %}', {}, "%sSimple%s%s is a lie!%s is a lie!" % (embedded.name, embedded.name, embedded.name, embedded.name)),
			
			# Tests for more complex situations...
			'complex01': ('{% block one %}{% endblock %}complex{% block two %}{% endblock %}', {}, 'complex'),
			'complex02': ('{% extends "complex01" %}', {}, 'complex'),
			'complex03': ('{% extends "complex02" %}{% embed philo.tag with "embed01" %}', {}, 'complex'),
			'complex04': ('{% extends "complex03" %}{% block one %}{% embed philo.tag 1 %}{% endblock %}', {}, '%scomplex' % embedded.name),
			'complex05': ('{% extends "complex03" %}{% block one %}{% include "simple04" %}{% endblock %}', {}, '%scomplex' % embedded.name),
		}


class NodeURLTestCase(TestCase):
	"""Tests the features of the node_url template tag."""
	urls = 'philo.urls'
	fixtures = ['test_fixtures.json']
	
	def setUp(self):
		self.templates = [
				("{% node_url %}", "/root/second"),
				("{% node_url for node2 %}", "/root/second2"),
				("{% node_url as hello %}<p>{{ hello|slice:'1:' }}</p>", "<p>root/second</p>"),
				("{% node_url for nodes|first %}", "/root"),
		]
		
		nodes = Node.objects.all()
		
		self.context = template.Context({
			'node': nodes.get(slug='second'),
			'node2': nodes.get(slug='second2'),
			'nodes': nodes,
		})
	
	def test_nodeurl(self):
		for string, result in self.templates:
			self.assertEqual(template.Template(string).render(self.context), result)

class TreePathTestCase(TestCase):
	urls = 'philo.urls'
	fixtures = ['test_fixtures.json']
	
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
		self.assertQueryLimit(3, (second2, 'sub'), 'root/second2/sub/', absolute_result=False)
		self.assertQueryLimit(2, e, 'invalid/path/1/2/3/4/5/6/7/8/9/1/2/3/4/5/6/7/8/9/0', absolute_result=False)
		self.assertQueryLimit(1, (root, None), 'root', absolute_result=False)
		self.assertQueryLimit(2, (second2, None), 'root/second2', absolute_result=False)
		self.assertQueryLimit(3, (third, None), 'root/second/third', absolute_result=False)
		
		# with root != None
		self.assertQueryLimit(1, (second2, None), 'second2', root=root, absolute_result=False)
		self.assertQueryLimit(2, (third, None), 'second/third', root=root, absolute_result=False)
		
		# Eliminate trailing slash
		self.assertQueryLimit(2, (second2, 'sub/path/tail'), 'root/second2/sub/path/tail/', absolute_result=False)
		
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


class ContainerTestCase(TestCase):
	def test_simple_containers(self):
		t = Template(code="{% container one %}{% container two %}{% container three %}{% container two %}")
		contentlet_specs, contentreference_specs = t.containers
		self.assertEqual(len(contentreference_specs.keyOrder), 0)
		self.assertEqual(contentlet_specs, ['one', 'two', 'three'])
		
		ct = ContentType.objects.get_for_model(Tag)
		t = Template(code="{% container one references philo.tag as tag1 %}{% container two references philo.tag as tag2 %}{% container one references philo.tag as tag1 %}")
		contentlet_specs, contentreference_specs = t.containers
		self.assertEqual(len(contentlet_specs), 0)
		self.assertEqual(contentreference_specs, SortedDict([('one', ct), ('two', ct)]))
