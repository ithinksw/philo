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


class Embed(models.Model):
	embedder_content_type = models.ForeignKey(ContentType, related_name="embedder_related")
	embedder_object_id = models.PositiveIntegerField()
	embedder = generic.GenericForeignKey("embedder_content_type", "embedder_object_id")
	
	embedded_content_type = models.ForeignKey(ContentType, related_name="embedded_related")
	embedded_object_id = models.PositiveIntegerField()
	embedded = generic.GenericForeignKey("embedded_content_type", "embedded_object_id")
	
	def delete(self):
		# This needs to be called manually.
		super(Embed, self).delete()
		
		# Cycle through all the fields in the embedder and remove all references
		# to the embedded object.
		embedder = self.embedder
		for field in embedder._meta.fields:
			if isinstance(field, EmbedField):
				attr = getattr(embedder, field.attname)
				setattr(embedder, field.attname, attr.replace(self.get_embed_tag(), ''))
		
		embedder.save()
	
	def get_embed_tag(self):
		"""Convenience function to construct the embed tag that would create this instance."""
		ct = self.embedded_content_type
		return "{%% embed %s.%s %s %%}" % (ct.app_label, ct.model, self.embedded_object_id)
	
	class Meta:
		app_label = 'penfield'


def sync_embedded_instances(model_instance, embedded_instances):
	model_instance_ct = ContentType.objects.get_for_model(model_instance)
	
	# Cycle through all the embedded instances and make sure that they are linked to
	# the model instance. Track their pks.
	new_embed_pks = []
	for embedded_instance in embedded_instances:
		embedded_instance_ct = ContentType.objects.get_for_model(embedded_instance)
		new_embed = Embed.objects.get_or_create(embedder_content_type=model_instance_ct, embedder_object_id=model_instance.id, embedded_content_type=embedded_instance_ct, embedded_object_id=embedded_instance.id)[0]
		new_embed_pks.append(new_embed.pk)
	
	# Then, delete all embed objects related to this model instance which do not relate
	# to one of the newly embedded instances.
	Embed.objects.filter(embedder_content_type=model_instance_ct, embedder_object_id=model_instance.id).exclude(pk__in=new_embed_pks).delete()


class EmbedField(TemplateField):
	_embedded_instances = set()
	
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
					self._embedded_instances.add(node.model.objects.get(pk=node.object_pk))
	
	def pre_save(self, model_instance, add):
		if not hasattr(model_instance, '_embedded_instances'):
			model_instance._embedded_instances = set()
		model_instance._embedded_instances |= self._embedded_instances
		return getattr(model_instance, self.attname)


# Add a post-save signal function to run the syncer.
def post_save_embed_sync(sender, instance, **kwargs):
	if hasattr(instance, '_embedded_instances') and instance._embedded_instances:
		sync_embedded_instances(instance, instance._embedded_instances)
models.signals.post_save.connect(post_save_embed_sync)


# Deletions can't cascade automatically without a GenericRelation - but there's no good way of
# knowing what models should have one. Anything can be embedded! Also, cascading would probably
# bypass the Embed model's delete method.
def post_delete_cascade(sender, instance, **kwargs):
	ct = ContentType.objects.get_for_model(sender)
	embeds = Embed.objects.filter(embedded_content_type=ct, embedded_object_id=instance.id)
	for embed in embeds:
		embed.delete()
	Embed.objects.filter(embedder_content_type=ct, embedder_object_id=instance.id).delete()
models.signals.post_delete.connect(post_delete_cascade)


class Test(models.Model):
	template = TemplateField()
	embedder = EmbedField()
	
	class Meta:
		app_label = 'penfield'