from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from philo.models.base import value_content_type_limiter, register_value_model
from philo.utils import fattr
from django.template import add_to_builtins as register_templatetags


class Collection(models.Model):
	name = models.CharField(max_length=255)
	description = models.TextField(blank=True, null=True)
	
	@fattr(short_description='Members')
	def get_count(self):
		return self.members.count()
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class CollectionMemberManager(models.Manager):
	use_for_related_fields = True

	def with_model(self, model):
		return model._default_manager.filter(pk__in=self.filter(member_content_type=ContentType.objects.get_for_model(model)).values_list('member_object_id', flat=True))


class CollectionMember(models.Model):
	objects = CollectionMemberManager()
	collection = models.ForeignKey(Collection, related_name='members')
	index = models.PositiveIntegerField(verbose_name='Index', help_text='This will determine the ordering of the item within the collection. (Optional)', null=True, blank=True)
	member_content_type = models.ForeignKey(ContentType, limit_choices_to=value_content_type_limiter, verbose_name='Member type')
	member_object_id = models.PositiveIntegerField(verbose_name='Member ID')
	member = generic.GenericForeignKey('member_content_type', 'member_object_id')
	
	def __unicode__(self):
		return u'%s - %s' % (self.collection, self.member)
	
	class Meta:
		app_label = 'philo'


register_templatetags('philo.templatetags.collections')
register_value_model(Collection)