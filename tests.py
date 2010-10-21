from django.test import TestCase
from django import template
from django.conf import settings
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
		
		self.templates = [template.Template(string) for string in
			[
				"{% node_url %}", # 0
				"{% node_url for node2 %}", # 1
				"{% node_url as hello %}<p>{{ hello|slice:'1:' }}</p>", # 2
				"{% node_url for nodes|first %}", # 3
				"{% node_url with entry %}", # 4
				"{% node_url with entry for node2 %}", # 5
				"{% node_url with tag for node2 %}", # 6
				"{% node_url with date for node2 %}", # 7
				"{% node_url entries_by_day year=date|date:'Y' month=date|date:'m' day=date|date:'d' for node2 as goodbye %}<em>{{ goodbye|upper }}</em>", # 8
				"{% node_url entries_by_month year=date|date:'Y' month=date|date:'m' for node2 %}", # 9
				"{% node_url entries_by_year year=date|date:'Y' for node2 %}", # 10
			]
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
		for i, template in enumerate(self.templates):
			t = template.render(self.context)
			
			if i == 0:
				self.assertEqual(t, "/root/never/")
			elif i == 1:
				self.assertEqual(t, "/root/blog/")
			elif i == 2:
				self.assertEqual(t, "<p>root/never/</p>")
			elif i == 3:
				self.assertEqual(t, "/root/never/")
			elif i == 4:
				self.assertEqual(t, settings.TEMPLATE_STRING_IF_INVALID)
			elif i == 5:
				self.assertEqual(t, "/root/blog/2010/10/20/first-entry")
			elif i == 6:
				self.assertEqual(t, "/root/blog/tags/test-tag/")
			elif i == 7:
				self.assertEqual(t, "/root/blog/2010/10/20")
			elif i == 8:
				self.assertEqual(t, "<em>/ROOT/BLOG/2010/10/20</em>")
			elif i == 9:
				self.assertEqual(t, "/root/blog/2010/10")
			elif i == 10:
				self.assertEqual(t, "/root/blog/2010/")
			else:
				print "Rendered as:\n%s\n\n" % t