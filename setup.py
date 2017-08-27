#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
import versioneer

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'bokeh>=0.12',
    'ipython>=5.0',
    'ipywidgets>=5.0',
    'matplotlib>=2.0',
    'notebook>=5.0',
    'numpy>=1.11',
    'pandas>=0.19',
    'seaborn>=0.7',
    'statsmodels>=0.8',
]

setup_requirements = [
    # TODO(leifwalsh): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='perfume-bench',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Interactive performance benchmarking in Jupyter",
    long_description=readme + '\n\n' + history,
    author="Leif Walsh",
    author_email='leif.walsh@gmail.com',
    url='https://github.com/leifwalsh/perfume',
    packages=find_packages(include=['perfume']),
    entry_points={
        'console_scripts': [
            'perfume=perfume.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.4, <4',
    license="BSD license",
    zip_safe=False,
    keywords='perfume python performance benchmarking jupyter interactive',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
