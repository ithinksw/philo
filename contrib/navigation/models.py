#encoding: utf-8
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.db import models
from philo.models import TreeEntity, JSONField, Node, TreeManager
from philo.validators import RedirectValidator

#from mptt.templatetags.mptt_tags import cache_tree_children


DEFAULT_NAVIGATION_DEPTH = 3


class NavigationManager(TreeManager):
	
	# Analagous to contenttypes, cache Navigation to avoid repeated lookups all over the place.
	# Navigation will probably be used frequently.
	_cache = {}
	
	def for_node(self, node):
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
				if self._is_cached(self.db, ancestor) or ancestor.num_navigation > 0:
					host_node = ancestor
					break
				else:
					nodes_to_cache.append(ancestor)
			
			if not self._is_cached(self.db, host_node):
				self._add_to_cache(self.db, host_node)
			
			# Cache the queryset instance for every node that was passed over, as well.
			hosted_navigation = self._get_from_cache(self.db, host_node)
			for node in nodes_to_cache:
				self._add_to_cache(self.db, node, hosted_navigation)
		
		return hosted_navigation
	
	def _add_to_cache(self, using, node, qs=None):
		if node is None or node.pk is None:
			qs = self.none()
			key = None
		else:
			key = node.pk
		
		if qs is None:
			qs = node.hosted_navigation.select_related('target_node')
		
		self.__class__._cache.setdefault(using, {})[key] = qs
	
	def _get_from_cache(self, using, node):
		key = node.pk
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
		
		TODO: call this method from update() and delete()!
		"""
		if navigation is None:
			self.__class__._cache.clear()
		else:
			cache = self.__class__._cache[self.db]
			for pk in cache.keys():
				for qs in cache[pk]:
					if navigation in qs:
						cache.pop(pk)
						break
					else:
						for instance in qs:
							if navigation.is_descendant(instance):
								cache.pop(pk)
								break
						# necessary?
						if pk not in cache:
							break


class Navigation(TreeEntity):
	objects = NavigationManager()
	text = models.CharField(max_length=50)
	
	hosting_node = models.ForeignKey(Node, blank=True, null=True, related_name='hosted_navigation', help_text="Be part of this node's root navigation.")
	
	target_node = models.ForeignKey(Node, blank=True, null=True, related_name='targeting_navigation', help_text="Point to this node's url.")
	url_or_subpath = models.CharField(max_length=200, validators=[RedirectValidator()], blank=True, help_text="Point to this url or, if a node is defined and accepts subpaths, this subpath of the node.")
	reversing_parameters = JSONField(blank=True, help_text="If reversing parameters are defined, url_or_subpath will instead be interpreted as the view name to be reversed.")
	
	order = models.PositiveSmallIntegerField(blank=True, null=True)
	depth = models.PositiveSmallIntegerField(blank=True, null=True, default=DEFAULT_NAVIGATION_DEPTH, help_text="For the root of a hosted tree, defines the depth of the tree. A blank depth will hide this section of navigation. Otherwise, depth is ignored.")
	
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
	
	def __unicode__(self):
		return self.get_path(field='text', pathsep=u' › ')
	
	# TODO: Add delete and save methods to handle cache clearing.
	
	class Meta:
		ordering = ['order']
		verbose_name_plural = 'navigation'