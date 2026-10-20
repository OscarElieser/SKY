import pytest

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass
