#encoding: utf-8
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.db import models
from philo.models import TreeEntity, JSONField, Node
from philo.validators import RedirectValidator

#from mptt.templatetags.mptt_tags import cache_tree_children


DEFAULT_NAVIGATION_DEPTH = 3


class NavigationManager(models.Manager):
	
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
		key = node.pk
		try:
			hosted_navigation = self.__class__._cache[self.db][key]
		except KeyError:
			# Find the most recent host!
			ancestors = node.get_ancestors(ascending=True, include_self=True).annotate(num_navigation=models.Count("hosted_navigation_set"))
			
			# Iterate down the ancestors until you find one that:
			# a) is cached, or
			# b) has hosted navigation.
			pks_to_cache = []
			host_node = None
			for ancestor in ancestors:
				if ancestor.pk in self.__class__._cache[self.db] or ancestor.num_navigation > 0:
					host_node = ancestor
					break
				else:
					pks_to_cache.append(ancestor.pk)
			
			if host_node is None:
				return self.none()
			
			if ancestor.pk not in self.__class__._cache[self.db]:
				self.__class__._cache[self.db][ancestor.pk] = host_node.hosted_navigation_set.select_related('target_node')
			
			hosted_navigation = self.__class__._cache[self.db][ancestor.pk]
			
			# Cache the queryset instance for every pk that was passed over, as well.
			for pk in pks_to_cache:
				self.__class__._cache[self.db][pk] = hosted_navigation
		
		return hosted_navigation
	
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
	text = models.CharField(max_length=50)
	
	hosting_node = models.ForeignKey(Node, blank=True, null=True, related_name='hosted_navigation_set', help_text="Be part of this node's root navigation.")
	
	target_node = models.ForeignKey(Node, blank=True, null=True, related_name='targeting_navigation_set', help_text="Point to this node's url.")
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
			if self.reversing_parameters:
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
	
	def __unicode__(self):
		return self.get_path(field='text', pathsep=u' › ')
	
	# TODO: Add delete and save methods to handle cache clearing.
	
	class Meta:
		ordering = ['order']
		verbose_name_plural = 'navigation'