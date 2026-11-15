"""
Bake server address into the built package. Should be built on proper machine.
"""

import os
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithServer(build_py):
    def run(self):
        super().run()
        host = os.environ.get("GC_VM_IP")
        port = os.environ.get("HEREYOUGOBOT_PORT")
        if not host or not port:
            raise SystemExit("GC_VM_IP and HEREYOUGOBOT_PORT must be set to build hereyougo")
        target = Path(self.build_lib, "hereyougo", "_server.py")
        target.write_text(f"HOST = {host!r}\nPORT = {int(port)}\n")


setup(cmdclass={"build_py": BuildPyWithServer})
