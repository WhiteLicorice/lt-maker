import io
import os

WARNING_MSG = """
###############################################################################################################################
# This code was generated using `source_generator.py`. DO NOT MAKE ANY EDITS TO THIS FILE - YOUR CHANGES WILL BE OVERWRITTEN. #
###############################################################################################################################
"""

def get_codegen_header() -> str:
    return WARNING_MSG


class GeneratedSource(io.StringIO):
    """A generated source file. Written like a file opened for writing, but it only
    reaches the disk on close, and only if what was generated differs from what is
    already there.

    Generating is idempotent and runs every time the engine or editor starts, and
    again from tests. Rewriting an unchanged file would empty it for a moment, and
    another process importing it in that moment gets a module with nothing in it.
    """
    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def _on_disk(self) -> str:
        if not os.path.exists(self.path):
            return None
        with open(self.path) as existing:
            return existing.read()

    def close(self):
        text = self.getvalue()
        if self._on_disk() != text:
            with open(self.path, 'w') as generated:
                generated.write(text)
        super().close()
