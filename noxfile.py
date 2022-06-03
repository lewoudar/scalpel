import os
import shutil
import tempfile
from pathlib import Path

import nox

nox.options.reuse_existing_virtualenvs = True

PYTHON_VERSIONS = ['pypy3', '3.7', '3.8', '3.9']
CI_ENVIRONMENT = 'GITHUB_ACTIONS' in os.environ


@nox.session(python=PYTHON_VERSIONS[-1])
def lint(session):
    """Performs pep8 and security checks."""
    source_code = 'scalpel'
    session.install('flake8==3.9.2', 'bandit==1.7.4')
    session.run('flake8', source_code)
    session.run('bandit', '-r', source_code)


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """
    Runs the test suite.
    You can also run a part of the test suite by specifying the parts you want to test. The values "core", "green"
    and "any_io" are accepted as extra arguments. They can be cumulated.
    """
    to_test = ['core', 'any_io', 'green']
    for item in session.posargs:
        if item not in to_test:
            session.error(f'{item} is not part of {to_test}')
    to_test = session.posargs if session.posargs else to_test

    session.install('poetry>=1.0.0,<2.0.0')
    session.run('poetry', 'install', '-E', 'full')
    for part in to_test:
        arguments = ['coverage', 'run', f'--source=scalpel/{part}', '-m', 'pytest', f'tests/{part}']
        if part == 'green':
            arguments.insert(3, '--concurrency=gevent')
        session.run(*arguments)
        session.run('coverage', 'xml', '-o', f'coverage-{part}.xml')

    if not CI_ENVIRONMENT:
        session.notify('clean-robots-cache')


@nox.session(python=PYTHON_VERSIONS[-1])
def docs(session):
    """Builds the documentation."""
    session.install('poetry>=1.0.0,<2.0.0')
    session.run('poetry', 'install')
    session.run('mkdocs', 'build', '--clean')


@nox.session(python=False)
def deploy(session):
    """
    Deploys on pypi.
    """
    session.install('poetry>=1.0.0,<2.0.0')
    if 'POETRY_PYPI_TOKEN_PYPI' not in os.environ:
        session.error('you must specify your pypi token api to deploy your package')

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
