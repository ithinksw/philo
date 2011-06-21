from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

from philo.utils.registry import Registry


DEFAULT_FEED = Atom1Feed


registry = Registry()


registry.register(Atom1Feed, verbose_name='Atom')
registry.register(Rss201rev2Feed, verbose_name='RSS')