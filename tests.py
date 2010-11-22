from django.test import TestCase
from django import template
from django.conf import settings
from django.db import connection
from philo.exceptions import AncestorDoesNotExist
from philo.models import Node, Page, Template
from philo.contrib.penfield.models import Blog, BlogView, BlogEntry


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