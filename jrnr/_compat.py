from contextlib import contextmanager
import os
import sys

py2 = (sys.version_info[0] < 3)

if py2:

    @contextmanager
    def exclusive_open(fp):
        fd = os.open(fp, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, 'w+') as f:
            yield f

else:

    @contextmanager
    def exclusive_open(fp):
        with open(fp, 'x') as f:
            yield f
