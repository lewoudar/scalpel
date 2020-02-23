import re

from scalpel.__version__ import __version__


def test_version_is_correctly_formatted():
    assert re.match(r'(\d+\.){2}\d+', __version__)
