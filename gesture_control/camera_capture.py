"""Small, dependency-free helpers for resilient webcam capture."""


def camera_backends(system_name, windows_backend, default_backend):
    """Prefer DirectShow on Windows, always retaining OpenCV fallback."""
    if system_name == "Windows" and windows_backend is not None:
        return [windows_backend, default_backend]
    return [default_backend]
