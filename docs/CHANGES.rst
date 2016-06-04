Changelog
=========

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
