#!/usr/bin/env python3
import os
import sys
import tkinter as tk

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.ui.gui_manager import FoxgloveAppGUIManager  # noqa: E402


def main():
    root = tk.Tk()
    gui = FoxgloveAppGUIManager(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
