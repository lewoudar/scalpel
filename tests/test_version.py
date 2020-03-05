import re

from scalpel.__version__ import __version__, version_info


def test_version_is_correctly_formatted():
    assert re.match(r'(\d+\.){2}\d+', __version__)


def test_version_info_returns_correct_version():
    value = version_info()
    assert isinstance(value, tuple)
    assert 3 == len(value)
    for item in value:
        assert isinstance(item, int)
