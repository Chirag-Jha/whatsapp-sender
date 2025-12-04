#!/usr/bin/env python3
"""
WhatsApp Bulk Sender GUI - Modern Sleek Interface
Features: Smart validation, JSON/CSV import, Auto profile creation, Error handling
"""

import csv
import time
import urllib.parse
import sys
import subprocess
import traceback
import threading
import json
import os
from pathlib import Path
from datetime import datetime
import platform
from decimal import Decimal

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# GUI imports
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font as tkfont
import tkinter.messagebox as tkmsg

# ---------------- CONFIG ---------------- #
# Files
SENT_LOG_CSV = "sent_log.csv"
DEBUG_LOG = "debug_log.txt"
ERROR_LOG = "error_log.txt"
DRAFT_FILE = "draft_autosave.json"

# Edge driver and profile
EDGE_DRIVER_PATH = r"D:\driver\msedgedriver.exe"
USE_REAL_EDGE_PROFILE = True
EDGE_USER_DATA_DIR = r"C:\Users\chira\AppData\Local\Microsoft\Edge\User Data"
EDGE_PROFILE_DIR_NAME = "Profile 1"

# Local profile fallback
LOCAL_PROFILE_DIR = Path.cwd() / "edge_whatsapp_profile"

# Behavior settings
REMOTE_DEBUGGING_PORT = 9222
DELAY_AFTER_OPEN = 4
MAX_TRIES = 2
WAIT_FOR_INPUT_TIMEOUT = 20

# Modern Color Palette (Dark Theme)
COLORS = {
    "bg_dark": "#1e1e1e",
    "bg_darker": "#171717",
    "bg_lighter": "#2d2d2d",
    "primary": "#0ea5e9",      # Sky blue
    "primary_dark": "#0284c7",
    "primary_light": "#38bdf8",
    "secondary": "#8b5cf6",    # Violet
    "success": "#10b981",      # Emerald
    "error": "#ef4444",        # Red
    "warning": "#f59e0b",      # Amber
    "text_primary": "#f8fafc",
    "text_secondary": "#cbd5e1",
    "text_muted": "#94a3b8",
    "border": "#374151",
    "card_bg": "#262626",
    "hover_bg": "#3f3f3f",
    "input_bg": "#0f172a",
    "log_bg": "#000000",
    "log_text": "#e2e8f0",
}
# -------------------------------------- #

def log_debug(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[DEBUG {timestamp}] {msg}"
    print(line)
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (PermissionError, IOError):
        pass

def log_error(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[ERROR {timestamp}] {msg}"
    print(line)
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (PermissionError, IOError):
        pass

def log_exception(exc: Exception):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write("-----\n")
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " EXCEPTION TRACE\n")
        traceback.print_exc(file=f)
        f.write("-----\n")
    traceback.print_exc()

class ModernButton(tk.Canvas):
    """Modern custom button with hover effects"""
    def __init__(self, parent, text, command=None, width=120, height=40, 
                 bg=COLORS["primary"], fg=COLORS["text_primary"], 
                 hover_bg=COLORS["primary_dark"], radius=8, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=COLORS["bg_dark"])
        
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg
        self.radius = radius
        self.width = width
        self.height = height
        
        # Draw button
        self.draw_button(bg)
        
        # Add text
        self.text_id = self.create_text(width/2, height/2, text=text, 
                                       fill=fg, font=("Segoe UI", 10, "bold"))
        
        # Bind events
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
    def draw_button(self, color):
        self.delete("button")
        # Draw rounded rectangle
        self.create_rounded_rect(2, 2, self.width-2, self.height-2, 
                                self.radius, fill=color, outline=color, tags="button")
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1,
                 x2-radius, y1,
                 x2, y1,
                 x2, y1+radius,
                 x2, y2-radius,
                 x2, y2,
                 x2-radius, y2,
                 x1+radius, y2,
                 x1, y2,
                 x1, y2-radius,
                 x1, y1+radius,
                 x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)
    
    def on_enter(self, e):
        self.draw_button(self.hover_bg)
    
    def on_leave(self, e):
        self.draw_button(self.bg)
    
    def on_click(self, e):
        if self.command:
            self.command()

class WhatsAppBulkSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp Bulk Sender Pro")
        self.root.geometry("1100x800")
        self.root.configure(bg=COLORS["bg_dark"])
        
        # Center window on screen
        self.center_window()
        
        # Initialize variables
        self.driver = None
        self.sending = False
        self.stop_requested = False
        self.processed_count = 0
        self.total_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.delay_between = 6
        self.first_run = not Path("edge_whatsapp_profile").exists()
        
        # Setup fonts
        self.setup_fonts()
        
        # Setup GUI
        self.setup_ui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Ensure local profile directory exists
        self.ensure_local_profile()
        
        # Load saved draft if exists
        self.load_draft()
        
        # Auto-save draft every 30 seconds
        self.auto_save_draft()
        
        # Show welcome guide on first run
        if self.first_run:
            self.root.after(500, self.show_welcome_guide)
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_fonts(self):
        """Define custom fonts"""
        self.title_font = ("Segoe UI", 24, "bold")
        self.heading_font = ("Segoe UI", 14, "bold")
        self.body_font = ("Segoe UI", 11)
        self.mono_font = ("Consolas", 10)
        self.small_font = ("Segoe UI", 9)
        
    def ensure_local_profile(self):
        """Create local profile directory if it doesn't exist"""
        try:
            LOCAL_PROFILE_DIR.mkdir(exist_ok=True)
            log_debug(f"Local profile directory: {LOCAL_PROFILE_DIR}")
        except Exception as e:
            log_error(f"Failed to create local profile directory: {e}")
            
    def setup_ui(self):
        # Main container
        main_container = tk.Frame(self.root, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_container, bg=COLORS["bg_dark"])
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Title with gradient effect
        title_frame = tk.Frame(header_frame, bg=COLORS["bg_dark"])
        title_frame.pack(fill="x")
        
        tk.Label(title_frame, text="📱 WhatsApp Bulk Sender", 
                font=self.title_font,
                bg=COLORS["bg_dark"],
                fg=COLORS["text_primary"]).pack(side="left")
        
        tk.Label(title_frame, text="Pro", 
                font=self.title_font,
                bg=COLORS["bg_dark"],
                fg=COLORS["primary"]).pack(side="left", padx=(0, 10))
        
        # Version label
        tk.Label(title_frame, text="v2.1", 
                font=("Segoe UI", 10),
                bg=COLORS["bg_dark"],
                fg=COLORS["text_muted"]).pack(side="right")
        
        # Subtitle
        tk.Label(header_frame, text="Send WhatsApp messages in bulk with ease", 
                font=self.small_font,
                bg=COLORS["bg_dark"],
                fg=COLORS["text_secondary"]).pack(anchor="w")
        
        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True)
        
        # Style the notebook
        self.style_notebook()
        
        # Create tabs
        self.setup_compose_tab()
        self.setup_settings_tab()
        self.setup_progress_tab()
        
        # Status bar
        self.setup_status_bar()
        
    def style_notebook(self):
        """Style the notebook tabs"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure notebook style
        style.configure("Custom.TNotebook", 
                       background=COLORS["bg_dark"],
                       borderwidth=0)
        style.configure("Custom.TNotebook.Tab",
                       padding=[15, 8],
                       background=COLORS["card_bg"],
                       foreground=COLORS["text_secondary"],
                       borderwidth=0,
                       font=("Segoe UI", 10, "bold"))
        style.map("Custom.TNotebook.Tab",
                 background=[("selected", COLORS["primary"])],
                 foreground=[("selected", COLORS["text_primary"])])
        
        self.notebook.configure(style="Custom.TNotebook")
        
    def setup_compose_tab(self):
        """Tab 1: Compose message and enter numbers"""
        tab1 = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab1, text="✏️ Compose")
        
        # Two-column layout
        left_panel = tk.Frame(tab1, bg=COLORS["bg_dark"])
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_panel = tk.Frame(tab1, bg=COLORS["bg_dark"])
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Message Section
        msg_frame = self.create_card(left_panel, "Your Message")
        msg_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Message counter
        counter_frame = tk.Frame(msg_frame, bg=COLORS["card_bg"])
        counter_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        tk.Label(counter_frame, text="Message:", 
                font=self.body_font,
                bg=COLORS["card_bg"],
                fg=COLORS["text_primary"]).pack(side="left")
        
        self.msg_counter = tk.Label(counter_frame, text="0 chars", 
                                   font=self.small_font,
                                   bg=COLORS["card_bg"],
                                   fg=COLORS["text_muted"])
        self.msg_counter.pack(side="right")
        
        # Message text area
        self.message_text = scrolledtext.ScrolledText(msg_frame,
                                                     height=12,
                                                     font=("Segoe UI", 11),
                                                     wrap=tk.WORD,
                                                     bg=COLORS["input_bg"],
                                                     fg=COLORS["text_primary"],
                                                     insertbackground=COLORS["text_primary"],
                                                     relief="flat",
                                                     borderwidth=2,
                                                     highlightbackground=COLORS["border"],
                                                     highlightcolor=COLORS["primary"],
                                                     highlightthickness=1)
        self.message_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.message_text.bind("<KeyRelease>", self.update_message_counter)
        self.message_text.bind("<<Paste>>", lambda e: self.root.after(10, self.update_message_counter))
        
        # Numbers Section
        num_frame = self.create_card(right_panel, "Phone Numbers")
        num_frame.pack(fill="both", expand=True)
        
        # Instructions
        instr_text = """Enter phone numbers (comma separated)

Examples:
• 940669674 → becomes 91940669674
• 91940669674 → stays as is
• 9140669674 → INVALID (check number)

Only 10-digit numbers or 12-digit numbers with '91' prefix."""
        
        instr_label = tk.Label(num_frame, 
                              text=instr_text,
                              font=self.small_font,
                              bg=COLORS["card_bg"],
                              fg=COLORS["text_secondary"],
                              justify=tk.LEFT)
        instr_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Numbers text area
        self.numbers_text = scrolledtext.ScrolledText(num_frame,
                                                     height=10,
                                                     font=self.mono_font,
                                                     wrap=tk.WORD,
                                                     bg=COLORS["input_bg"],
                                                     fg=COLORS["text_primary"],
                                                     insertbackground=COLORS["text_primary"],
                                                     relief="flat",
                                                     borderwidth=2,
                                                     highlightbackground=COLORS["border"],
                                                     highlightthickness=1)
        self.numbers_text.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.numbers_text.bind("<KeyRelease>", self.update_numbers_counter)
        self.numbers_text.bind("<<Paste>>", lambda e: self.root.after(10, self.update_numbers_counter))
        
        # Number counter
        self.numbers_counter = tk.Label(num_frame, 
                                       text="0 numbers",
                                       font=self.small_font,
                                       bg=COLORS["card_bg"],
                                       fg=COLORS["text_muted"])
        self.numbers_counter.pack(anchor="e", padx=15, pady=(0, 5))
        
        # Import buttons
        import_frame = tk.Frame(num_frame, bg=COLORS["card_bg"])
        import_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # CSV button
        csv_btn = tk.Frame(import_frame, bg=COLORS["primary"], 
                          highlightbackground=COLORS["primary"], 
                          highlightthickness=0)
        csv_btn.pack(side="left", padx=(0, 10))
        
        csv_btn_label = tk.Label(csv_btn, text="📁 CSV", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["primary"],
                fg=COLORS["text_primary"],
                padx=12, pady=6)
        csv_btn_label.pack()
        csv_btn.bind("<Button-1>", lambda e: self.load_csv())
        csv_btn_label.bind("<Button-1>", lambda e: self.load_csv())
        csv_btn.bind("<Enter>", lambda e: (csv_btn.configure(bg=COLORS["primary_dark"]), csv_btn_label.configure(bg=COLORS["primary_dark"])))
        csv_btn.bind("<Leave>", lambda e: (csv_btn.configure(bg=COLORS["primary"]), csv_btn_label.configure(bg=COLORS["primary"])))
        csv_btn_label.bind("<Enter>", lambda e: (csv_btn.configure(bg=COLORS["primary_dark"]), csv_btn_label.configure(bg=COLORS["primary_dark"])))
        csv_btn_label.bind("<Leave>", lambda e: (csv_btn.configure(bg=COLORS["primary"]), csv_btn_label.configure(bg=COLORS["primary"])))
        
        # JSON button
        json_btn = tk.Frame(import_frame, bg=COLORS["secondary"], 
                           highlightbackground=COLORS["secondary"], 
                           highlightthickness=0)
        json_btn.pack(side="left")
        
        json_btn_label = tk.Label(json_btn, text="📊 JSON", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["secondary"],
                fg=COLORS["text_primary"],
                padx=12, pady=6)
        json_btn_label.pack()
        json_btn.bind("<Button-1>", lambda e: self.load_json())
        json_btn_label.bind("<Button-1>", lambda e: self.load_json())
        json_btn.bind("<Enter>", lambda e: (json_btn.configure(bg="#7c3aed"), json_btn_label.configure(bg="#7c3aed")))
        json_btn.bind("<Leave>", lambda e: (json_btn.configure(bg=COLORS["secondary"]), json_btn_label.configure(bg=COLORS["secondary"])))
        json_btn_label.bind("<Enter>", lambda e: (json_btn.configure(bg="#7c3aed"), json_btn_label.configure(bg="#7c3aed")))
        json_btn_label.bind("<Leave>", lambda e: (json_btn.configure(bg=COLORS["secondary"]), json_btn_label.configure(bg=COLORS["secondary"])))
        
        # Example button
        example_btn = tk.Frame(import_frame, bg=COLORS["success"], 
                              highlightthickness=0)
        example_btn.pack(side="left", padx=(10, 0))
        
        example_btn_label = tk.Label(example_btn, text="💡 Example", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["success"],
                fg=COLORS["text_primary"],
                padx=12, pady=6)
        example_btn_label.pack()
        example_btn.bind("<Button-1>", lambda e: self.load_example())
        example_btn_label.bind("<Button-1>", lambda e: self.load_example())
        example_btn.bind("<Enter>", lambda e: (example_btn.configure(bg="#059669"), example_btn_label.configure(bg="#059669")))
        example_btn.bind("<Leave>", lambda e: (example_btn.configure(bg=COLORS["success"]), example_btn_label.configure(bg=COLORS["success"])))
        example_btn_label.bind("<Enter>", lambda e: (example_btn.configure(bg="#059669"), example_btn_label.configure(bg="#059669")))
        example_btn_label.bind("<Leave>", lambda e: (example_btn.configure(bg=COLORS["success"]), example_btn_label.configure(bg=COLORS["success"])))
        
        # Preview Section at bottom
        preview_frame = self.create_card(left_panel, "Preview")
        preview_frame.pack(fill="x", pady=(10, 0))
        
        self.preview_label = tk.Label(preview_frame,
                                     text="Enter message and numbers to see preview",
                                     font=self.small_font,
                                     bg=COLORS["card_bg"],
                                     fg=COLORS["text_muted"],
                                     justify=tk.LEFT,
                                     wraplength=400)
        self.preview_label.pack(padx=15, pady=15)
        
    def setup_settings_tab(self):
        """Tab 2: Settings"""
        tab2 = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab2, text="⚙️ Settings")
        
        # Settings container with scroll
        canvas = tk.Canvas(tab2, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab2, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Sending Settings
        send_frame = self.create_card(scrollable_frame, "Sending Settings")
        send_frame.pack(fill="x", padx=20, pady=10)
        
        # Delay setting
        self.create_setting_row(send_frame, "Delay between messages (seconds):", 
                               self.create_spinbox, "delay_var", 6, 1, 60)
        
        # Max retries
        self.create_setting_row(send_frame, "Max retry attempts:", 
                               self.create_spinbox, "tries_var", 2, 1, 5)
        
        # Browser Settings
        browser_frame = self.create_card(scrollable_frame, "Browser Settings")
        browser_frame.pack(fill="x", padx=20, pady=10)
        
        # Kill Edge checkbox
        self.kill_edge_var = tk.BooleanVar(value=True)
        self.create_checkbox(browser_frame, "Kill Edge processes before starting", 
                            self.kill_edge_var)
        
        # Profile selection
        self.create_setting_row(browser_frame, "Edge Profile:", 
                               self.create_profile_dropdown)
        
        # Logging Settings
        log_frame = self.create_card(scrollable_frame, "Logging")
        log_frame.pack(fill="x", padx=20, pady=10)
        
        # Add helpful tip
        tip_label = tk.Label(log_frame,
                            text="💡 Tip: Use Tab key to navigate between tabs quickly!",
                            font=self.small_font,
                            bg=COLORS["card_bg"],
                            fg=COLORS["text_muted"],
                            pady=10)
        tip_label.pack(anchor="w", padx=15)
        
        # Log level
        self.create_setting_row(log_frame, "Log Level:", 
                               self.create_log_level_dropdown)
        
        # Action buttons
        action_frame = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
        action_frame.pack(fill="x", padx=20, pady=20)
        
        # Button container
        btn_container = tk.Frame(action_frame, bg=COLORS["bg_dark"])
        btn_container.pack()
        
        # Clear Logs button
        clear_btn = tk.Frame(btn_container, bg=COLORS["error"], 
                            highlightthickness=0)
        clear_btn.pack(side="left", padx=(0, 10))
        
        clear_btn_label = tk.Label(clear_btn, text="🗑️ Clear Logs", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["error"],
                fg=COLORS["text_primary"],
                padx=15, pady=8)
        clear_btn_label.pack()
        clear_btn.bind("<Button-1>", lambda e: self.clear_logs())
        clear_btn_label.bind("<Button-1>", lambda e: self.clear_logs())
        clear_btn.bind("<Enter>", lambda e: (clear_btn.configure(bg="#dc2626"), clear_btn_label.configure(bg="#dc2626")))
        clear_btn.bind("<Leave>", lambda e: (clear_btn.configure(bg=COLORS["error"]), clear_btn_label.configure(bg=COLORS["error"])))
        clear_btn_label.bind("<Enter>", lambda e: (clear_btn.configure(bg="#dc2626"), clear_btn_label.configure(bg="#dc2626")))
        clear_btn_label.bind("<Leave>", lambda e: (clear_btn.configure(bg=COLORS["error"]), clear_btn_label.configure(bg=COLORS["error"])))
        
        # Open Log Folder button
        folder_btn = tk.Frame(btn_container, bg=COLORS["primary"], 
                             highlightthickness=0)
        folder_btn.pack(side="left")
        
        folder_btn_label = tk.Label(folder_btn, text="📂 Open Log Folder", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["primary"],
                fg=COLORS["text_primary"],
                padx=15, pady=8)
        folder_btn_label.pack()
        folder_btn.bind("<Button-1>", lambda e: self.open_log_folder())
        folder_btn_label.bind("<Button-1>", lambda e: self.open_log_folder())
        folder_btn.bind("<Enter>", lambda e: (folder_btn.configure(bg=COLORS["primary_dark"]), folder_btn_label.configure(bg=COLORS["primary_dark"])))
        folder_btn.bind("<Leave>", lambda e: (folder_btn.configure(bg=COLORS["primary"]), folder_btn_label.configure(bg=COLORS["primary"])))
        folder_btn_label.bind("<Enter>", lambda e: (folder_btn.configure(bg=COLORS["primary_dark"]), folder_btn_label.configure(bg=COLORS["primary_dark"])))
        folder_btn_label.bind("<Leave>", lambda e: (folder_btn.configure(bg=COLORS["primary"]), folder_btn_label.configure(bg=COLORS["primary"])))
        
        # Help button
        help_btn = tk.Frame(btn_container, bg=COLORS["secondary"], 
                           highlightthickness=0)
        help_btn.pack(side="left", padx=(10, 0))
        
        help_btn_label = tk.Label(help_btn, text="❓ Help Guide", 
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["secondary"],
                fg=COLORS["text_primary"],
                padx=15, pady=8)
        help_btn_label.pack()
        help_btn.bind("<Button-1>", lambda e: self.show_welcome_guide())
        help_btn_label.bind("<Button-1>", lambda e: self.show_welcome_guide())
        help_btn.bind("<Enter>", lambda e: (help_btn.configure(bg="#7c3aed"), help_btn_label.configure(bg="#7c3aed")))
        help_btn.bind("<Leave>", lambda e: (help_btn.configure(bg=COLORS["secondary"]), help_btn_label.configure(bg=COLORS["secondary"])))
        help_btn_label.bind("<Enter>", lambda e: (help_btn.configure(bg="#7c3aed"), help_btn_label.configure(bg="#7c3aed")))
        help_btn_label.bind("<Leave>", lambda e: (help_btn.configure(bg=COLORS["secondary"]), help_btn_label.configure(bg=COLORS["secondary"])))
        
    def setup_progress_tab(self):
        """Tab 3: Progress and Logs"""
        tab3 = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab3, text="📊 Progress")
        
        # Stats cards in grid
        stats_frame = tk.Frame(tab3, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Create stat cards
        self.total_card = self.create_stat_card(stats_frame, "Total Numbers", "0", COLORS["text_primary"])
        self.total_card.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.processed_card = self.create_stat_card(stats_frame, "Processed", "0", COLORS["primary"])
        self.processed_card.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.success_card = self.create_stat_card(stats_frame, "Successful", "0", COLORS["success"])
        self.success_card.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.failed_card = self.create_stat_card(stats_frame, "Failed", "0", COLORS["error"])
        self.failed_card.pack(side="left", expand=True, fill="both")
        
        # Progress bar area
        progress_frame = self.create_card(tab3, "Sending Progress")
        progress_frame.pack(fill="x", padx=20, pady=10)
        
        # Custom progress bar
        self.progress_frame_inner = tk.Frame(progress_frame, bg=COLORS["border"], height=25)
        self.progress_frame_inner.pack(fill="x", padx=20, pady=(15, 10))
        self.progress_frame_inner.pack_propagate(False)
        
        self.progress_bar = tk.Frame(self.progress_frame_inner, bg=COLORS["primary"], width=0)
        self.progress_bar.pack(side="left", fill="y")
        
        self.progress_label = tk.Label(self.progress_frame_inner,
                                      text="0%",
                                      font=("Segoe UI", 9, "bold"),
                                      bg=COLORS["border"],
                                      fg=COLORS["text_primary"])
        self.progress_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Status text
        self.status_label = tk.Label(progress_frame,
                                    text="Ready to start",
                                    font=self.small_font,
                                    bg=COLORS["card_bg"],
                                    fg=COLORS["text_secondary"])
        self.status_label.pack(pady=(0, 15))
        
        # Control buttons
        control_frame = tk.Frame(progress_frame, bg=COLORS["card_bg"])
        control_frame.pack(pady=(0, 20))
        
        # Start button
        self.start_btn_frame = tk.Frame(control_frame, bg=COLORS["success"], 
                                       highlightthickness=0)
        self.start_btn_frame.pack(side="left", padx=(0, 15))
        
        self.start_label = tk.Label(self.start_btn_frame, text="🚀 START SENDING", 
                                   font=("Segoe UI", 11, "bold"),
                                   bg=COLORS["success"],
                                   fg=COLORS["text_primary"],
                                   padx=25, pady=12)
        self.start_label.pack()
        self.start_btn_frame.bind("<Button-1>", lambda e: self.start_sending())
        self.start_label.bind("<Button-1>", lambda e: self.start_sending())
        self.start_btn_frame.bind("<Enter>", lambda e: (self.start_btn_frame.configure(bg="#059669"), self.start_label.configure(bg="#059669")))
        self.start_btn_frame.bind("<Leave>", lambda e: (self.start_btn_frame.configure(bg=COLORS["success"]), self.start_label.configure(bg=COLORS["success"])))
        self.start_label.bind("<Enter>", lambda e: (self.start_btn_frame.configure(bg="#059669"), self.start_label.configure(bg="#059669")))
        self.start_label.bind("<Leave>", lambda e: (self.start_btn_frame.configure(bg=COLORS["success"]), self.start_label.configure(bg=COLORS["success"])))
        
        # Stop button
        self.stop_btn_frame = tk.Frame(control_frame, bg=COLORS["error"], highlightthickness=0)
        self.stop_btn_frame.pack(side="left", padx=(0, 15))
        
        self.stop_label = tk.Label(self.stop_btn_frame, text="⏹️ STOP", 
                                  font=("Segoe UI", 11, "bold"),
                                  bg=COLORS["error"],
                                  fg=COLORS["text_primary"],
                                  padx=25, pady=12)
        
        self.stop_label.pack()
        self.stop_btn_frame.bind("<Button-1>", lambda e: self.stop_sending())
        self.stop_label.bind("<Button-1>", lambda e: self.stop_sending())
        self.stop_btn_frame.bind("<Enter>", lambda e: (self.stop_btn_frame.configure(bg="#dc2626"), self.stop_label.configure(bg="#dc2626")))
        self.stop_btn_frame.bind("<Leave>", lambda e: (self.stop_btn_frame.configure(bg=COLORS["error"]), self.stop_label.configure(bg=COLORS["error"])))
        self.stop_label.bind("<Enter>", lambda e: (self.stop_btn_frame.configure(bg="#dc2626"), self.stop_label.configure(bg="#dc2626")))
        self.stop_label.bind("<Leave>", lambda e: (self.stop_btn_frame.configure(bg=COLORS["error"]), self.stop_label.configure(bg=COLORS["error"])))
        
        # Test button (send to first number only)
        self.test_btn_frame = tk.Frame(control_frame, bg=COLORS["warning"], highlightthickness=0)
        self.test_btn_frame.pack(side="left")
        
        self.test_label = tk.Label(self.test_btn_frame, text="🧪 TEST (First Number)", 
                                  font=("Segoe UI", 11, "bold"),
                                  bg=COLORS["warning"],
                                  fg=COLORS["text_primary"],
                                  padx=25, pady=12)
        
        self.test_label.pack()
        self.test_btn_frame.bind("<Button-1>", lambda e: self.test_send())
        self.test_label.bind("<Button-1>", lambda e: self.test_send())
        self.test_btn_frame.bind("<Enter>", lambda e: (self.test_btn_frame.configure(bg="#d97706"), self.test_label.configure(bg="#d97706")))
        self.test_btn_frame.bind("<Leave>", lambda e: (self.test_btn_frame.configure(bg=COLORS["warning"]), self.test_label.configure(bg=COLORS["warning"])))
        self.test_label.bind("<Enter>", lambda e: (self.test_btn_frame.configure(bg="#d97706"), self.test_label.configure(bg="#d97706")))
        self.test_label.bind("<Leave>", lambda e: (self.test_btn_frame.configure(bg=COLORS["warning"]), self.test_label.configure(bg=COLORS["warning"])))
        
        # Log area
        log_frame = self.create_card(tab3, "Live Log")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # Log controls
        log_controls = tk.Frame(log_frame, bg=COLORS["card_bg"])
        log_controls.pack(fill="x", padx=15, pady=(15, 10))
        
        # Copy button
        copy_btn = tk.Frame(log_controls, bg=COLORS["primary"], 
                           highlightthickness=0)
        copy_btn.pack(side="left", padx=(0, 10))
        
        copy_btn_label = tk.Label(copy_btn, text="📋 Copy", 
                font=("Segoe UI", 9),
                bg=COLORS["primary"],
                fg=COLORS["text_primary"],
                padx=12, pady=6)
        copy_btn_label.pack()
        copy_btn.bind("<Button-1>", lambda e: self.copy_log())
        copy_btn_label.bind("<Button-1>", lambda e: self.copy_log())
        copy_btn.bind("<Enter>", lambda e: (copy_btn.configure(bg=COLORS["primary_dark"]), copy_btn_label.configure(bg=COLORS["primary_dark"])))
        copy_btn.bind("<Leave>", lambda e: (copy_btn.configure(bg=COLORS["primary"]), copy_btn_label.configure(bg=COLORS["primary"])))
        copy_btn_label.bind("<Enter>", lambda e: (copy_btn.configure(bg=COLORS["primary_dark"]), copy_btn_label.configure(bg=COLORS["primary_dark"])))
        copy_btn_label.bind("<Leave>", lambda e: (copy_btn.configure(bg=COLORS["primary"]), copy_btn_label.configure(bg=COLORS["primary"])))
        
        # Clear button
        clear_log_btn = tk.Frame(log_controls, bg=COLORS["warning"], 
                                highlightthickness=0)
        clear_log_btn.pack(side="left")
        
        clear_log_btn_label = tk.Label(clear_log_btn, text="🧹 Clear", 
                font=("Segoe UI", 9),
                bg=COLORS["warning"],
                fg=COLORS["text_primary"],
                padx=12, pady=6)
        clear_log_btn_label.pack()
        clear_log_btn.bind("<Button-1>", lambda e: self.clear_log_display())
        clear_log_btn_label.bind("<Button-1>", lambda e: self.clear_log_display())
        clear_log_btn.bind("<Enter>", lambda e: (clear_log_btn.configure(bg="#d97706"), clear_log_btn_label.configure(bg="#d97706")))
        clear_log_btn.bind("<Leave>", lambda e: (clear_log_btn.configure(bg=COLORS["warning"]), clear_log_btn_label.configure(bg=COLORS["warning"])))
        clear_log_btn_label.bind("<Enter>", lambda e: (clear_log_btn.configure(bg="#d97706"), clear_log_btn_label.configure(bg="#d97706")))
        clear_log_btn_label.bind("<Leave>", lambda e: (clear_log_btn.configure(bg=COLORS["warning"]), clear_log_btn_label.configure(bg=COLORS["warning"])))
        
        # Log text area
        log_container = tk.Frame(log_frame, bg=COLORS["card_bg"])
        log_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(log_container,
                                                 height=12,
                                                 font=("Consolas", 9),
                                                 wrap=tk.WORD,
                                                 bg=COLORS["log_bg"],
                                                 fg=COLORS["log_text"],
                                                 insertbackground=COLORS["log_text"],
                                                 relief="flat",
                                                 borderwidth=0)
        self.log_text.pack(fill="both", expand=True)
        
        # Configure tags for colored log messages
        self.log_text.tag_config("success", foreground="#10b981")
        self.log_text.tag_config("error", foreground="#ef4444")
        self.log_text.tag_config("warning", foreground="#f59e0b")
        self.log_text.tag_config("info", foreground="#0ea5e9")
        self.log_text.tag_config("debug", foreground="#8b5cf6")
        
        self.log_text.config(state=tk.DISABLED)
        
    def setup_status_bar(self):
        """Create status bar at bottom"""
        status_bar = tk.Frame(self.root, bg=COLORS["bg_darker"], height=30)
        status_bar.pack(side="bottom", fill="x")
        status_bar.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(status_bar,
                               textvariable=self.status_var,
                               font=self.small_font,
                               bg=COLORS["bg_darker"],
                               fg=COLORS["text_muted"])
        status_label.pack(side="left", padx=15)
        
        # Profile indicator
        profile_label = tk.Label(status_bar,
                                text="Profile: Local",
                                font=self.small_font,
                                bg=COLORS["bg_darker"],
                                fg=COLORS["text_muted"])
        profile_label.pack(side="right", padx=15)
        
    def create_card(self, parent, title):
        """Create a modern card widget"""
        frame = tk.Frame(parent, bg=COLORS["card_bg"], 
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        
        # Title
        title_label = tk.Label(frame, text=title,
                              font=self.heading_font,
                              bg=COLORS["card_bg"],
                              fg=COLORS["text_primary"])
        title_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        return frame
        
    def create_stat_card(self, parent, title, value, color):
        """Create a statistics card"""
        card = tk.Frame(parent, bg=COLORS["card_bg"],
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        
        tk.Label(card, text=title,
                font=self.small_font,
                bg=COLORS["card_bg"],
                fg=COLORS["text_secondary"]).pack(pady=(15, 5))
        
        value_label = tk.Label(card, text=value,
                             font=("Segoe UI", 24, "bold"),
                             bg=COLORS["card_bg"],
                             fg=color)
        value_label.pack(pady=(0, 15))
        
        # Store reference to update later
        if title == "Total Numbers":
            self.total_value = value_label
        elif title == "Processed":
            self.processed_value = value_label
        elif title == "Successful":
            self.success_value = value_label
        elif title == "Failed":
            self.failed_value = value_label
        
        return card
        
    def create_setting_row(self, parent, label_text, widget_creator, *args):
        """Create a setting row with label and widget"""
        row_frame = tk.Frame(parent, bg=COLORS["card_bg"])
        row_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(row_frame, text=label_text,
                font=self.body_font,
                bg=COLORS["card_bg"],
                fg=COLORS["text_primary"]).pack(side="left")
        
        widget_creator(row_frame, *args)
        
    def create_spinbox(self, parent, var_name, default, min_val, max_val):
        """Create a spinbox widget"""
        var = tk.StringVar(value=str(default))
        setattr(self, var_name, var)
        
        spinbox = tk.Spinbox(parent,
                            from_=min_val, to=max_val,
                            textvariable=var,
                            width=10,
                            font=self.body_font,
                            bg=COLORS["input_bg"],
                            fg=COLORS["text_primary"],
                            buttonbackground=COLORS["primary"],
                            relief="flat",
                            borderwidth=1,
                            highlightbackground=COLORS["border"],
                            highlightcolor=COLORS["primary"],
                            highlightthickness=1)
        spinbox.pack(side="right")
        return spinbox
        
    def create_profile_dropdown(self, parent):
        """Create profile dropdown"""
        self.profile_var = tk.StringVar(value="Real Profile (Recommended)")
        
        options = ["Real Profile (Recommended)", "Local Profile"]
        dropdown = tk.OptionMenu(parent, self.profile_var, *options)
        dropdown.config(font=self.body_font,
                       bg=COLORS["input_bg"],
                       fg=COLORS["text_primary"],
                       activebackground=COLORS["primary"],
                       activeforeground=COLORS["text_primary"],
                       relief="flat",
                       borderwidth=1,
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        dropdown["menu"].config(bg=COLORS["input_bg"], 
                               fg=COLORS["text_primary"])
        dropdown.pack(side="right")
        
    def create_log_level_dropdown(self, parent):
        """Create log level dropdown"""
        self.loglevel_var = tk.StringVar(value="Detailed")
        
        options = ["Minimal", "Detailed", "Debug"]
        dropdown = tk.OptionMenu(parent, self.loglevel_var, *options)
        dropdown.config(font=self.body_font,
                       bg=COLORS["input_bg"],
                       fg=COLORS["text_primary"],
                       activebackground=COLORS["primary"],
                       activeforeground=COLORS["text_primary"],
                       relief="flat",
                       borderwidth=1,
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        dropdown["menu"].config(bg=COLORS["input_bg"], 
                               fg=COLORS["text_primary"])
        dropdown.pack(side="right")
        
    def create_checkbox(self, parent, text, variable):
        """Create a modern checkbox"""
        def toggle():
            variable.set(not variable.get())
            check_btn.configure(bg=COLORS["primary"] if variable.get() else COLORS["card_bg"])
        
        check_frame = tk.Frame(parent, bg=COLORS["card_bg"])
        check_frame.pack(fill="x", padx=15, pady=10)
        
        check_btn = tk.Frame(check_frame, 
                            width=20, height=20,
                            bg=COLORS["primary"] if variable.get() else COLORS["card_bg"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
        check_btn.pack(side="left")
        check_btn.bind("<Button-1>", lambda e: toggle())
        
        tk.Label(check_frame, text=text,
                font=self.body_font,
                bg=COLORS["card_bg"],
                fg=COLORS["text_primary"]).pack(side="left", padx=10)
        
        # Initial state
        check_btn.configure(bg=COLORS["primary"] if variable.get() else COLORS["card_bg"])
        
    def update_message_counter(self, event=None):
        """Update character count for message"""
        text = self.message_text.get("1.0", "end-1c")
        count = len(text)
        self.msg_counter.config(text=f"{count} characters")
        
        # Also update numbers counter
        self.update_numbers_counter()
        
        # Update preview
        numbers_text = self.numbers_text.get("1.0", "end-1c")
        if text and numbers_text:
            numbers, invalid = self.validate_numbers(numbers_text)
            preview_text = f"📝 Message: '{text[:50]}{'...' if len(text) > 50 else ''}'\n"
            preview_text += f"📱 Recipients: {len(numbers)} valid number(s)\n"
            if invalid:
                preview_text += f"⚠️ Invalid: {len(invalid)} number(s) will be skipped"
            else:
                preview_text += f"✅ All numbers are valid"
            
            self.preview_label.config(text=preview_text, fg=COLORS["text_primary"])
        elif text:
            self.preview_label.config(text="Enter phone numbers to see preview", 
                                     fg=COLORS["text_muted"])
        elif numbers_text:
            self.preview_label.config(text="Enter a message to see preview", 
                                     fg=COLORS["text_muted"])
    
    def save_draft(self):
        """Save current message and numbers as draft"""
        try:
            draft = {
                "message": self.message_text.get("1.0", "end-1c"),
                "numbers": self.numbers_text.get("1.0", "end-1c"),
                "timestamp": datetime.now().isoformat()
            }
            with open(DRAFT_FILE, 'w', encoding='utf-8') as f:
                json.dump(draft, f, indent=2)
        except Exception as e:
            log_debug(f"Failed to save draft: {e}")
    
    def load_draft(self):
        """Load saved draft if exists"""
        try:
            if Path(DRAFT_FILE).exists():
                with open(DRAFT_FILE, 'r', encoding='utf-8') as f:
                    draft = json.load(f)
                
                message = draft.get("message", "").strip()
                numbers = draft.get("numbers", "").strip()
                
                if message or numbers:
                    if messagebox.askyesno("Draft Found", 
                                          "A previous draft was found. Would you like to restore it?"):
                        if message:
                            self.message_text.delete(1.0, tk.END)
                            self.message_text.insert(1.0, message)
                        if numbers:
                            self.numbers_text.delete(1.0, tk.END)
                            self.numbers_text.insert(1.0, numbers)
                        
                        self.update_message_counter()
                        self.update_numbers_counter()
                        self.log_to_gui("Draft restored", "success")
        except Exception as e:
            log_debug(f"Failed to load draft: {e}")
    
    def auto_save_draft(self):
        """Auto-save draft every 30 seconds"""
        if not self.sending:
            self.save_draft()
        self.root.after(30000, self.auto_save_draft)  # Run every 30 seconds
    
    def update_numbers_counter(self, event=None):
        """Update count of valid phone numbers"""
        numbers_text = self.numbers_text.get("1.0", "end-1c")
        if numbers_text.strip():
            numbers, invalid = self.validate_numbers(numbers_text)
            total = len(numbers) + len(invalid)
            
            if invalid:
                self.numbers_counter.config(
                    text=f"{len(numbers)} valid, {len(invalid)} invalid ({total} total)",
                    fg=COLORS["warning"])
            else:
                self.numbers_counter.config(
                    text=f"{len(numbers)} numbers (all valid)",
                    fg=COLORS["success"])
        else:
            self.numbers_counter.config(text="0 numbers", fg=COLORS["text_muted"])
        
    def validate_numbers(self, numbers_str):
        """Parse and validate phone numbers - Smart validation"""
        numbers = []
        invalid = []
        
        for num in numbers_str.split(','):
            original_num = num.strip()
            if not original_num:
                continue
                
            # Remove any non-digits
            cleaned = ''.join(filter(str.isdigit, original_num))
            
            if not cleaned:
                invalid.append(f"{original_num} (no digits)")
                continue
                
            # Handle different cases
            if cleaned.startswith('91'):
                # Already has India country code
                if len(cleaned) == 12:
                    # Perfect: 91 + 10 digits
                    numbers.append(cleaned)
                elif len(cleaned) == 10:
                    # Problem: 9140669674 - This is 10 digits starting with 91
                    invalid.append(f"{original_num} (10 digits starting with 91 - likely missing digit)")
                elif len(cleaned) > 12:
                    invalid.append(f"{original_num} (too long: {len(cleaned)} digits)")
                else:
                    invalid.append(f"{original_num} (too short: {len(cleaned)} digits)")
            else:
                # Doesn't start with 91
                if len(cleaned) == 10:
                    # Good 10-digit number, add 91
                    numbers.append('91' + cleaned)
                elif len(cleaned) > 10:
                    invalid.append(f"{original_num} ({len(cleaned)} digits without 91)")
                else:
                    invalid.append(f"{original_num} (too short: {len(cleaned)} digits)")
                    
        return numbers, invalid
        
    def load_example(self):
        """Load example message and numbers for demonstration"""
        example_message = """Hello! This is a test message from WhatsApp Bulk Sender.

You can customize this message with your own content.

Best regards,
Your Name"""
        
        example_numbers = "9876543210, 9876543211, 9876543212"
        
        if messagebox.askyesno("Load Example", 
                              "This will replace your current message and numbers with example data.\n\nContinue?"):
            self.message_text.delete(1.0, tk.END)
            self.message_text.insert(1.0, example_message)
            
            self.numbers_text.delete(1.0, tk.END)
            self.numbers_text.insert(1.0, example_numbers)
            
            self.update_message_counter()
            self.log_to_gui("Example data loaded", "info")
            messagebox.showinfo("Example Loaded", 
                              "Example message and numbers have been loaded.\n\nNote: These are dummy numbers for demonstration only.")
    
    def load_csv(self):
        """Load phone numbers from CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    numbers = []
                    for row in reader:
                        # Try common column names
                        for col in ['number', 'phone', 'mobile', 'contact', 'Phone', 'Number']:
                            if col in row and row[col]:
                                numbers.append(str(row[col]).strip())
                                break
                    
                    if numbers:
                        self.numbers_text.delete(1.0, tk.END)
                        self.numbers_text.insert(1.0, ', '.join(numbers))
                        self.update_numbers_counter()
                        self.log_to_gui(f"Loaded {len(numbers)} numbers from CSV", "success")
                        
                        # Validate and show summary
                        valid, invalid = self.validate_numbers(', '.join(numbers))
                        msg = f"Loaded {len(numbers)} numbers from CSV\n\n"
                        msg += f"Valid: {len(valid)}\nInvalid: {len(invalid)}"
                        if invalid:
                            msg += f"\n\nFirst few invalid numbers:\n" + "\n".join(invalid[:3])
                        messagebox.showinfo("CSV Loaded", msg)
                    else:
                        messagebox.showwarning("Warning", "No phone number column found in CSV")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
                
    def load_json(self):
        """Load phone numbers from JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Try different possible JSON structures
                    numbers = []
                    message = ""
                    
                    if isinstance(data, dict):
                        # Structure 1: {"numbers": [...], "message": "..."}
                        if "numbers" in data:
                            numbers = [str(num).strip() for num in data["numbers"] if str(num).strip()]
                        elif "contacts" in data:
                            numbers = [str(contact).strip() for contact in data["contacts"] if str(contact).strip()]
                        
                        if "message" in data and isinstance(data["message"], str):
                            message = data["message"].strip()
                            
                    elif isinstance(data, list):
                        # Structure 2: List of objects
                        for item in data:
                            if isinstance(item, dict):
                                for key in ['number', 'phone', 'mobile', 'contact']:
                                    if key in item:
                                        numbers.append(str(item[key]).strip())
                                        break
                            elif isinstance(item, str):
                                numbers.append(item.strip())
                    
                    if numbers:
                        self.numbers_text.delete(1.0, tk.END)
                        self.numbers_text.insert(1.0, ', '.join(numbers))
                        
                        if message:
                            self.message_text.delete(1.0, tk.END)
                            self.message_text.insert(1.0, message)
                        
                        self.update_numbers_counter()
                        self.update_message_counter()
                        self.log_to_gui(f"Loaded {len(numbers)} numbers from JSON", "success")
                        
                        # Validate and show summary
                        valid, invalid = self.validate_numbers(', '.join(numbers))
                        msg = f"Loaded {len(numbers)} numbers from JSON"
                        if message:
                            msg += " and message"
                        msg += f"\n\nValid: {len(valid)}\nInvalid: {len(invalid)}"
                        messagebox.showinfo("JSON Loaded", msg)
                    else:
                        messagebox.showwarning("Warning", "No phone numbers found in JSON")
                        
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
                
    def log_to_gui(self, message, level="info"):
        """Add message to log display with colored tags"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine prefix based on level
        if level == "success":
            prefix = "✓ "
        elif level == "error":
            prefix = "✗ "
        elif level == "warning":
            prefix = "⚠ "
        elif level == "info":
            prefix = "ℹ "
        elif level == "debug":
            prefix = "🔧 "
        else:
            prefix = ""
        
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix}{message}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def clear_log_display(self):
        """Clear the log display"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_to_gui("Log cleared", "info")
        
    def show_welcome_guide(self):
        """Show welcome guide for first-time users"""
        guide_window = tk.Toplevel(self.root)
        guide_window.title("Welcome to WhatsApp Bulk Sender Pro")
        guide_window.geometry("700x600")
        guide_window.configure(bg=COLORS["bg_dark"])
        guide_window.transient(self.root)
        guide_window.grab_set()
        
        # Center the window
        guide_window.update_idletasks()
        x = (guide_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (guide_window.winfo_screenheight() // 2) - (600 // 2)
        guide_window.geometry(f'700x600+{x}+{y}')
        
        # Title
        title_label = tk.Label(guide_window, 
                              text="📚 Quick Start Guide",
                              font=("Segoe UI", 20, "bold"),
                              bg=COLORS["bg_dark"],
                              fg=COLORS["primary"])
        title_label.pack(pady=20)
        
        # Scrollable content
        canvas = tk.Canvas(guide_window, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(guide_window, orient="vertical", command=canvas.yview)
        content_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        
        content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        # Guide content
        guide_text = """How to Use WhatsApp Bulk Sender:

📝 STEP 1: Compose Your Message
• Go to the "Compose" tab
• Type your message in the message box
• The character counter shows how long your message is

📱 STEP 2: Add Phone Numbers
• Enter phone numbers separated by commas
• Format: 10 digits (e.g., 9876543210)
• Or with country code (e.g., 919876543210)
• Invalid numbers will be highlighted

📁 STEP 3: Import Numbers (Optional)
• Click "CSV" to import from spreadsheet
• Click "JSON" to import from JSON file
• Click "Example" to see demo data

⚙️ STEP 4: Configure Settings
• Go to "Settings" tab
• Set delay between messages (recommended: 6-10 seconds)
• Choose Edge profile (Real Profile recommended)
• Kill Edge processes before starting (recommended)

🚀 STEP 5: Start Sending
• Go to "Progress" tab
• Click "START SENDING"
• If first time: Scan QR code in WhatsApp Web
• Monitor progress in real-time
• Use "STOP" to pause/cancel

⚠️ Important Tips:
• Keep delays between 6-10 seconds to avoid blocking
• Don't close the browser window while sending
• Check logs if messages fail
• Use real Edge profile for better reliability

📊 Understanding Results:
• Total: All numbers you entered
• Processed: Numbers attempted so far
• Successful: Messages sent successfully
• Failed: Messages that couldn't be sent

🔍 Troubleshooting:
• If browser won't start: Check Edge driver path in code
• If QR code stuck: Use real Edge profile
• If messages fail: Increase delay time
• Check error logs in the log folder

💡 Pro Tips:
• Test with 2-3 numbers first
• Keep messages under 500 characters
• Save your number lists as CSV files
• Monitor the live log for issues

⌨️ Keyboard Shortcuts:
• Ctrl+Q - Quit application
• Ctrl+V - Paste (auto-validates numbers)
• Tab/Shift+Tab - Navigate between fields
"""
        
        guide_label = tk.Label(content_frame,
                              text=guide_text,
                              font=("Segoe UI", 10),
                              bg=COLORS["bg_dark"],
                              fg=COLORS["text_secondary"],
                              justify=tk.LEFT,
                              padx=20,
                              pady=10)
        guide_label.pack(fill="both", expand=True)
        
        # Close button
        close_btn_frame = tk.Frame(guide_window, bg=COLORS["bg_dark"])
        close_btn_frame.pack(pady=20)
        
        close_btn = tk.Frame(close_btn_frame, bg=COLORS["primary"], highlightthickness=0)
        close_btn.pack()
        
        close_label = tk.Label(close_btn, text="Got it!", 
                              font=("Segoe UI", 11, "bold"),
                              bg=COLORS["primary"],
                              fg=COLORS["text_primary"],
                              padx=40, pady=10)
        close_label.pack()
        
        close_btn.bind("<Button-1>", lambda e: guide_window.destroy())
        close_label.bind("<Button-1>", lambda e: guide_window.destroy())
        close_btn.bind("<Enter>", lambda e: (close_btn.configure(bg=COLORS["primary_dark"]), close_label.configure(bg=COLORS["primary_dark"])))
        close_btn.bind("<Leave>", lambda e: (close_btn.configure(bg=COLORS["primary"]), close_label.configure(bg=COLORS["primary"])))
        close_label.bind("<Enter>", lambda e: (close_btn.configure(bg=COLORS["primary_dark"]), close_label.configure(bg=COLORS["primary_dark"])))
        close_label.bind("<Leave>", lambda e: (close_btn.configure(bg=COLORS["primary"]), close_label.configure(bg=COLORS["primary"])))
    
    def copy_log(self):
        """Copy log contents to clipboard"""
        try:
            self.root.clipboard_clear()
            log_content = self.log_text.get(1.0, tk.END)
            self.root.clipboard_append(log_content)
            self.log_to_gui("Log copied to clipboard", "success")
        except Exception as e:
            self.log_to_gui(f"Failed to copy log: {str(e)}", "error")
            
    def clear_logs(self):
        """Clear all log files"""
        try:
            cleared = []
            for log_file in [DEBUG_LOG, ERROR_LOG, SENT_LOG_CSV]:
                path = Path(log_file)
                if path.exists():
                    path.unlink()
                    cleared.append(log_file)
            
            if cleared:
                self.log_to_gui(f"Cleared logs: {', '.join(cleared)}", "success")
                messagebox.showinfo("Success", f"Cleared {len(cleared)} log file(s)")
            else:
                self.log_to_gui("No log files to clear", "info")
        except Exception as e:
            self.log_to_gui(f"Failed to clear logs: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to clear logs: {str(e)}")
            
    def open_log_folder(self):
        """Open the folder containing log files"""
        try:
            folder_path = Path.cwd()
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
            self.log_to_gui(f"Opened folder: {folder_path}", "info")
        except Exception as e:
            self.log_to_gui(f"Failed to open folder: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
    
    def test_send(self):
        """Send message to first number only as a test"""
        if self.sending:
            return
            
        # Get message
        message = self.message_text.get(1.0, tk.END).strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a message to test")
            return
            
        # Get and validate numbers
        numbers_str = self.numbers_text.get(1.0, tk.END).strip()
        if not numbers_str:
            messagebox.showwarning("Warning", "Please enter at least one phone number to test")
            return
            
        numbers, invalid = self.validate_numbers(numbers_str)
        
        if not numbers:
            messagebox.showwarning("Warning", "No valid phone numbers found")
            return
        
        # Use only first number for test
        test_number = numbers[0]
        
        # Confirm test
        if not messagebox.askyesno("Test Send", 
                                   f"Send test message to:\\n{test_number}\\n\\nMessage preview:\\n{message[:100]}{'...' if len(message) > 100 else ''}\\n\\nThis will open WhatsApp Web."):
            return
        
        # Set up for single message send
        self.sending = True
        self.stop_requested = False
        self.processed_count = 0
        self.total_count = 1
        self.success_count = 0
        self.failed_count = 0
        
        try:
            self.delay_between = int(self.delay_var.get())
            max_tries = int(self.tries_var.get())
        except:
            self.delay_between = 6
            max_tries = 2
        
        # Disable test button during test
        self.test_btn_frame.unbind("<Button-1>")
        self.test_label.unbind("<Button-1>")
        self.test_btn_frame.configure(bg=COLORS["text_muted"])
        self.test_label.configure(bg=COLORS["text_muted"])
        
        # Update UI
        self.update_progress(0)
        self.total_value.config(text="1")
        self.processed_value.config(text="0")
        self.success_value.config(text="0")
        self.failed_value.config(text="0")
        self.status_label.config(text="Testing...")
        self.status_var.set("Testing...")
        
        self.clear_log_display()
        self.log_to_gui("Starting test send...", "info")
        
        # Start test in background thread
        threading.Thread(target=self.test_send_thread,
                        args=([test_number], message, max_tries),
                        daemon=True).start()
    
    def test_send_thread(self, numbers, message, max_tries):
        """Thread for test sending"""
        try:
            self.log_to_gui("Initializing browser for test...", "info")
            
            # Optionally kill edge processes
            if self.kill_edge_var.get():
                self.log_to_gui("Killing Edge processes...", "warning")
                self.kill_edge_processes()
            
            # Start Edge driver
            try:
                self.driver = self.start_edge_driver()
                self.log_to_gui("Browser started successfully", "success")
            except Exception as e:
                error_msg = f"Failed to start Edge: {str(e)}"
                self.log_to_gui(error_msg, "error")
                self.test_complete(False)
                return
            
            # Wait for WhatsApp to load
            self.log_to_gui("Loading WhatsApp Web...", "info")
            if not self.wait_for_whatsapp_ready(self.driver):
                self.log_to_gui("WhatsApp not ready. Please scan QR code if needed.", "error")
                self.test_complete(False)
                return
            
            self.log_to_gui("WhatsApp loaded successfully!", "success")
            
            # Send test message
            number = numbers[0]
            self.log_to_gui(f"Sending test message to {number}...", "info")
            
            success, note = self.send_via_wa_me(self.driver, number, message, max_tries)
            
            self.processed_count = 1
            self.update_progress(100)
            self.root.after(0, self.processed_value.config, {"text": "1"})
            
            if success:
                self.success_count = 1
                self.log_to_gui(f"✓ Test message sent successfully to {number}!", "success")
                self.root.after(0, self.success_value.config, {"text": "1"})
                self.test_complete(True)
            else:
                self.failed_count = 1
                self.log_to_gui(f"✗ Test failed: {note}", "error")
                self.root.after(0, self.failed_value.config, {"text": "1"})
                self.test_complete(False)
                
        except Exception as e:
            self.log_to_gui(f"Test error: {str(e)}", "error")
            log_exception(e)
            self.test_complete(False)
    
    def test_complete(self, success):
        """Complete test send"""
        self.sending = False
        
        # Re-enable test button
        self.root.after(0, lambda: self.test_btn_frame.bind("<Button-1>", lambda e: self.test_send()))
        self.root.after(0, lambda: self.test_label.bind("<Button-1>", lambda e: self.test_send()))
        self.root.after(0, lambda: self.test_btn_frame.configure(bg=COLORS["warning"]))
        self.root.after(0, lambda: self.test_label.configure(bg=COLORS["warning"]))
        
        if success:
            self.root.after(0, lambda: self.status_label.config(text="Test successful!"))
            self.root.after(0, lambda: self.status_var.set("Test successful!"))
            self.root.after(0, lambda: messagebox.showinfo("Test Complete", 
                                                         "✅ Test message sent successfully!\\n\\nYou can now send to all numbers."))
        else:
            self.root.after(0, lambda: self.status_label.config(text="Test failed"))
            self.root.after(0, lambda: self.status_var.set("Test failed"))
            self.root.after(0, lambda: messagebox.showwarning("Test Failed", 
                                                            "❌ Test message failed.\\n\\nPlease check the logs and try again."))
        
        # Close browser
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_to_gui("Browser closed", "info")
            except:
                pass
            
    def start_sending(self):
        if self.sending:
            return
            
        # Get message
        message = self.message_text.get(1.0, tk.END).strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a message")
            return
            
        # Get and validate numbers
        numbers_str = self.numbers_text.get(1.0, tk.END).strip()
        if not numbers_str:
            messagebox.showwarning("Warning", "Please enter phone numbers")
            return
            
        numbers, invalid = self.validate_numbers(numbers_str)
        
        if invalid:
            invalid_list = "\n".join(invalid[:5])
            if len(invalid) > 5:
                invalid_list += f"\n... and {len(invalid) - 5} more"
                
            if not messagebox.askyesno("Invalid Numbers",
                                      f"Found {len(invalid)} invalid numbers:\n{invalid_list}\n\nContinue with {len(numbers)} valid numbers?"):
                return
                
        if not numbers:
            messagebox.showwarning("Warning", "No valid phone numbers found")
            return
            
        # Confirm before starting
        confirm_msg = f"Send message to {len(numbers)} numbers?\n\n"
        confirm_msg += f"Message: {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
        confirm_msg += f"Delay between messages: {self.delay_var.get()} seconds"
        
        if not messagebox.askyesno("Confirm Sending", confirm_msg):
            return
            
        # Update UI state
        self.sending = True
        self.stop_requested = False
        self.processed_count = 0
        self.total_count = len(numbers)
        self.success_count = 0
        self.failed_count = 0
        
        # Get settings from GUI
        try:
            self.delay_between = int(self.delay_var.get())
            max_tries = int(self.tries_var.get())
        except:
            self.delay_between = 6
            max_tries = 2
            
        # Disable start button, enable stop button
        self.start_btn_frame.unbind("<Button-1>")
        self.start_label.unbind("<Button-1>")
        self.start_btn_frame.configure(bg=COLORS["text_muted"])
        self.start_label.configure(bg=COLORS["text_muted"])
        
        self.stop_btn_frame.bind("<Button-1>", lambda e: self.stop_sending())
        self.stop_label.bind("<Button-1>", lambda e: self.stop_sending())
        
        # Reset progress
        self.update_progress(0)
        self.total_value.config(text=str(self.total_count))
        self.processed_value.config(text="0")
        self.success_value.config(text="0")
        self.failed_value.config(text="0")
        self.status_label.config(text="Starting...")
        self.status_var.set("Starting...")
        
        # Clear log display
        self.clear_log_display()
        
        # Start sending in background thread
        threading.Thread(target=self.send_messages_thread,
                         args=(numbers, message, max_tries),
                         daemon=True).start()
        
    def send_messages_thread(self, numbers, message, max_tries):
        try:
            self.log_to_gui("Starting WhatsApp bulk sender...", "info")
            self.update_status("Initializing...")
            
            # Optionally kill edge processes
            if self.kill_edge_var.get():
                self.log_to_gui("Killing Edge processes...", "warning")
                self.kill_edge_processes()
                
            # Start Edge driver
            self.log_to_gui("Starting Edge browser...", "info")
            self.update_status("Starting browser...")
            
            try:
                self.driver = self.start_edge_driver()
                self.log_to_gui("Browser started successfully", "success")
            except Exception as e:
                error_msg = f"Failed to start Edge: {str(e)}"
                self.log_to_gui(error_msg, "error")
                self.update_status("Browser start failed")
                self.sending_complete(False)
                return
                
            # Wait for WhatsApp to load
            self.log_to_gui("Loading WhatsApp Web...", "info")
            self.update_status("Loading WhatsApp...")
            
            if not self.wait_for_whatsapp_ready(self.driver):
                self.log_to_gui("WhatsApp not ready. Please scan QR code if needed.", "error")
                self.update_status("WhatsApp not ready")
                self.sending_complete(False)
                return
                
            self.log_to_gui("WhatsApp loaded successfully!", "success")
            self.log_to_gui(f"Starting to send to {len(numbers)} numbers...", "info")
            
            # Send messages
            for idx, number in enumerate(numbers, start=1):
                if self.stop_requested:
                    self.log_to_gui("Sending stopped by user", "warning")
                    break
                    
                self.processed_count = idx
                progress = (idx / len(numbers)) * 100
                
                self.root.after(0, self.update_progress, progress)
                self.root.after(0, self.processed_value.config, {"text": str(idx)})
                
                self.log_to_gui(f"[{idx}/{len(numbers)}] Sending to {number}...", "info")
                
                success, note = self.send_via_wa_me(self.driver, number, message, max_tries)
                
                if success:
                    self.success_count += 1
                    self.log_to_gui(f"✓ Successfully sent to {number}", "success")
                    self.root.after(0, self.success_value.config, {"text": str(self.success_count)})
                else:
                    self.failed_count += 1
                    self.log_to_gui(f"✗ Failed to send to {number}: {note}", "error")
                    self.root.after(0, self.failed_value.config, {"text": str(self.failed_count)})
                    
                # Log to CSV
                self.append_sent_log({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "number": number,
                    "message": message,
                    "status": "OK" if success else "FAILED",
                    "note": note
                })
                
                # Update status
                self.update_status(f"Sending... {idx}/{len(numbers)}")
                
                # Delay between messages
                if idx < len(numbers) and not self.stop_requested:
                    self.log_to_gui(f"Waiting {self.delay_between} seconds before next...", "debug")
                    for i in range(self.delay_between):
                        if self.stop_requested:
                            break
                        time.sleep(1)
                    
            if not self.stop_requested:
                self.log_to_gui(f"All messages processed! Sent: {self.success_count}, Failed: {self.failed_count}", "success")
                self.update_status("Complete")
                self.sending_complete(True)
            else:
                self.log_to_gui(f"Stopped. Processed: {self.processed_count}, Sent: {self.success_count}, Failed: {self.failed_count}", "warning")
                self.sending_complete(False)
                
        except Exception as e:
            self.log_to_gui(f"Unexpected error: {str(e)}", "error")
            log_exception(e)
            self.update_status("Error occurred")
            self.sending_complete(False)
            
    def stop_sending(self):
        if not self.sending:
            return
            
        self.stop_requested = True
        try:
            self.stop_btn_frame.unbind("<Button-1>")
            self.stop_label.unbind("<Button-1>")
        except:
            pass
        self.log_to_gui("Stop requested. Finishing current message...", "warning")
        self.update_status("Stopping...")
        
    def sending_complete(self, success):
        self.sending = False
        self.stop_requested = False
        
        # Re-enable start button
        self.root.after(0, lambda: self.start_btn_frame.bind("<Button-1>", lambda e: self.start_sending()))
        self.root.after(0, lambda: self.start_label.bind("<Button-1>", lambda e: self.start_sending()))
        self.root.after(0, lambda: self.start_btn_frame.configure(bg=COLORS["success"]))
        self.root.after(0, lambda: self.start_label.configure(bg=COLORS["success"]))
        
        # Disable stop button
        def unbind_stop():
            try:
                self.stop_btn_frame.unbind("<Button-1>")
                self.stop_label.unbind("<Button-1>")
            except:
                pass
        self.root.after(0, unbind_stop)
        self.root.after(0, lambda: self.stop_label.config(text="⏹️ STOP"))
        
        if success:
            self.root.after(0, lambda: self.status_label.config(text="Complete"))
            self.root.after(0, lambda: self.status_var.set("Complete"))
            
            # Save session stats
            self.save_session_stats()
            
            self.root.after(0, lambda: messagebox.showinfo("Complete", 
                                                         f"✅ Processing Complete!\n\n"
                                                         f"Total: {self.total_count}\n"
                                                         f"Sent: {self.success_count}\n"
                                                         f"Failed: {self.failed_count}"))
        else:
            self.root.after(0, lambda: self.status_label.config(text="Stopped"))
            self.root.after(0, lambda: self.status_var.set("Stopped"))
            
        # Close browser
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_to_gui("Browser closed", "info")
            except:
                pass
                
    def update_progress(self, percentage):
        width = self.progress_frame_inner.winfo_width()
        progress_width = int((percentage / 100) * width)
        self.progress_bar.configure(width=progress_width)
        self.progress_label.configure(text=f"{int(percentage)}%")
        
    def update_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))
        self.root.after(0, lambda: self.status_var.set(text))
        
    def kill_edge_processes(self):
        try:
            if platform.system().lower().startswith("win"):
                result = subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_to_gui("Edge processes killed", "success")
                else:
                    self.log_to_gui("No Edge processes to kill", "info")
                time.sleep(1)
            else:
                subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
                time.sleep(1)
        except Exception as e:
            self.log_to_gui(f"Failed to kill Edge processes: {e}", "warning")
            
    def start_edge_driver(self):
        # Validate Edge driver exists
        if not Path(EDGE_DRIVER_PATH).exists():
            error_msg = f"Edge driver not found at: {EDGE_DRIVER_PATH}\n\nPlease update EDGE_DRIVER_PATH in the code."
            self.log_to_gui(error_msg, "error")
            messagebox.showerror("Driver Not Found", error_msg)
            raise FileNotFoundError(error_msg)
        
        def _build_options(profile_path: str, profile_dir: str = None):
            opts = EdgeOptions()
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument(f"--remote-debugging-port={REMOTE_DEBUGGING_PORT}")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument(f"--user-data-dir={profile_path}")
            if profile_dir:
                opts.add_argument(f"--profile-directory={profile_dir}")
            return opts
            
        service = EdgeService(executable_path=EDGE_DRIVER_PATH)
        
        # Check which profile to use
        profile_choice = self.profile_var.get() if hasattr(self, 'profile_var') else "Real Profile (Recommended)"
        
        if "Real" in profile_choice and USE_REAL_EDGE_PROFILE:
            try:
                self.log_to_gui("Using real Edge profile...", "info")
                opts = _build_options(EDGE_USER_DATA_DIR, EDGE_PROFILE_DIR_NAME)
                driver = webdriver.Edge(service=service, options=opts)
                driver.maximize_window()
                self.log_to_gui("Using real Edge profile (Profile 1)", "success")
                return driver
            except Exception as e:
                self.log_to_gui(f"Failed with real profile: {e}. Switching to local profile...", "warning")
                # Fall through to local profile
                
        # Use local profile
        self.log_to_gui("Using local Edge profile...", "info")
        local_profile_dir_str = str(LOCAL_PROFILE_DIR.resolve())
        opts2 = _build_options(local_profile_dir_str, None)
        service2 = EdgeService(executable_path=EDGE_DRIVER_PATH)
        driver2 = webdriver.Edge(service=service2, options=opts2)
        driver2.maximize_window()
        self.log_to_gui("Local profile created/loaded", "success")
        return driver2
        
    def wait_for_whatsapp_ready(self, driver, timeout=60):
        try:
            driver.get("https://web.whatsapp.com/")
            self.log_to_gui("Opened WhatsApp Web", "info")
            
            # Wait for WhatsApp to load
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "pane-side"))
            )
            self.log_to_gui("WhatsApp Web is ready", "success")
            return True
        except TimeoutException:
            self.log_to_gui("WhatsApp took too long to load. Please scan QR code manually.", "error")
            # Keep browser open for manual QR scan
            return False
        except Exception as e:
            self.log_to_gui(f"Error loading WhatsApp: {e}", "error")
            return False
            
    def send_via_wa_me(self, driver, number, message, max_tries):
        for attempt in range(1, max_tries + 1):
            try:
                encoded = urllib.parse.quote_plus(message)
                url = f"https://web.whatsapp.com/send/?phone={number}&text={encoded}"
                
                if attempt > 1:
                    self.log_to_gui(f"  Retry {attempt}/{max_tries} for {number}", "warning")
                
                driver.get(url)
                time.sleep(DELAY_AFTER_OPEN)
                
                try:
                    send_btn = WebDriverWait(driver, WAIT_FOR_INPUT_TIMEOUT).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
                    )
                    send_btn.click()
                    time.sleep(0.5)
                    return True, "Sent successfully"
                except TimeoutException:
                    if attempt < max_tries:
                        time.sleep(1)
                        continue
                    return False, "Send button not found (page may not have loaded)"
                except Exception as e:
                    if attempt < max_tries:
                        time.sleep(1)
                        continue
                    return False, f"Send exception: {str(e)}"
            except WebDriverException as e:
                if attempt < max_tries:
                    time.sleep(1)
                    continue
                return False, f"Browser error: {str(e)}"
            except Exception as exc:
                if attempt < max_tries:
                    time.sleep(1)
                    continue
                return False, f"Unexpected error: {str(exc)}"
        return False, "All attempts failed"
    
    def save_session_stats(self):
        """Save session statistics to file"""
        try:
            stats_file = Path("session_stats.json")
            stats = {
                "timestamp": datetime.now().isoformat(),
                "total": self.total_count,
                "processed": self.processed_count,
                "successful": self.success_count,
                "failed": self.failed_count,
                "success_rate": f"{(self.success_count/self.total_count*100) if self.total_count > 0 else 0:.1f}%"
            }
            
            # Append to history
            history = []
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = []
                    except:
                        history = []
            
            history.append(stats)
            # Keep only last 50 sessions
            history = history[-50:]
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
            
            log_debug(f"Session stats saved: {stats}")
        except Exception as e:
            log_error(f"Failed to save session stats: {e}")
        
    def append_sent_log(self, row):
        try:
            p = Path(SENT_LOG_CSV)
            exists = p.exists()
            with p.open("a", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["time","number","message","status","note"])
                if not exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            log_error(f"Failed to write to CSV: {e}")
            
    def on_closing(self):
        if self.sending:
            if messagebox.askyesno("Confirm Exit", 
                                  f"Sending is in progress!\n\nProcessed: {self.processed_count}/{self.total_count}\nSuccessful: {self.success_count}\nFailed: {self.failed_count}\n\nAre you sure you want to quit?\n\nThe current message will complete before exiting."):
                self.stop_requested = True
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                time.sleep(0.5)
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    
    # Set window icon (optional)
    try:
        root.iconbitmap('icon.ico')  # Add an icon file if available
    except:
        pass
    
    app = WhatsAppBulkSenderGUI(root)
    
    # Bind Ctrl+Q to quit
    root.bind('<Control-q>', lambda e: app.on_closing())
    
    root.mainloop()

if __name__ == "__main__":
    main()