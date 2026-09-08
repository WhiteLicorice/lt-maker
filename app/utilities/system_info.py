import sys
from typing import Optional

# The docs say "use python version 3.11 only" and .gitlab-ci.yml builds on
# 3.11.8. Nothing else is tested.
SUPPORTED_PYTHON = (3, 11)

def is_editor_engine_built_version() -> bool:
    return hasattr(sys, 'frozen')

def get_python_version_warning() -> Optional[str]:
    """Returns a warning if this is not the Python version LT-maker is built
    and tested against, otherwise None."""
    if is_editor_engine_built_version():
        return None  # A release bundles its own interpreter
    version = sys.version_info[:2]
    if version != SUPPORTED_PYTHON:
        return ("LT-maker is only tested on Python %d.%d -- you are running %d.%d. "
                "No other version is supported, and crashes on one are usually "
                "the interpreter rather than anything in your project."
                % (SUPPORTED_PYTHON + version))
    return None