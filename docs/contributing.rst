Contributing to Philo
=====================

So you want to contribute to Philo? That's great! Here's some ways you can get started:

* **Report bugs and request features** using the issue tracker at the `project site <http://project.philocms.org/>`_.
* **Contribute code** using `git <http://git-scm.com/>`_. You can fork philo's repository either on `GitHub <http://github.com/ithinksw/philo/>`_ or `Gitorious <http://gitorious.org/ithinksw/philo/>`_. If you are contributing to Philo, you will need to submit a :ref:`Contributor License Agreement <cla>`.
* **Join the discussion** on IRC at `irc://irc.oftc.net/#philo <irc://irc.oftc.net/#philo>`_ if you have any questions or suggestions or just want to chat about the project. You can also keep in touch using the project mailing lists: `philo@ithinksw.org <mailto:philo@ithinksw.org>`_ and `philo-devel@ithinksw.org <mailto:philo-devel@ithinksw.org>`_.


Branches and Code Style
+++++++++++++++++++++++

We use `A successful Git branching model`__ with the blessed repository. To make things easier, you probably should too. This means that you should work on and against the develop branch in most cases, and leave it to the release manager to create the commits on the master branch if and when necessary. When pulling changes into the blessed repository at your request, the release manager will usually merge them into the develop branch unless you explicitly note they be treated otherwise.

__ http://nvie.com/posts/a-successful-git-branching-model/

Philo adheres to PEP8 for its code style, with two exceptions: tabs are used rather than spaces, and lines are not truncated at 79 characters.

.. _cla:

Licensing and Legal
+++++++++++++++++++

In order for the release manager to merge your changes into the blessed repository, you will need to have already submitted a signed CLA. Our CLAs are based on the Apache Software Foundation's CLAs, which is the same source as the `Django Project's CLAs`_. You might, therefore, find the `Django Project's CLA FAQ`_. helpful.

.. _`Django Project's CLAs`: https://www.djangoproject.com/foundation/cla/
.. _`Django Project's CLA FAQ`: https://www.djangoproject.com/foundation/cla/faq/

If you are an individual not doing work for an employer, then you can simply submit the :download:`Individual CLA <cla/ithinksw-icla.txt>`.

If you are doing work for an employer, they will need to submit the :download:`Corporate CLA <cla/ithinksw-ccla.txt>` and you will need to submit the Individual CLA :download:`Individual CLA <cla/ithinksw-icla.txt>` as well.

Both documents include information on how to submit them.
