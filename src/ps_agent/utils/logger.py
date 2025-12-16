from __future__ import annotations

try:
    import structlog
except ImportError:
    structlog = None


def get_logger(name: str = __name__):
    if structlog:
        return structlog.get_logger(name)

    class _DummyLogger:
        def __getattr__(self, item):
            def _log(*args, **kwargs):
                return None

            return _log

    return _DummyLogger()
