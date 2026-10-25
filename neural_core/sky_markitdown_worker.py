"""Internal SKY MarkItDown child; not a public CLI or a system sandbox."""
from __future__ import annotations

import io
import json
import socket
import sys

VALID_EXTS = frozenset({".pdf", ".docx", ".pptx", ".xlsx"})
MAX_INPUT = 4 * 1024 * 1024
MAX_OUTPUT = 60_000


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1 or arguments[0] not in VALID_EXTS:
        return 2
    payload = sys.stdin.buffer.read(MAX_INPUT + 1)
    if not payload or len(payload) > MAX_INPUT:
        return 2

    # Block ordinary Python socket connections during file conversion. This is
    # defense in depth, NOT isolation from native extensions/child processes.
    def no_network(*_args, **_kwargs):
        raise PermissionError("SKY MarkItDown conversion does not permit network access.")
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network

    try:
        # CPU limit on POSIX where supported; Windows is bounded by parent timeout.
        try:
            import resource
            if hasattr(resource, "RLIMIT_CPU"):
                resource.setrlimit(resource.RLIMIT_CPU, (22, 25))
        except (ImportError, OSError, ValueError):
            pass

        from markitdown import MarkItDown, StreamInfo
        converter = MarkItDown(enable_plugins=False)
        converted = converter.convert_stream(
            io.BytesIO(payload), stream_info=StreamInfo(extension=arguments[0])
        )
        markdown = getattr(converted, "markdown", None)
        if not isinstance(markdown, str):
            return 3
        result = {"markdown": markdown[:MAX_OUTPUT], "truncated": len(markdown) > MAX_OUTPUT}
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        # No private document data or converter traceback leaked to API callers.
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
