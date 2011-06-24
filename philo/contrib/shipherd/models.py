#encoding: utf-8
from UserDict import DictMixin
from hashlib import sha1

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.forms.models import model_to_dict

from philo.models.base import TreeEntity, TreeEntityManager, Entity
from philo.models.nodes import Node, TargetURLModel


DEFAULT_NAVIGATION_DEPTH = 3


class NavigationMapper(object, DictMixin):
	"""
	The :class:`NavigationMapper` is a dictionary-like object which allows easy fetching of the root items of a navigation for a node according to a key. A :class:`NavigationMapper` instance will be available on each node instance as :attr:`Node.navigation` if :mod:`~philo.contrib.shipherd` is in the :setting:`INSTALLED_APPS`
	
	"""
	def __init__(self, node):
		self.node = node
		self._cache = {}
	
	def __getitem__(self, key):
		if key not in self._cache:
			try:
				self._cache[key] = Navigation.objects.get_for_node(self.node, key)
			except Navigation.DoesNotExist:
				self._cache[key] = None
		return self._cache[key]


def navigation(self):
	if not hasattr(self, '_navigation'):
		self._navigation = NavigationMapper(self)
	return self._navigation


Node.navigation = property(navigation)


class NavigationManager(models.Manager):
	use_for_related = True
	
	def get_for_node(self, node, key):
		cache_key = self._get_cache_key(node, key)
		cached = cache.get(cache_key)
		
		if cached is None:
			opts = Node._mptt_meta
			left = getattr(node, opts.left_attr)
			right = getattr(node, opts.right_attr)
			tree_id = getattr(node, opts.tree_id_attr)
			kwargs = {
				"node__%s__lte" % opts.left_attr: left,
				"node__%s__gte" % opts.right_attr: right,
				"node__%s" % opts.tree_id_attr: tree_id
			}
			navs = self.filter(key=key, **kwargs).select_related('node').order_by('-node__%s' % opts.level_attr)
			nav = navs[0]
			roots = nav.roots.all().select_related('target_node').order_by('order')
			item_opts = NavigationItem._mptt_meta
			by_pk = {}
			tree_ids = []
			
			site_root_node = Site.objects.get_current().root_node
			
			for root in roots:
				by_pk[root.pk] = root
				tree_ids.append(getattr(root, item_opts.tree_id_attr))
				root._cached_children = []
				if root.target_node:
					root.target_node.get_path(root=site_root_node)
				root.navigation = nav
			
			kwargs = {
				'%s__in' % item_opts.tree_id_attr: tree_ids,
				'%s__lt' % item_opts.level_attr: nav.depth,
				'%s__gt' % item_opts.level_attr: 0
			}
			items = NavigationItem.objects.filter(**kwargs).select_related('target_node').order_by('level', 'order')
			for item in items:
				by_pk[item.pk] = item
				item._cached_children = []
				parent_pk = getattr(item, '%s_id' % item_opts.parent_attr)
				item.parent = by_pk[parent_pk]
				item.parent._cached_children.append(item)
				if item.target_node:
					item.target_node.get_path(root=site_root_node)
			
			cached = roots
			cache.set(cache_key, cached)
		
		return cached
	
	def _get_cache_key(self, node, key):
		opts = Node._mptt_meta
		left = getattr(node, opts.left_attr)
		right = getattr(node, opts.right_attr)
		tree_id = getattr(node, opts.tree_id_attr)
		parent_id = getattr(node, "%s_id" % opts.parent_attr)
		
		return sha1(unicode(left) + unicode(right) + unicode(tree_id) + unicode(parent_id) + unicode(node.pk) + unicode(key)).hexdigest()


class Navigation(Entity):
	"""
	:class:`Navigation` represents a group of :class:`NavigationItem`\ s that have an intrinsic relationship in terms of navigating a website. For example, a ``main`` navigation versus a ``side`` navigation, or a ``authenticated`` navigation versus an ``anonymous`` navigation.
	
	A :class:`Navigation`'s :class:`NavigationItem`\ s will be accessible from its related :class:`.Node` and that :class:`.Node`'s descendants through a :class:`NavigationMapper` instance at :attr:`Node.navigation`. Example::
	
		>>> node.navigation_set.all()
		[]
		>>> parent = node.parent
		>>> items = parent.navigation_set.get(key='main').roots.all()
		>>> parent.navigation["main"] == node.navigation["main"] == list(items)
		True
	
	"""
	#: A :class:`NavigationManager` instance.
	objects = NavigationManager()
	
	#: The :class:`.Node` which the :class:`Navigation` is attached to. The :class:`Navigation` will also be available to all the :class:`.Node`'s descendants and will override any :class:`Navigation` with the same key on any of the :class:`.Node`'s ancestors.
	node = models.ForeignKey(Node, related_name='navigation_set', help_text="Be available as navigation for this node.")
	#: Each :class:`Navigation` has a ``key`` which consists of one or more word characters so that it can easily be accessed in a template as ``{{ node.navigation.this_key }}``.
	key = models.CharField(max_length=255, validators=[RegexValidator("\w+")], help_text="Must contain one or more alphanumeric characters or underscores.", db_index=True)
	#: There is no limit to the depth of a tree of :class:`NavigationItem`\ s, but ``depth`` will limit how much of the tree will be displayed.
	depth = models.PositiveSmallIntegerField(default=DEFAULT_NAVIGATION_DEPTH, validators=[MinValueValidator(1)], help_text="Defines the maximum display depth of this navigation.")
	
	def __unicode__(self):
		return "%s[%s]" % (self.node, self.key)
	
	class Meta:
		unique_together = ('node', 'key')


class NavigationItem(TreeEntity, TargetURLModel):
	#: A :class:`ForeignKey` to a :class:`Navigation` instance. If this is not null, then the :class:`NavigationItem` will be a root node of the :class:`Navigation` instance.
	navigation = models.ForeignKey(Navigation, blank=True, null=True, related_name='roots', help_text="Be a root in this navigation tree.")
	#: The text which will be displayed in the navigation. This is a :class:`CharField` instance with max length 50.
	text = models.CharField(max_length=50)
	
	#: The order in which the :class:`NavigationItem` will be displayed.
	order = models.PositiveSmallIntegerField(default=0)
	
	def get_path(self, root=None, pathsep=u' › ', field='text'):
		return super(NavigationItem, self).get_path(root, pathsep, field)
	path = property(get_path)
	
	def clean(self):
		super(NavigationItem, self).clean()
		if bool(self.parent) == bool(self.navigation):
			raise ValidationError("Exactly one of `parent` and `navigation` must be defined.")
	
	def is_active(self, request):
		"""Returns ``True`` if the :class:`NavigationItem` is considered active for a given request and ``False`` otherwise."""
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
			root = self
			
			# The common case will be cached items, whose parents are cached with them.
			while root.parent is not None:
				root = root.parent
			
			host_node_id = root.navigation.node_id
			if self.target_node.pk != host_node_id and self.target_node.is_ancestor_of(request.node):
				return True
		
		return False
	
	def has_active_descendants(self, request):
		"""Returns ``True`` if the :class:`NavigationItem` has active descendants and ``False`` otherwise."""
		for child in self.get_children():
			if child.is_active(request) or child.has_active_descendants(request):
				return True
		return False