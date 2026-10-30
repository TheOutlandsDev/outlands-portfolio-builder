"""Capture only the fictional Tk review window on a Windows CI runner."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from PIL import ImageGrab, ImageStat
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import portfolio as core
from portfolio_gui import App


def finish_worker(root, app):
    deadline = time.monotonic() + 30
    while app.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(0.02)
    root.update()
    if app.busy:
        raise RuntimeError('fictional GUI worker did not finish')


def capture(root, window, path):
    window.lift()
    root.update()
    time.sleep(0.2)
    bounds = (window.winfo_rootx(), window.winfo_rooty(),
              window.winfo_rootx() + window.winfo_width(),
              window.winfo_rooty() + window.winfo_height())
    image = ImageGrab.grab(bbox=bounds, all_screens=True).convert('RGB')
    if image.width < 620 or image.height < 450 or ImageStat.Stat(image.convert('L')).var[0] < 50:
        raise RuntimeError('review window capture is missing or visually blank')
    image.save(path, format='PNG')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_controls_in_work_area(window, frame):
    if os.name != 'nt':
        return
    import ctypes
    from ctypes import wintypes

    work_area = wintypes.RECT()
    if not ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_area), 0):
        raise RuntimeError('could not determine Windows desktop work area')
    buttons = [item for item in frame.winfo_children() if isinstance(item, ttk.Frame)][-1]
    controls = [item for item in buttons.winfo_children() if isinstance(item, ttk.Button)]
    if len(controls) != 2:
        raise RuntimeError('review confirmation controls are missing')
    for control in controls:
        left, top = control.winfo_rootx(), control.winfo_rooty()
        right, bottom = left + control.winfo_width(), top + control.winfo_height()
        if (left < work_area.left or top < work_area.top or
                right > work_area.right or bottom > work_area.bottom):
            raise RuntimeError('review confirmation control is outside the Windows work area')


def main(require_windows=True):
    if require_windows and os.name != 'nt':
        raise RuntimeError('this capture must run on a native Windows runner')
    output = Path(os.environ['RUNNER_TEMP']) / 'portfolio-review-capture'
    output.mkdir()
    root = tk.Tk()
    app = App(root)
    try:
        app.demo()
        app.hash_files.set(True)
        with tempfile.TemporaryDirectory(prefix='portfolio-visual-') as folder:
            target = Path(folder) / 'bundle'
            app.output.set(str(target))
            app.start_export()
            finish_worker(root, app)
            if app.review_window is None or target.exists():
                raise RuntimeError('review must open before any output is written')
            window = app.review_window
            screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
            if screen_width < 940 or screen_height < 700:
                raise RuntimeError('Windows runner screen is too small for a 900x620 visual check')
            window.geometry('+20+20')
            root.update()
            frame = window.winfo_children()[0]
            assert_controls_in_work_area(window, frame)
            review_dimensions = f'{window.winfo_width()}x{window.winfo_height()}'
            book = next(item for item in frame.winfo_children() if isinstance(item, ttk.Notebook))
            readable_sha = capture(root, window, output / 'review-readable.png')
            book.select(1)
            exact_sha = capture(root, window, output / 'review-json.png')
            app.cancel_review()
            if target.exists():
                raise RuntimeError('cancelling review wrote output')
            app.start_export()
            finish_worker(root, app)
            if app.review_window is None or target.exists():
                raise RuntimeError('second review did not open before export')
            reviewed_json = app.pending_review[0].members['portfolio.json']
            app.confirm_review()
            finish_worker(root, app)
            if (target / 'portfolio.json').read_bytes() != reviewed_json:
                raise RuntimeError('confirmed output differs from reviewed JSON')
            verification = core.verify_bundle(target)
            if verification['status'] != 'PASS':
                raise RuntimeError('confirmed fictional bundle failed verification')
            result = {'status': 'PASS', 'platform': 'Windows runner' if os.name == 'nt' else 'Linux preflight',
                      'review_window': review_dimensions, 'files': verification['files'],
                      'readable_sha256': readable_sha, 'json_sha256': exact_sha}
            (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(result))
    finally:
        if app.review_window is not None:
            app.cancel_review()
        app.destroy()
        root.destroy()


if __name__ == '__main__':
    main()
