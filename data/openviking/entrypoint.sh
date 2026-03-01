#!/bin/bash
# Patch pyagfs missing AGFSBindingClient, then start OpenViking server
exec /app/.venv/bin/python -c "
import pyagfs
class _Dummy:
    def __init__(self, *a, **kw):
        raise NotImplementedError('AGFSBindingClient not available, use http-client mode')
if not hasattr(pyagfs, 'AGFSBindingClient'):
    pyagfs.AGFSBindingClient = _Dummy
from openviking.server.bootstrap import main
import sys
sys.exit(main())
" "$@"
