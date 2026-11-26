"""Create disposable test directories under the repository's build boundary."""
from pathlib import Path
from tempfile import TemporaryDirectory


def temporary_build_directory(root):
    build = Path(root) / 'build'
    build.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=build)
