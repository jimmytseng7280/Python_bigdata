from pathlib import Path
import os
import runpy
import subprocess
import sys

base_dir = Path(__file__).resolve().parent
script_path = base_dir / "lesson4-1.py"

venv_python_candidates = [
    base_dir.parent / ".venv" / "Scripts" / "python.exe",
    base_dir.parent / ".venv" / "bin" / "python",
]
venv_python = next((p for p in venv_python_candidates if p.exists()), None)

if venv_python and str(Path(sys.executable).resolve()).lower() != str(venv_python.resolve()).lower():
    os.execv(str(venv_python), [str(venv_python), str(script_path)])
else:
    runpy.run_path(str(script_path), run_name="__main__")
