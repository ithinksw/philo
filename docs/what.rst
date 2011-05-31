What is Philo, anyway?
======================

Philo allows the creation of site structures using Django's built-in admin interface. Like Django, Philo separates URL structure from backend code from display:

* :class:`.Node`\ s represent the URL hierarchy of the website.
* :class:`.View`\ s contain the logic for each :class:`.Node`, as simple as a :class:`.Redirect` or as complex as a :class:`.Blog`.
* :class:`.Page`\ s (the most commonly used :class:`.View`) render whatever context they are passed using database-driven :class:`.Template`\ s written with Django's template language.
* :class:`.Attribute`\ s are arbitrary key/value pairs which can be attached to most of the models that Philo provides. Attributes of a :class:`.Node` will be inherited by all of the :class:`.Node`'s descendants and will be available in the template's context.

The :ttag:`~philo.templatetags.containers.container` template tag that Philo provides makes it easy to mark areas in a template which need to be editable page-by-page; every :class:`.Page` will have an additional field in the admin for each :ttag:`~philo.templatetags.containers.container` in the template it uses.
