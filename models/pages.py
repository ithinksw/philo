# encoding: utf-8
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.conf import settings
from django.template import add_to_builtins as register_templatetags
from django.template import Template as DjangoTemplate
from django.template import TemplateDoesNotExist
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.template.loader_tags import ExtendsNode, ConstantIncludeNode, IncludeNode
from django.http import HttpResponse
from philo.models.base import TreeModel, register_value_model
from philo.models.nodes import View
from philo.utils import fattr
from philo.templatetags.containers import ContainerNode


class Template(TreeModel):
	name = models.CharField(max_length=255)
	documentation = models.TextField(null=True, blank=True)
	mimetype = models.CharField(max_length=255, null=True, blank=True, help_text='Default: %s' % settings.DEFAULT_CONTENT_TYPE)
	code = models.TextField(verbose_name='django template code')
	
	@property
	def origin(self):
		return 'philo.models.Template: ' + self.path
	
	@property
	def django_template(self):
		return DjangoTemplate(self.code)
	
	@property
	def containers(self):
		"""
		Returns a tuple where the first item is a list of names of contentlets referenced by containers,
		and the second item is a list of tuples of names and contenttypes of contentreferences referenced by containers.
		This will break if there is a recursive extends or includes in the template code.
		Due to the use of an empty Context, any extends or include tags with dynamic arguments probably won't work.
		"""
		def container_nodes(template):
			def nodelist_container_nodes(nodelist):
				nodes = []
				for node in nodelist:
					try:
						if hasattr(node, 'child_nodelists'):
							for nodelist_name in node.child_nodelists:
								if hasattr(node, nodelist_name):
									nodes.extend(nodelist_container_nodes(getattr(node, nodelist_name)))
						if isinstance(node, ContainerNode):
							nodes.append(node)
						elif isinstance(node, ExtendsNode):
							extended_template = node.get_parent(Context())
							if extended_template:
								nodes.extend(container_nodes(extended_template))
						elif isinstance(node, ConstantIncludeNode):
							included_template = node.template
							if included_template:
								nodes.extend(container_nodes(included_template))
						elif isinstance(node, IncludeNode):
							included_template = get_template(node.template_name.resolve(Context()))
							if included_template:
								nodes.extend(container_nodes(included_template))
					except:
						raise # fail for this node
				return nodes
			return nodelist_container_nodes(template.nodelist)
		all_nodes = container_nodes(self.django_template)
		contentlet_node_names = set([node.name for node in all_nodes if not node.references])
		contentreference_node_names = []
		contentreference_node_specs = []
		for node in all_nodes:
			if node.references and node.name not in contentreference_node_names:
				contentreference_node_specs.append((node.name, node.references))
				contentreference_node_names.append(node.name)
		return contentlet_node_names, contentreference_node_specs
	
	def __unicode__(self):
		return self.get_path(u' › ', 'name')
	
	@staticmethod
	@fattr(is_usable=True)
	def loader(template_name, template_dirs=None): # load_template_source
		try:
			template = Template.objects.get_with_path(template_name)
		except Template.DoesNotExist:
			raise TemplateDoesNotExist(template_name)
		return (template.code, template.origin)
	
	class Meta:
		app_label = 'philo'


class Page(View):
	"""
	Represents a page - something which is rendered according to a template. The page will have a number of related Contentlets depending on the template selected - but these will appear only after the page has been saved with that template.
	"""
	template = models.ForeignKey(Template, related_name='pages')
	title = models.CharField(max_length=255)
	
	def render_to_response(self, node, request, path=None, subpath=None, extra_context=None):
		context = {}
		context.update(extra_context or {})
		context.update({'page': self, 'attributes': self.attributes_with_node(node), 'relationships': self.relationships_with_node(node)})
		return HttpResponse(self.template.django_template.render(RequestContext(request, context)), mimetype=self.template.mimetype)
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		app_label = 'philo'


class Contentlet(models.Model):
	page = models.ForeignKey(Page, related_name='contentlets')
	name = models.CharField(max_length=255)
	content = models.TextField()
	dynamic = models.BooleanField(default=False)
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class ContentReference(models.Model):
	page = models.ForeignKey(Page, related_name='contentreferences')
	name = models.CharField(max_length=255)
	content_type = models.ForeignKey(ContentType, verbose_name='Content type')
	content_id = models.PositiveIntegerField(verbose_name='Content ID', blank=True, null=True)
	content = generic.GenericForeignKey('content_type', 'content_id')
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


register_templatetags('philo.templatetags.containers')


register_value_model(Template)
register_value_model(Page)