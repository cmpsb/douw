Douw
====

| :strong:`dou·wen` `/ˈdɑu̯ən/`
| verb
| 1. (informal) Alternative form of :emphasis:`duwen` (to push)


.. contents::

Description
-----------

Drop-in website deployment.

Douw automates deploying new versions of websites using git and supports important features such as atomic updates, quick rollback, and DTAP environments.

Usage
-----

:strong:`NB:` this is a quick guide. Run ``douw help`` for the full documentation.

First, add a site::

    douw add --name example.com --remote https://github.com/Microsoft/project-html-website --env P

This creates a new, empty site under ``/srv/www/sites/example.com/``. Now you can deploy the site::

    douw deploy example.com

It is also possible to override the commit to deploy::

    douw deploy example.com 7552d9968e3cf8e11698696ea3f7fd42556d62e3

And if that version contains an error you can revert to the previous version::

    douw revert example.com

Or a specific version::

    douw revert example.com 747bf678fac31f72441428091b755755a62dbbbd

Only a limited number of previous deployments is kept in order to save space. A cleaning job can also be triggered manually::

    douw clean example.com

Or the site can be removed altogether::

    douw remove example.com

Directory structure
-------------------

By default, all sites are stored in directories with the sites' names under /srv/www/sites. In each directory, a ``deployments`` folder holds the currently available deployments. Next to the deployments is a link called ``current``, which points to one of the local deployments. Additionally, a folder ``shared`` is linked into each deployment in order to share data between deployments in a simple way. It is therefore recommended to put public htdocs in a separate folder.