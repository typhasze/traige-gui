#!/usr/bin/env python3
# filepath: /python-gui-app/python-gui-app/src/main.py
import os
import sys
import tkinter as tk

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.gui_manager import FoxgloveAppGUIManager  # noqa: E402


def main():
    root = tk.Tk()
    gui = FoxgloveAppGUIManager(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
