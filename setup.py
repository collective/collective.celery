from setuptools import setup, find_packages
import os

version = '1.1.3'

setup(name='collective.celery',
      version=version,
      description="Celery for Plone",
      long_description="%s\n%s" % (
          open("README.rst").read(),
          open(os.path.join("docs", "CHANGES.rst")).read()
      ),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Plone :: 4.0",
          "Framework :: Plone :: 4.1",
          "Framework :: Plone :: 4.2",
          "Framework :: Plone :: 4.3",
          "Framework :: Plone :: 5.0",
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
      install_requires=[
          'setuptools',
          'celery>=4',
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
      """,
      )
