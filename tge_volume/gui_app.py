"""Lightweight Tkinter launcher to run the CLI from a double-clickable macOS app bundle."""
from __future__ import annotations

import contextlib
import io
import threading
from pathlib import Path
from tkinter import END, DISABLED, NORMAL, Tk, Text, filedialog, messagebox, ttk

from .cli import main as cli_main


DEFAULT_OUTPUT = Path.home() / "Desktop" / "trading_flow_15m.csv"


def _append_log(widget: Text, text: str) -> None:
    widget.configure(state=NORMAL)
    widget.insert(END, text)
    widget.see(END)
    widget.configure(state=DISABLED)


def _run_cli_async(symbol: str, output_csv: str, log_widget: Text, root: Tk) -> None:
    def runner() -> None:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                cli_main([symbol, "--output-csv", output_csv])
            _append_log(log_widget, buf.getvalue())
            messagebox.showinfo("Complete", "Processing finished. Check the log output and CSV file.", parent=root)
        except Exception as exc:  # pragma: no cover - UI convenience
            _append_log(log_widget, buf.getvalue())
            _append_log(log_widget, f"\nERROR: {exc}\n")
            messagebox.showerror("Failed", f"Run failed: {exc}", parent=root)

    threading.Thread(target=runner, daemon=True).start()


def main() -> None:
    root = Tk()
    root.title("TGE Volume Explorer")
    root.geometry("720x480")

    content = ttk.Frame(root, padding=12)
    content.pack(fill="both", expand=True)

    # Form controls
    form = ttk.Frame(content)
    form.pack(fill="x", pady=(0, 10))

    ttk.Label(form, text="Token ticker (no $)").grid(column=0, row=0, sticky="w")
    symbol_var = ttk.Entry(form, width=40)
    symbol_var.grid(column=0, row=1, sticky="we", padx=(0, 12))
    symbol_var.insert(0, "ELIZAOS")

    ttk.Label(form, text="Output CSV path").grid(column=1, row=0, sticky="w")
    path_frame = ttk.Frame(form)
    path_frame.grid(column=1, row=1, sticky="we")

    output_var = ttk.Entry(path_frame, width=40)
    output_var.pack(side="left", fill="x", expand=True)
    output_var.insert(0, str(DEFAULT_OUTPUT))

    def choose_file() -> None:
        path = filedialog.asksaveasfilename(
            parent=root,
            title="Save 15m trading flow CSV",
            defaultextension=".csv",
            initialfile=DEFAULT_OUTPUT.name,
            initialdir=DEFAULT_OUTPUT.parent,
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
        )
        if path:
            output_var.delete(0, END)
            output_var.insert(0, path)

    ttk.Button(path_frame, text="Browse", command=choose_file).pack(side="left", padx=(8, 0))

    # Log output
    log = Text(content, height=20, wrap="word", state=DISABLED)
    log.pack(fill="both", expand=True)

    def on_run() -> None:
        symbol = symbol_var.get().strip()
        output_csv = output_var.get().strip()
        if not symbol:
            messagebox.showwarning("Missing symbol", "Enter a token ticker.", parent=root)
            return
        if not output_csv:
            messagebox.showwarning("Missing path", "Choose an output CSV path.", parent=root)
            return

        _append_log(log, f"\nRunning: {symbol} -> {output_csv}\n")
        _run_cli_async(symbol, output_csv, log, root)

    actions = ttk.Frame(content)
    actions.pack(fill="x", pady=(10, 0))
    ttk.Button(actions, text="Run", command=on_run).pack(side="right")

    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
