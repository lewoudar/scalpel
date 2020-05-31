from gevent import monkey

monkey.patch_all()
from .files import read_mp, write_mp  # noqa: E402
from .utils.io import wrap_file, open_file  # noqa: E402

__all__ = [
    # files
    'read_mp', 'write_mp',
    # io
    'wrap_file', 'open_file'
]
