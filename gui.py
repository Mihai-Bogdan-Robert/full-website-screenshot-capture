#!/usr/bin/env python3
"""
Select output folder, enter sitemap URL, click Start.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import main

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
    result = main.main(folder, url)
    messagebox.showinfo("Result", result)

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

# Sitemap URL
ttk.Label(content, text="Sitemap URL:").grid(row=0, column=0, sticky='w')
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

# Layout weight
content.grid_columnconfigure(0, weight=0)
content.grid_columnconfigure(1, weight=1)
content.grid_columnconfigure(2, weight=0)

#---------------TODO---------------
# Add delay slider between requests in GUI
# Add a status bar to show progress
# Add max pages input field
# Add more options as needed

root.mainloop()
