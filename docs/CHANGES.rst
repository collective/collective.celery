Changelog
=========

1.1.3 (2018-12-06)
------------------

- Fix use of always eager with newly created content
  [vangheem]


1.1.2 (2018-12-04)
------------------

- Use pickle transport by default to not break b/w compat
  [vangheem]


1.1.1 (2018-11-28)
------------------

- fix use of CELERY_TASK_ALWAYS_EAGER
  [vangheem]
  
- Python 3/Plone 5.2 support
  [vangheem]


1.1.0 (2018-10-12)
------------------

- fixes to work with latest celery
  [runyaga]


1.0.6 (2016-08-01)
------------------

Fixes:

- provide PARENTS value on the request object
  [vangheem]

1.0.5 (2016-06-27)
------------------

Fixes:

- detect location of zope conf
  [vangheem]


1.0.4 (2016-06-27)
------------------

Fixes:

- be able to use compound celery commands
  [vangheem]

1.0.3 (2016-06-03)
------------------

Fixes:

- If eager mode used, do not switch users
  [vangheem]


1.0.2 (2016-05-03)
------------------

New:

- nothing yet

Fixes:

- More test fixes. Provide setApp method to use in test setup
  [vangheem]

1.0.1 (2016-02-12)
------------------

New:

- nothing yet

Fixes:

- Fix use of CELERY_ALWAYS_EAGER so this package can be include in tests without
  too many gymnastics
  [vangheem]

1.0 (2015-12-09)
----------------

New:

- be able to schedule task outside of transaction management
  [vangheem]

- be able to specify entry points for module tasks
  [vangheem]


1.0a5 (2015-03-11)
------------------

- Add options argument to pass more options to apply_async (e.a: countdown eta etc.)


1.0a4 (2015-03-04)
------------------

- use unrestrictedTraverse when deserializing parameters
- Fix documentation

1.0a2 (2015-03-03)
------------------

- Initial release
