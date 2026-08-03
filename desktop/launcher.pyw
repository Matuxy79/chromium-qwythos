"""Desktop launcher bootstrapper.

Double-clicked via the "Qwythos" desktop shortcut, run with the *system*
pythonw.exe. Must work with stdlib only -- pywebview isn't installed until
this script installs it, so no third-party imports belong here.

Creates .venv (if missing), installs backend/requirements.txt + pywebview into
it, then hands off to app.py (run with the venv's own pythonw.exe, which is
where pywebview + the backend deps are guaranteed to exist).
"""

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / '.venv'
SETUP_MARKER = VENV_DIR / '.setup_complete'
SETUP_LOG = REPO_ROOT / 'desktop' / 'setup.log'
REQUIREMENTS = REPO_ROOT / 'backend' / 'requirements.txt'
ICON_PATH = REPO_ROOT / 'static' / 'static' / 'qwythos.ico'

CREATE_NO_WINDOW = 0x08000000


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / 'Scripts' / 'python.exe'


def venv_pythonw(venv_dir: Path) -> Path:
    return venv_dir / 'Scripts' / 'pythonw.exe'


def run_setup(status_var: tk.StringVar, on_done, on_error) -> None:
    try:
        with open(SETUP_LOG, 'w', encoding='utf-8') as log:
            status_var.set('Creating virtual environment...')
            subprocess.run(
                [sys.executable, '-m', 'venv', str(VENV_DIR)],
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )

            py = venv_python(VENV_DIR)
            status_var.set('Installing dependencies (this can take a minute)...')
            subprocess.run(
                [str(py), '-m', 'pip', 'install', '--upgrade', 'pip'],
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            subprocess.run(
                [str(py), '-m', 'pip', 'install', '-r', str(REQUIREMENTS), 'pywebview'],
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )

        SETUP_MARKER.write_text('ok', encoding='utf-8')
        on_done()
    except Exception as exc:
        on_error(f'{exc}\n\nSee {SETUP_LOG} for details.')


def show_progress_and_setup() -> bool:
    root = tk.Tk()
    if ICON_PATH.exists():
        try:
            root.iconbitmap(default=str(ICON_PATH))
        except tk.TclError:
            pass
    root.title('Qwythos - First-Time Setup')
    root.geometry('440x140')
    root.resizable(False, False)

    status_var = tk.StringVar(value='Preparing...')
    tk.Label(root, text='Setting up Qwythos (first run only)', font=('Segoe UI', 11, 'bold')).pack(pady=(18, 6))
    tk.Label(root, textvariable=status_var, font=('Segoe UI', 9), wraplength=400, justify='center').pack(pady=(0, 10))

    progress = ttk.Progressbar(root, mode='indeterminate', length=380)
    progress.pack(pady=(0, 12))
    progress.start(12)

    def on_done() -> None:
        root.after(0, root.destroy)

    def on_error(message: str) -> None:
        def show_error() -> None:
            progress.stop()
            status_var.set(f'Setup failed: {message}')
            tk.Button(root, text='Close', command=root.destroy).pack(pady=(0, 10))

        root.after(0, show_error)

    thread = threading.Thread(target=run_setup, args=(status_var, on_done, on_error), daemon=True)
    thread.start()
    root.mainloop()
    return SETUP_MARKER.exists()


def main() -> None:
    if not SETUP_MARKER.exists():
        if not show_progress_and_setup():
            return  # setup failed; error already shown to the user

    pyw = venv_pythonw(VENV_DIR)
    app_script = Path(__file__).resolve().parent / 'app.py'
    subprocess.Popen([str(pyw), str(app_script)], cwd=str(REPO_ROOT))


if __name__ == '__main__':
    main()
