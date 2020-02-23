import os
import shutil

import nox

nox.options.reuse_existing_virtualenvs = True

PYTHON_VERSIONS = ['3.6', '3.7', '3.8']


@nox.session(python=PYTHON_VERSIONS[-1])
def lint(session):
    """Performs pep8 and security checks."""
    source_code = 'scalpel'
    session.install('flake8==3.7.9', 'bandit==1.6.2')
    session.run('flake8', source_code)
    session.run('bandit', '-r', source_code)


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Runs the test suite."""
    session.install('poetry>=1.0.0,<2.0.0')
    session.run('poetry', 'install')
    session.run('pytest')

    # we notify codecov when the latest version of python is used
    if session.python == PYTHON_VERSIONS[-1]:
        session.notify('codecov')


@nox.session
def codecov(session):
    """Runs codecov command to share coverage information on codecov.io"""
    session.install('codecov==2.0.15')
    session.run('coverage', 'xml', '-i')
    session.run('codecov', '-f', 'coverage.xml')


@nox.session(python=PYTHON_VERSIONS[-1])
def docs(session):
    """Builds the documentation."""
    session.install('mkdocs==1.0.4')
    session.run('mkdocs', 'build', '--clean')


@nox.session(python=PYTHON_VERSIONS[-1])
def deploy(session):
    """
    Deploys on pypi.
    """
    if 'POETRY_PYPI_TOKEN_PYPI' not in os.environ:
        session.error('you must specify your pypi token api to deploy your package')

    session.install('poetry>=1.0.0,<2.0.0')
    session.run('poetry', 'publish', '--build')


@nox.session(python=False)
def clean(*_):
    """Since nox take a bit of memory, this command helps to clean nox environment."""
    shutil.rmtree('.nox', ignore_errors=True)
