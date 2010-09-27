from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.template import Template, loader, loader_tags
import re
from philo.contrib.penfield.templatetags.embed import EmbedNode


embed_re = re.compile("{% embed (?P<app_label>\w+)\.(?P<model>\w+) (?P<pk>)\w+ %}")


class TemplateField(models.TextField):
	def validate(self, value, model_instance):
		"""For value (a template), make sure that all included templates exist."""
		super(TemplateField, self).validate(value, model_instance)
		try:
			self.validate_template(self.to_template(value))
		except Exception, e:
			raise ValidationError("Template code invalid. Error was: %s: %s" % (e.__class__.__name__, e))
	
	def validate_template(self, template):
		for node in template.nodelist:
			if isinstance(node, loader_tags.ExtendsNode):
				extended_template = node.get_parent(Context())
				self.validate_template(extended_template)
			elif isinstance(node, loader_tags.IncludeNode):
				included_template = loader.get_template(node.template_name.resolve(Context()))
				self.validate_template(extended_template)
	
	def to_template(self, value):
		return Template(value)


class EmbedField(TemplateField):
	def validate_template(self, template):
		"""Check to be sure that the embedded instances and templates all exist."""
		for node in template.nodelist:
			if isinstance(node, loader_tags.ExtendsNode):
				extended_template = node.get_parent(Context())
				self.validate_template(extended_template)
			elif isinstance(node, loader_tags.IncludeNode):
				included_template = loader.get_template(node.template_name.resolve(Context()))
				self.validate_template(extended_template)
			elif isinstance(node, EmbedNode):
				if node.template_name is not None:
					embedded_template = loader.get_template(node.template_name)
					self.validate_template(embedded_template)
				elif node.object_pk is not None:
					embedded_instance = node.model.objects.get(pk=node.object_pk)
	
	def to_template(self, value):
		return Template("{% load embed %}" + value)


class Embed(models.Model):
	embedder_embed_field = models.CharField(max_length=255)
	
	embedder_contenttype = models.ForeignKey(ContentType, related_name="embedder_related")
	embedder_object_id = models.PositiveIntegerField()
	embedder = generic.GenericForeignKey("embedder_contenttype", "embedder_object_id")
	
	embedded_contenttype = models.ForeignKey(ContentType, related_name="embedded_related")
	embedded_object_id = models.PositiveIntegerField()
	embedded = generic.GenericForeignKey("embedded_contenttype", "embedded_object_id")
	
	def delete(self):
		# Unclear whether this would be called by a cascading deletion.
		
		super(Embed, self).delete()
	
	class Meta:
		app_label = 'penfield'


class Test(models.Model):
	template = TemplateField()
	embedder = EmbedField()
	
	class Meta:
		app_label = 'penfield'