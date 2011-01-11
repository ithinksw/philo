#encoding: utf-8
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.db import models
from django.forms.models import model_to_dict
from philo.models import TreeEntity, JSONField, Node, TreeManager
from philo.validators import RedirectValidator


DEFAULT_NAVIGATION_DEPTH = 3


class NavigationQuerySet(models.query.QuerySet):
	"""
	This subclass is necessary to trigger cache clearing for Navigation when a mass update
	or deletion is performed. For now, either action will trigger a clearing of the entire
	navigation cache, since there's no convenient way to iterate over the changed or
	deleted instances.
	"""
	def update(self, *args, **kwargs):
		super(NavigationQuerySet, self).update(*args, **kwargs)
		Navigation.objects.clear_cache()
	
	def delete(self, *args, **kwargs):
		super(NavigationQuerySet, self).delete(*args, **kwargs)
		Navigation.objects.clear_cache()


class NavigationManager(TreeManager):
	
	# Analagous to contenttypes, cache Navigation to avoid repeated lookups all over the place.
	# Navigation will probably be used frequently.
	_cache = {}
	
	def get_queryset(self):
		return NavigationQuerySet(self.model, using=self._db)
	
	def closest_navigation(self, node):
		"""
		Returns the set of Navigation objects for a given node's navigation. This
		will be the most recent set of defined hosted navigation among the node's
		ancestors. Lookups are cached so that subsequent lookups for the same node
		don't hit the database.
		
		TODO: Should this create the auto-generated navigation in "physical" form?
		"""
		try:
			return self._get_from_cache(self.db, node)
		except KeyError:
			# Find the most recent host!
			ancestors = node.get_ancestors(ascending=True, include_self=True).annotate(num_navigation=models.Count("hosted_navigation"))
			
			# Iterate down the ancestors until you find one that:
			# a) is cached, or
			# b) has hosted navigation.
			nodes_to_cache = []
			host_node = None
			for ancestor in ancestors:
				if self.is_cached(ancestor) or ancestor.num_navigation > 0:
					host_node = ancestor
					break
				else:
					nodes_to_cache.append(ancestor)
			
			if not self.is_cached(host_node):
				self._add_to_cache(self.db, host_node)
			
			# Cache the queryset instance for every node that was passed over, as well.
			hosted_navigation = self._get_from_cache(self.db, host_node)
			for node in nodes_to_cache:
				self._add_to_cache(self.db, node, hosted_navigation)
		
		return hosted_navigation
	
	def is_cached(self, node):
		return self._is_cached(self.db, node)
	
	def _add_to_cache(self, using, node, qs=None):
		key = getattr(node, 'pk', None)
		
		if qs is None:
			if key is None:
				roots = self.none()
			else:
				roots = node.hosted_navigation.select_related('target_node')
			
			for root in roots:
				root_qs = root.get_descendants(include_self=True).complex_filter({'%s__lte' % root._mptt_meta.level_attr: root.get_level() + root.depth}).exclude(depth__isnull=True)
				if qs is None:
					qs = root_qs
				else:
					qs |= root_qs
		
			if qs is None:
				qs = self.none()
		
		self.__class__._cache.setdefault(using, {})[key] = qs
	
	def _get_from_cache(self, using, node):
		key = getattr(node, 'pk', None)
		return self.__class__._cache[self.db][key]
	
	def _is_cached(self, using, node):
		try:
			self._get_from_cache(using, node)
		except KeyError:
			return False
		return True
	
	def clear_cache(self, navigation=None):
		"""
		Clear out the navigation cache. This needs to happen during database flushes
		or if a navigation entry is changed to prevent caching of outdated navigation information.
		"""
		if navigation is None:
			self.__class__._cache.clear()
		elif self.db in self.__class__._cache:
			cache = self.__class__._cache[self.db]
			for pk, qs in cache.items():
				if navigation in qs:
					cache.pop(pk)


class Navigation(TreeEntity):
	objects = NavigationManager()
	text = models.CharField(max_length=50)
	
	hosting_node = models.ForeignKey(Node, blank=True, null=True, related_name='hosted_navigation', help_text="Be part of this node's root navigation.")
	
	target_node = models.ForeignKey(Node, blank=True, null=True, related_name='targeting_navigation', help_text="Point to this node's url.")
	url_or_subpath = models.CharField(max_length=200, validators=[RedirectValidator()], blank=True, help_text="Point to this url or, if a node is defined and accepts subpaths, this subpath of the node.")
	reversing_parameters = JSONField(blank=True, help_text="If reversing parameters are defined, url_or_subpath will instead be interpreted as the view name to be reversed.")
	
	order = models.PositiveSmallIntegerField(blank=True, null=True)
	depth = models.PositiveSmallIntegerField(blank=True, null=True, default=DEFAULT_NAVIGATION_DEPTH, help_text="For the root of a hosted tree, defines the depth of the tree. A blank depth will hide this section of navigation. Otherwise, depth is ignored.")
	
	def __init__(self, *args, **kwargs):
		super(Navigation, self).__init__(*args, **kwargs)
		self._initial_data = model_to_dict(self)
	
	def __unicode__(self):
		return self.get_path(field='text', pathsep=u' › ')
	
	def clean(self):
		# Should this be enforced? Not enforcing it would allow creation of "headers" in the navbar.
		if not self.target_node and not self.url_or_subpath:
			raise ValidationError("Either a target node or a url must be defined.")
		
		if self.reversing_parameters and (not self.url_or_subpath or not self.target_node):
			raise ValidationError("Reversing parameters require a view name and a target node.")
		
		try:
			self.get_target_url()
		except NoReverseMatch, e:
			raise ValidationError(e.message)
	
	def get_target_url(self):
		node = self.target_node
		if node is not None and node.accepts_subpath and self.url_or_subpath:
			if self.reversing_parameters is not None:
				view_name = self.url_or_subpath
				params = self.reversing_parameters
				args = isinstance(params, list) and params or None
				kwargs = isinstance(params, dict) and params or None
				return node.view.reverse(view_name, args=args, kwargs=kwargs, node=node)
			else:
				subpath = self.url_or_subpath
				while subpath and subpath[0] == '/':
					subpath = subpath[1:]
				return '%s%s' % (node.get_absolute_url(), subpath)
		elif node is not None:
			return node.get_absolute_url()
		else:
			return self.url_or_subpath
	target_url = property(get_target_url)
	
	def is_active(self, request):
		# First check if this particular navigation is active. It is considered active if:
		# - the requested node is this instance's target node and its subpath matches the requested path.
		# - the requested node is a descendant of this instance's target node and this instance's target
		#   node is not the hosting node of this navigation structure.
		# - this instance has no target node and the url matches either the request path or the full url.
		# - any of this instance's children are active.
		node = request.node
		
		if self.target_node == node:
			if self.target_url == request.path:
				return True
		elif self.target_node is None:
			if self.url_or_subpath == request.path or self.url_or_subpath == "http%s://%s%s" % (request.is_secure() and 's' or '', request.get_host(), request.path):
				return True
		elif self.target_node.is_ancestor_of(node) and self.target_node != self.hosting_node:
			return True
		
		# Always fall back to whether the node has active children.
		return self.has_active_children(request)
	
	def is_cached(self):
		"""Shortcut method for Navigation.objects.is_cached"""
		return Navigation.objects.is_cached(self)
	
	def has_active_children(self, request):
		for child in self.get_children():
			if child.is_active(request):
				return True
		return False
	
	def _has_changed(self):
		if model_to_dict(self) == self._initial_data:
			return False
		return True
	
	def save(self, *args, **kwargs):
		super(Navigation, self).save(*args, **kwargs)
		
		if self._has_changed():
			self._initial_data = model_to_dict(self)
			if self.is_cached():
				Navigation.objects.clear_cache(self)
			else:
				for navigation in self.get_ancestors():
					if navigation.hosting_node and navigation.is_cached() and self.get_level() <= (navigation.get_level() + navigation.depth):
						Navigation.objects.clear_cache(navigation)
	
	def delete(self, *args, **kwargs):
		super(Navigation, self).delete(*args, **kwargs)
		Navigation.objects.clear_cache(self)
	
	class Meta:
		ordering = ['order']
		verbose_name_plural = 'navigation'