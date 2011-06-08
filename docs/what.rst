What is Philo, anyway?
======================

Philo allows the creation of site structures using Django's built-in admin interface. Like Django, Philo separates URL structure from backend code from display:

* :class:`.Node`\ s represent the URL hierarchy of the website.
* :class:`.View`\ s contain the logic for each :class:`.Node`, as simple as a :class:`.Redirect` or as complex as a :class:`.Blog`.
* :class:`.Page`\ s (the most commonly used :class:`.View`) render whatever context they are passed using database-driven :class:`.Template`\ s written with Django's template language.
* :class:`.Attribute`\ s are arbitrary key/value pairs which can be attached to most of the models that Philo provides. Attributes of a :class:`.Node` will be inherited by all of the :class:`.Node`'s descendants and will be available in the template's context.

The :ttag:`~philo.templatetags.containers.container` template tag that Philo provides makes it easy to mark areas in a template which need to be editable page-by-page; every :class:`.Page` will have an additional field in the admin for each :ttag:`~philo.templatetags.containers.container` in the template it uses.

How's that different than other CMSes?
++++++++++++++++++++++++++++++++++++++

Philo developed according to principles that grew out of the observation of the limitations and practices of other content management systems. For example, Philo believes that:

* Designers are in charge of how content is displayed, not end users. For example, users should be able to embed images in blog entries -- but the display of the image, even the presence or absence of a wrapping ``<figure>`` element, should depend on the template used to render the entry, not the HTML5 knowledge of the user.
	.. seealso:: :ttag:`~philo.templatetags.embed.embed`
* Interpretation of content (as a django template, as markdown, as textile, etc.) is the responsibility of the template designer, not of code developers or the framework.
	.. seealso:: :ttag:`~philo.templatetags.include_string.include_string`
* Page content should be simple -- not reorderable. Each piece of content should only be related to one page. Any other system will cause more trouble than it's worth.
	.. seealso:: :class:`.Contentlet`, :class:`.ContentReference`
* Some pieces of information may be shared by an entire site, used in disparate places, and changed frequently enough that it is far too difficult to track down every use. These pieces of information should be stored separately from the content that contains them.
	.. seealso:: :class:`.Attribute`
