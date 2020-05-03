import os
import shutil
import tempfile
from pathlib import Path

import nox

nox.options.reuse_existing_virtualenvs = True

PYTHON_VERSIONS = ['3.6', '3.7', '3.8']
if os.getenv('TRAVIS') is not None or os.getenv('AGENT_ID') is not None:
    CI_ENVIRONMENT = True
else:
    CI_ENVIRONMENT = False


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
    if not CI_ENVIRONMENT:
        session.notify('clean-robots-cache')


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


@nox.session(python=False, name='clean-nox')
def clean_nox(_):
    """Since nox take a bit of memory, this command helps to clean nox environment."""
    shutil.rmtree('.nox', ignore_errors=True)


@nox.session(python=False, name='clean-robots-cache')
def clean_robots_cache(_):
    """
    The creation of core.config.Configuration class creates a temporary directory.
    So as long as we write tests, more folders are created. This command helps to delete them
    """
    temp_dir = Path(tempfile.gettempdir())
    for path in temp_dir.iterdir():
        if path.is_dir() and path.name.startswith('robots_'):
            shutil.rmtree(f'{path.absolute()}')
