# GUI (placeholder) — Full Website Captures

This is a small placeholder GUI to select an output folder and enter a sitemap URL.
It does not perform any crawling yet — the Start button currently shows a placeholder dialog.

Requirements
- Python 3 (macOS usually ships a Python; prefer installing from python.org or Homebrew)
- Tkinter (usually included with the system Python)

Run (recommended inside a virtualenv)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 gui.py
```

Or simply:

```bash
python3 gui.py
```

Next steps
- Wire the Start button to the crawler logic in `full-screenshot.py` (planned).
- Optionally add validations and a progress bar.