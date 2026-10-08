from setuptools import setup, find_packages

version = '2.0.0.dev0'

setup(name='collective.celery',
      version=version,
      description="Celery for Plone",
      long_description=open("README.md").read(),
      long_description_content_type="text/markdown",
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Plone :: 6.0",
          "Framework :: Plone :: 6.1",
          "Framework :: Plone :: 6.2",
          "Programming Language :: Python :: 3",
      ],
      keywords='celery async plone',
      author='Nathan Van Gheem',
      author_email='vangheem@gmail.com',
      url='https://github.com/collective/collective.celery',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      python_requires='>=3.10',
      install_requires=[
          'setuptools',
          'celery>=5',
          'plone.api'
      ],
      extras_require={
          'test': [
              'plone.app.testing',
              'SQLAlchemy'
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone

      [console_scripts]
      pcelery = collective.celery.scripts.ccelery:main

      [celery.result_backends]
      zodb = collective.celery.backends.zodb:ZODBBackend
      """,
      )
