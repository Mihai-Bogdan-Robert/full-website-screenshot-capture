#!/usr/bin/env python3
"""
Select output folder, enter sitemap URL, click Start.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import main
import threading

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)

def on_start():
    url = url_entry.get().strip()
    folder = folder_var.get().strip()
    if not url:
        messagebox.showwarning("Missing sitemap URL")
        return
    if not folder:
        messagebox.showwarning("Missing folder location")
        return
    # disable the start button while the worker runs
    start_button.config(state='disabled')

    def set_status(text):
        root.after(0, lambda: status_var.set(text))

    def set_progress(running=True):
        def _action():
            if running:
                progress.start(10)
            else:
                progress.stop()
        root.after(0, _action)

    def worker(folder, url):
        try:
            set_status('Parsing sitemap...')
            set_progress(True)
            result = main.main(folder, url)
            screenshots = result.get('screenshots') if isinstance(result, dict) else None
            if screenshots is not None:
                set_status(f'Done: {screenshots} screenshots')
                root.after(0, lambda: messagebox.showinfo('Result', f"Done: {screenshots} screenshots saved to {result.get('out_dir')}") )
            else:
                set_status('Done')
                root.after(0, lambda: messagebox.showinfo('Result', str(result)))
        except Exception as e:
            set_status('Error')
            root.after(0, lambda: messagebox.showerror('Error', str(e)))
        finally:
            set_progress(False)
            root.after(0, lambda: start_button.config(state='normal'))

    t = threading.Thread(target=worker, args=(folder, url), daemon=True)
    t.start()

root = tk.Tk()
root.title("Full Website Captures")
root.geometry("900x400")

# Center container
card = ttk.Frame(root)
card.place(relx=0.5, rely=0.5, anchor='center', width=800, height=300)

# Title and description
title = ttk.Label(card, text="Full Website Captures")
title.pack(pady=(5, 5), anchor='w', padx=14)
desc = ttk.Label(card, text="Enter a sitemap URL and choose an output folder. Click Start to begin.")
desc.pack(pady=(5, 5), anchor='w', padx=14)

content = ttk.Frame(card)
content.pack(fill='both', expand=True, padx=12)

# Website domain
ttk.Label(content, text="Website domain:").grid(row=0, column=0, sticky='w')
url_entry = ttk.Entry(content, width=60)
url_entry.grid(row=0, column=1, columnspan=2, sticky='we', padx=(8,0))

# Output folder
ttk.Label(content, text="Output Folder:").grid(row=1, column=0, sticky='w', pady=(10,0))
folder_var = tk.StringVar()
folder_entry = ttk.Entry(content, textvariable=folder_var, width=48)
folder_entry.grid(row=1, column=1, sticky='we', pady=(10,0), padx=(8,0))
ttk.Button(content, text="Browse...", command=select_folder).grid(row=1, column=2, sticky='e', pady=(10,0), padx=(8,0))

# Start button
start_button = ttk.Button(content, text="Start", width=12, command=on_start)
start_button.grid(row=2, column=2, sticky='e', pady=(12,0))

# Status bar (shows simple textual progress and an indeterminate spinner)
status_var = tk.StringVar(value='Idle')
status_frame = ttk.Frame(card)
status_frame.pack(fill='x', side='bottom', padx=12, pady=(8,8))
status_label = ttk.Label(status_frame, textvariable=status_var)
status_label.pack(side='left')
progress = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
progress.pack(side='right')

# Layout weight
content.grid_columnconfigure(0, weight=0)
content.grid_columnconfigure(1, weight=1)
content.grid_columnconfigure(2, weight=0)

#---------------TODO---------------
# Add delay slider between requests in GUI
# Add more options as needed

root.mainloop()
