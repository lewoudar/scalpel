from gevent import monkey

monkey.patch_all()  # noqa: E402
from .files import read_mp, write_mp
from .utils.io import wrap_file, open_file

__all__ = [
    # files
    'read_mp', 'write_mp',
    # io
    'wrap_file', 'open_file'
]
