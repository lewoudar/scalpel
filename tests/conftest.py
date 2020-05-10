from pathlib import Path
from typing import List, Any

import msgpack
import pytest


@pytest.fixture(scope='session')
def robots_content():
    return """
    User-agent: Googlebot
    Disallow: /videos/
    Disallow: /photos/

    User-agent: *
    Disallow: /admin/
    Allow: /admin/admin-ajax.php
    """


@pytest.fixture()
def create_msgpack_file():
    # noinspection PyTypeChecker
    def _create_msgpack_file(path: Path, data: List[Any]):
        packer = msgpack.Packer(autoreset=False)
        for item in data:
            packer.pack(item)
        with open(path, 'wb') as f:
            f.write(packer.getbuffer())

        packer.reset()

    return _create_msgpack_file
