"""Minimal GUI stub for MVP."""

from __future__ import annotations

import tkinter as tk


def run_gui() -> None:
    root = tk.Tk()
    root.title("voice_control_pc")
    root.geometry("520x220")

    title = tk.Label(root, text="voice_control_pc", font=("Segoe UI", 16, "bold"))
    title.pack(pady=(20, 10))

    text = (
        "GUI-каркас создан.\n"
        "Следующий этап: очередь событий, push-to-talk, лог и статус ASR/NLU."
    )
    description = tk.Label(root, text=text, justify="center", font=("Segoe UI", 11))
    description.pack(padx=20, pady=10)

    close_button = tk.Button(root, text="Закрыть", command=root.destroy)
    close_button.pack(pady=10)

    root.mainloop()
