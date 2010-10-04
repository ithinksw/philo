from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.template import loader, loader_tags, Parser, Lexer, Template
import re
from philo.models.fields import TemplateField
from philo.contrib.penfield.templatetags.embed import EmbedNode
from philo.utils import nodelist_crawl, ContentTypeRegistryLimiter


embeddable_content_types = ContentTypeRegistryLimiter()


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
				setattr(embedder, field.attname, self.embed_re.sub('', attr))
		
		embedder.save()
	
	def get_embed_re(self):
		"""Convenience function to return a compiled regular expression to find embed tags that would create this instance."""
		if not hasattr(self, '_embed_re'):
			ct = self.embedded_content_type
		 	self._embed_re = re.compile("{%% ?embed %s.%s %s( .*?)? ?%%}" % (ct.app_label, ct.model, self.embedded_object_id))
		return self._embed_re
	embed_re = property(get_embed_re)
	
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
	def process_node(self, node, results):
		if isinstance(node, EmbedNode) and node.instance is not None:
			if node.content_type.model_class() not in embeddable_content_types.classes:
				raise ValidationError("Class %s.%s cannot be embedded." % (node.content_type.app_label, node.content_type.model))
			
			if not node.instance:
				raise ValidationError("Instance with content type %s.%s and id %s does not exist." % (node.content_type.app_label, node.content_type.model, node.object_pk))
			
			results.append(node.instance)
	
	def clean(self, value, model_instance):
		value = super(EmbedField, self).clean(value, model_instance)
		
		if not hasattr(model_instance, '_embedded_instances'):
			model_instance._embedded_instances = set()
		
		model_instance._embedded_instances |= set(nodelist_crawl(Template(value).nodelist, self.process_node))
		
		return value


try:
	from south.modelsinspector import add_introspection_rules
except ImportError:
	pass
else:
	add_introspection_rules([], ["^philo\.contrib\.penfield\.embed\.EmbedField"])


# Add a post-save signal function to run the syncer.
def post_save_embed_sync(sender, instance, **kwargs):
	if hasattr(instance, '_embedded_instances') and instance._embedded_instances:
		sync_embedded_instances(instance, instance._embedded_instances)
models.signals.post_save.connect(post_save_embed_sync)


# Deletions can't cascade automatically without a GenericRelation - but there's no good way of
# knowing what models should have one. Anything can be embedded! Also, cascading would probably
# bypass the Embed model's delete method.
def post_delete_cascade(sender, instance, **kwargs):
	if sender in embeddable_content_types.classes:
		# Don't bother looking for Embed objects that embed a contenttype that can't be embedded.
		ct = ContentType.objects.get_for_model(sender)
		embeds = Embed.objects.filter(embedded_content_type=ct, embedded_object_id=instance.id)
		for embed in embeds:
			embed.delete()
	
	if not hasattr(sender._meta, '_has_embed_fields'):
		sender._meta._has_embed_fields = False
		for field in sender._meta.fields:
			if isinstance(field, EmbedField):
				sender._meta._has_embed_fields = True
				break
	
	if sender._meta._has_embed_fields:
		# If it doesn't have embed fields, then it can't be an embedder.
		Embed.objects.filter(embedder_content_type=ct, embedder_object_id=instance.id).delete()
models.signals.post_delete.connect(post_delete_cascade)