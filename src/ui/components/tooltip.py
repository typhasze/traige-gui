import tkinter as tk
from tkinter import ttk


class ToolTip:
    def __init__(self, widget, text, delay_ms=400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._tip_window = None
        self._after_id = None

        self.widget.bind("<Enter>", self._schedule_show, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")
        self.widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule_show(self, _event=None):
        self._cancel_scheduled_show()
        if not self.text:
            return
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_scheduled_show(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                return
            self._after_id = None

    def _show(self):
        if self._tip_window is not None:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self._tip_window,
            text=self.text,
            padding=(8, 4),
            relief="solid",
            borderwidth=1,
            justify="left",
        )
        label.pack()

    def _hide(self, _event=None):
        self._cancel_scheduled_show()
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except tk.TclError:
                return
            self._tip_window = None


def attach_tooltip(widget, text):
    if text:
        ToolTip(widget, text)
