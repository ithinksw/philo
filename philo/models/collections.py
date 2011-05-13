from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from philo.models.base import value_content_type_limiter, register_value_model
from philo.utils import fattr


__all__ = ('Collection', 'CollectionMember')


class Collection(models.Model):
	"""
	Collections are curated ordered groupings of arbitrary models.
	
	"""
	#: :class:`CharField` with max_length 255
	name = models.CharField(max_length=255)
	#: Optional :class:`TextField`
	description = models.TextField(blank=True, null=True)
	
	@fattr(short_description='Members')
	def get_count(self):
		"""Returns the number of items in the collection."""
		return self.members.count()
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class CollectionMemberManager(models.Manager):
	use_for_related_fields = True

	def with_model(self, model):
		"""
		Given a model class or instance, returns a queryset of all instances of that model which have collection members in this manager's scope.
		
		Example::
		
			>>> from philo.models import Collection
			>>> from django.contrib.auth.models import User
			>>> collection = Collection.objects.get(name="Foo")
			>>> collection.members.all()
			[<CollectionMember: Foo - user1>, <CollectionMember: Foo - user2>, <CollectionMember: Foo - Spam & Eggs>]
			>>> collection.members.with_model(User)
			[<User: user1>, <User: user2>]
		
		"""
		return model._default_manager.filter(pk__in=self.filter(member_content_type=ContentType.objects.get_for_model(model)).values_list('member_object_id', flat=True))


class CollectionMember(models.Model):
	"""
	The collection member model represents a generic link from a :class:`Collection` to an arbitrary model instance with an attached order.
	
	"""
	#: A :class:`CollectionMemberManager` instance
	objects = CollectionMemberManager()
	#: :class:`ForeignKey` to a :class:`Collection` instance.
	collection = models.ForeignKey(Collection, related_name='members')
	#: The numerical index of the item within the collection (optional).
	index = models.PositiveIntegerField(verbose_name='Index', help_text='This will determine the ordering of the item within the collection. (Optional)', null=True, blank=True)
	member_content_type = models.ForeignKey(ContentType, limit_choices_to=value_content_type_limiter, verbose_name='Member type')
	member_object_id = models.PositiveIntegerField(verbose_name='Member ID')
	#: :class:`GenericForeignKey` to an arbitrary model instance.
	member = generic.GenericForeignKey('member_content_type', 'member_object_id')
	
	def __unicode__(self):
		return u'%s - %s' % (self.collection, self.member)
	
	class Meta:
		app_label = 'philo'


register_value_model(Collection)