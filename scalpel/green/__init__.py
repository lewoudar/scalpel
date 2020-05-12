from gevent import monkey

monkey.patch_all()  # noqa: E402
from .files import read_mp, write_mp

__all__ = [
    # files
    'read_mp', 'write_mp'
]
