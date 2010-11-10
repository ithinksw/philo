from django.test import TestCase
from django import template
from django.conf import settings
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