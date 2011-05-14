#encoding: utf-8
from UserDict import DictMixin

from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.forms.models import model_to_dict

from philo.models.base import TreeEntity, TreeManager, Entity
from philo.models.nodes import Node, TargetURLModel


DEFAULT_NAVIGATION_DEPTH = 3


class NavigationQuerySetMapper(object, DictMixin):
	"""This class exists to prevent setting of items in the navigation cache through node.navigation."""
	def __init__(self, node):
		self.node = node
	
	def __getitem__(self, key):
		return Navigation.objects.get_cache_for(self.node)[key]['root_items']
	
	def keys(self):
		return Navigation.objects.get_cache_for(self.node).keys()


def navigation(self):
	if not hasattr(self, '_navigation'):
		self._navigation = NavigationQuerySetMapper(self)
	return self._navigation


Node.navigation = property(navigation)


class NavigationCacheQuerySet(models.query.QuerySet):
	"""
	This subclass will trigger general cache clearing for Navigation.objects when a mass
	update or deletion is performed. As there is no convenient way to iterate over the
	changed or deleted instances, there's no way to be more precise about what gets cleared.
	"""
	def update(self, *args, **kwargs):
		super(NavigationCacheQuerySet, self).update(*args, **kwargs)
		Navigation.objects.clear_cache()
	
	def delete(self, *args, **kwargs):
		super(NavigationCacheQuerySet, self).delete(*args, **kwargs)
		Navigation.objects.clear_cache()


class NavigationManager(models.Manager):
	# Since navigation is going to be hit frequently and changed
	# relatively infrequently, cache it. Analogous to contenttypes.
	use_for_related = True
	_cache = {}
	
	def get_queryset(self):
		return NavigationCacheQuerySet(self.model, using=self._db)
	
	def get_cache_for(self, node, update_targets=True):
		created = False
		if not self.has_cache_for(node):
			self.create_cache_for(node)
			created = True
		
		if update_targets and not created:
			self.update_targets_for(node)
		
		return self.__class__._cache[self.db][node]
	
	def has_cache_for(self, node):
		return self.db in self.__class__._cache and node in self.__class__._cache[self.db]
	
	def create_cache_for(self, node):
		"This method loops through the nodes ancestors and caches all unique navigation keys."
		ancestors = node.get_ancestors(ascending=True, include_self=True)
		
		nodes_to_cache = []
		
		for node in ancestors:
			if self.has_cache_for(node):
				cache = self.get_cache_for(node).copy()
				break
			else:
				nodes_to_cache.insert(0, node)
		else:
			cache = {}
		
		for node in nodes_to_cache:
			cache = cache.copy()
			cache.update(self._build_cache_for(node))
			self.__class__._cache.setdefault(self.db, {})[node] = cache
	
	def _build_cache_for(self, node):
		cache = {}
		tree_id_attr = NavigationItem._mptt_meta.tree_id_attr
		level_attr = NavigationItem._mptt_meta.level_attr
		
		for navigation in node.navigation_set.all():
			tree_ids = navigation.roots.values_list(tree_id_attr)
			items = list(NavigationItem.objects.filter(**{'%s__in' % tree_id_attr: tree_ids, '%s__lt' % level_attr: navigation.depth}).order_by('order', 'lft'))
			
			root_items = []
			
			for item in items:
				item._is_cached = True
				
				if not hasattr(item, '_cached_children'):
					item._cached_children = []
				
				if item.parent:
					# alternatively, if I don't want to force it to a list, I could keep track of
					# instances where the parent hasn't yet been met and do this step later for them.
					# delayed action.
					item.parent = items[items.index(item.parent)]
					if not hasattr(item.parent, '_cached_children'):
						item.parent._cached_children = []
					item.parent._cached_children.append(item)
				else:
					root_items.append(item)
			
			cache[navigation.key] = {
				'navigation': navigation,
				'root_items': root_items,
				'items': items
			}
		
		return cache
	
	def clear_cache_for(self, node):
		# Clear the cache for this node and all its descendants. The
		# navigation for this node has probably changed, and for now,
		# it isn't worth it to only clear the descendants actually
		# affected by this.
		if not self.has_cache_for(node):
			# Already cleared.
			return
		
		descendants = node.get_descendants(include_self=True)
		cache = self.__class__._cache[self.db]
		for node in descendants:
			cache.pop(node, None)
	
	def update_targets_for(self, node):
		# Manually update a cache's target nodes in case something's changed there.
		# This should be a less complex operation than reloading the models each
		# time. Not as good as selective updates... but not much to be done
		# about that. TODO: Benchmark it.
		caches = self.__class__._cache[self.db][node].values()
		
		target_pks = set()
		
		for cache in caches:
			target_pks |= set([item.target_node_id for item in cache['items']])
		
		# A distinct query is not strictly necessary. TODO: benchmark the efficiency
		# with/without distinct.
		targets = list(Node.objects.filter(pk__in=target_pks).distinct())
		
		for cache in caches:
			for item in cache['items']:
				if item.target_node_id:
					item.target_node = targets[targets.index(item.target_node)]
	
	def clear_cache(self):
		self.__class__._cache.pop(self.db, None)


class Navigation(Entity):
	objects = NavigationManager()
	
	node = models.ForeignKey(Node, related_name='navigation_set', help_text="Be available as navigation for this node.")
	key = models.CharField(max_length=255, validators=[RegexValidator("\w+")], help_text="Must contain one or more alphanumeric characters or underscores.", db_index=True)
	depth = models.PositiveSmallIntegerField(default=DEFAULT_NAVIGATION_DEPTH, validators=[MinValueValidator(1)], help_text="Defines the maximum display depth of this navigation.")
	
	def __init__(self, *args, **kwargs):
		super(Navigation, self).__init__(*args, **kwargs)
		self._initial_data = model_to_dict(self)
	
	def __unicode__(self):
		return "%s[%s]" % (self.node, self.key)
	
	def _has_changed(self):
		return self._initial_data != model_to_dict(self)
	
	def save(self, *args, **kwargs):
		super(Navigation, self).save(*args, **kwargs)
		
		if self._has_changed():
			Navigation.objects.clear_cache_for(self.node)
			self._initial_data = model_to_dict(self)
	
	def delete(self, *args, **kwargs):
		super(Navigation, self).delete(*args, **kwargs)
		Navigation.objects.clear_cache_for(self.node)
	
	class Meta:
		unique_together = ('node', 'key')


class NavigationItemManager(TreeManager):
	use_for_related = True
	
	def get_queryset(self):
		return NavigationCacheQuerySet(self.model, using=self._db)


class NavigationItem(TreeEntity, TargetURLModel):
	objects = NavigationItemManager()
	
	navigation = models.ForeignKey(Navigation, blank=True, null=True, related_name='roots', help_text="Be a root in this navigation tree.")
	text = models.CharField(max_length=50)
	
	order = models.PositiveSmallIntegerField(default=0)
	
	def __init__(self, *args, **kwargs):
		super(NavigationItem, self).__init__(*args, **kwargs)
		self._initial_data = model_to_dict(self)
		self._is_cached = False
	
	def __unicode__(self):
		return self.get_path(field='text', pathsep=u' › ')
	
	def clean(self):
		super(NavigationItem, self).clean()
		if bool(self.parent) == bool(self.navigation):
			raise ValidationError("Exactly one of `parent` and `navigation` must be defined.")
	
	def is_active(self, request):
		if self.target_url == request.path:
			# Handle the `default` case where the target_url and requested path
			# are identical.
			return True
		
		if self.target_node is None and self.url_or_subpath == "http%s://%s%s" % (request.is_secure() and 's' or '', request.get_host(), request.path):
			# If there's no target_node, double-check whether it's a full-url
			# match.
			return True
		
		if self.target_node and not self.url_or_subpath:
			# If there is a target node and it's targeted simply, but the target URL is not
			# the same as the request path, check whether the target node is an ancestor
			# of the requested node. If so, this is active unless the target node
			# is the same as the ``host node`` for this navigation structure.
			try:
				host_node = self.get_root().navigation.node
			except AttributeError:
				pass
			else:
				if self.target_node != host_node and self.target_node.is_ancestor_of(request.node):
					return True
		
		return False
	
	def has_active_descendants(self, request):
		for child in self.get_children():
			if child.is_active(request) or child.has_active_descendants(request):
				return True
		return False
	
	def _has_changed(self):
		if model_to_dict(self) == self._initial_data:
			return False
		return True
	
	def _clear_cache(self):
		try:
			root = self.get_root()
			if self.get_level() < root.navigation.depth:
				Navigation.objects.clear_cache_for(self.get_root().navigation.node)
		except AttributeError:
			pass
	
	def save(self, *args, **kwargs):
		super(NavigationItem, self).save(*args, **kwargs)
		
		if self._has_changed():
			self._clear_cache()
	
	def delete(self, *args, **kwargs):
		super(NavigationItem, self).delete(*args, **kwargs)
		self._clear_cache()