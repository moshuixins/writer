"""
Monkey-patch pyagfs to add missing AGFSBindingClient.

The openviking:main image expects AGFSBindingClient in pyagfs,
but the bundled pyagfs 0.1.6 doesn't export it. Since we only use
http-client mode, a dummy class is sufficient.
"""
import pyagfs


class _DummyAGFSBindingClient:
    """Placeholder — never instantiated in http-client mode."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "AGFSBindingClient is not available in pyagfs 0.1.6. "
            "Use http-client mode instead of binding-client."
        )


if not hasattr(pyagfs, "AGFSBindingClient"):
    pyagfs.AGFSBindingClient = _DummyAGFSBindingClient
