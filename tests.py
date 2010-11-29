from django.test import TestCase
from django import template
from django.conf import settings
from django.template import loader
from django.template.loaders import cached
from philo.exceptions import AncestorDoesNotExist
from philo.models import Node, Page, Template
from philo.contrib.penfield.models import Blog, BlogView, BlogEntry
import sys, traceback


class TemplateTestCase(TestCase):
	fixtures = ['test_fixtures.json']
	
	def test_templates(self):
		"Tests to make sure that embed behaves with complex includes and extends"
		template_tests = self.get_template_tests()
		
		# Register our custom template loader. Shamelessly cribbed from django core regressiontests.
		def test_template_loader(template_name, template_dirs=None):
			"A custom template loader that loads the unit-test templates."
			try:
				return (template_tests[template_name][0] , "test:%s" % template_name)
			except KeyError:
				raise template.TemplateDoesNotExist, template_name
		
		cache_loader = cached.Loader(('test_template_loader',))
		cache_loader._cached_loaders = (test_template_loader,)
		
		old_template_loaders = loader.template_source_loaders
		loader.template_source_loaders = [cache_loader]
		
		# Turn TEMPLATE_DEBUG off, because tests assume that.
		old_td, settings.TEMPLATE_DEBUG = settings.TEMPLATE_DEBUG, False
		
		# Set TEMPLATE_STRING_IF_INVALID to a known string.
		old_invalid = settings.TEMPLATE_STRING_IF_INVALID
		expected_invalid_str = 'INVALID'
		
		failures = []
		
		# Run tests
		for name, vals in template_tests.items():
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
				("{% node_url %}", "/root/never/"),
				("{% node_url for node2 %}", "/root/blog/"),
				("{% node_url as hello %}<p>{{ hello|slice:'1:' }}</p>", "<p>root/never/</p>"),
				("{% node_url for nodes|first %}", "/root/never/"),
				("{% node_url with entry %}", settings.TEMPLATE_STRING_IF_INVALID),
				("{% node_url with entry for node2 %}", "/root/blog/2010/10/20/first-entry"),
				("{% node_url with tag for node2 %}", "/root/blog/tags/test-tag/"),
				("{% node_url with date for node2 %}", "/root/blog/2010/10/20"),
				("{% node_url entries_by_day year=date|date:'Y' month=date|date:'m' day=date|date:'d' for node2 as goodbye %}<em>{{ goodbye|upper }}</em>", "<em>/ROOT/BLOG/2010/10/20</em>"),
				("{% node_url entries_by_month year=date|date:'Y' month=date|date:'m' for node2 %}", "/root/blog/2010/10"),
				("{% node_url entries_by_year year=date|date:'Y' for node2 %}", "/root/blog/2010/"),
		]
		
		nodes = Node.objects.all()
		blog = Blog.objects.all()[0]
		
		self.context = template.Context({
			'node': nodes[0],
			'node2': nodes[1],
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
	
	def test_has_ancestor(self):
		root = Node.objects.get(slug='root')
		third = Node.objects.get(slug='third')
		r1 = Node.objects.get(slug='recursive1')
		r2 = Node.objects.get(slug='recursive2')
		pr1 = Node.objects.get(slug='postrecursive1')
		
		# Simple case: straight path
		self.assertEqual(third.has_ancestor(root), True)
		self.assertEqual(root.has_ancestor(root), False)
		self.assertEqual(root.has_ancestor(None), True)
		self.assertEqual(third.has_ancestor(None), True)
		self.assertEqual(root.has_ancestor(root, inclusive=True), True)
		
		# Recursive case
		self.assertEqual(r1.has_ancestor(r1), True)
		self.assertEqual(r1.has_ancestor(r2), True)
		self.assertEqual(r2.has_ancestor(r1), True)
		self.assertEqual(r2.has_ancestor(None), False)
		
		# Post-recursive case
		self.assertEqual(pr1.has_ancestor(r1), True)
		self.assertEqual(pr1.has_ancestor(pr1), False)
		self.assertEqual(pr1.has_ancestor(pr1, inclusive=True), True)
		self.assertEqual(pr1.has_ancestor(None), False)
		self.assertEqual(pr1.has_ancestor(root), False)
	
	def test_get_path(self):
		root = Node.objects.get(slug='root')
		third = Node.objects.get(slug='third')
		r1 = Node.objects.get(slug='recursive1')
		r2 = Node.objects.get(slug='recursive2')
		pr1 = Node.objects.get(slug='postrecursive1')
		
		# Simple case: straight path to None
		self.assertEqual(root.get_path(), 'root')
		self.assertEqual(third.get_path(), 'root/never/more/second/third')
		
		# Recursive case: Looped path to root None
		self.assertEqual(r1.get_path(), u'\u2026/recursive1/recursive2/recursive3/recursive1')
		self.assertEqual(pr1.get_path(), u'\u2026/recursive3/recursive1/recursive2/recursive3/postrecursive1')
		
		# Simple error case: straight invalid path
		self.assertRaises(AncestorDoesNotExist, root.get_path, root=third)
		self.assertRaises(AncestorDoesNotExist, third.get_path, root=pr1)
		
		# Recursive error case
		self.assertRaises(AncestorDoesNotExist, r1.get_path, root=root)
		self.assertRaises(AncestorDoesNotExist, pr1.get_path, root=third)