#!/usr/bin/env python3
"""A simple, friendly desktop interface for eSpeak NG."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from espeak_gui_core import (
    LANGUAGES,
    espeak_error,
    pitch_for,
    pitch_limits,
    safe_recording_name,
    voice_for,
)


APP_NAME = "eSpeak NG Studio"
DEFAULTS = {
    "language": "English",
    "accent": "American",
    "gender": "Male",
    "speed": 175,
    "pitch": 50,
}


class EspeakGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.config_path = self._config_path()
        self.settings = self._load_settings()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.speech_process: subprocess.Popen[str] | None = None
        self.busy = False
        self.espeak_path = shutil.which("espeak-ng")
        self.ffmpeg_path = shutil.which("ffmpeg")

        self._set_style()
        self._build_ui()
        self._language_changed(save=False)
        self._voice_changed(save=False)
        self._size_window()
        self._update_dependency_state()
        self.root.after(100, self._poll_events)

    @staticmethod
    def _config_path() -> Path:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "espeak-ng-studio" / "settings.json"

    def _load_settings(self) -> dict[str, object]:
        try:
            loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            loaded = {}
        settings = DEFAULTS.copy()
        settings.update({key: loaded[key] for key in DEFAULTS if key in loaded})
        if settings["language"] not in LANGUAGES:
            settings["language"] = DEFAULTS["language"]
        if settings["gender"] not in ("Male", "Female"):
            settings["gender"] = DEFAULTS["gender"]
        for key, minimum, maximum in (("speed", 80, 450), ("pitch", 0, 99)):
            try:
                settings[key] = max(minimum, min(maximum, int(settings[key])))
            except (TypeError, ValueError):
                settings[key] = DEFAULTS[key]
        return settings

    def _save_settings(self) -> None:
        settings = {
            "language": self.language_var.get(),
            "accent": self.accent_var.get(),
            "gender": self.gender_var.get(),
            "speed": int(self.speed_var.get()),
            "pitch": int(self.pitch_var.get()),
        }
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _set_style(self) -> None:
        self.colors = {
            "page": "#eef3f7",
            "card": "#ffffff",
            "ink": "#173042",
            "muted": "#667b89",
            "primary": "#176b87",
            "primary_active": "#0f5870",
            "accent": "#2aa198",
            "field": "#f6f9fb",
            "border": "#d7e2e8",
        }
        self.root.configure(bg=self.colors["page"])
        style = ttk.Style(self.root)
        for theme in ("clam", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("TFrame", background=self.colors["page"])
        style.configure("Header.TFrame", background=self.colors["primary"])
        style.configure("Card.TFrame", background=self.colors["card"], relief="solid", borderwidth=1)
        style.configure("CardBody.TFrame", background=self.colors["card"])
        style.configure("TLabel", background=self.colors["page"], foreground=self.colors["ink"], font=("Sans", 10))
        style.configure("Card.TLabel", background=self.colors["card"], foreground=self.colors["ink"], font=("Sans", 10))
        style.configure(
            "Section.TLabel",
            background=self.colors["card"],
            foreground=self.colors["primary"],
            font=("Sans", 10, "bold"),
        )
        style.configure(
            "Title.TLabel",
            background=self.colors["primary"],
            foreground="#ffffff",
            font=("Sans", 23, "bold"),
        )
        style.configure(
            "HeaderSub.TLabel",
            background=self.colors["primary"],
            foreground="#d8eef4",
            font=("Sans", 10),
        )
        style.configure("Sub.TLabel", background=self.colors["page"], foreground=self.colors["muted"], font=("Sans", 10))
        style.configure("Hint.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Sans", 9))
        style.configure(
            "Primary.TButton",
            background=self.colors["primary"],
            foreground="#ffffff",
            font=("Sans", 10, "bold"),
            padding=(18, 10),
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["primary_active"]), ("disabled", "#9aabb3")],
        )
        style.configure("Accent.TButton", foreground=self.colors["primary"], font=("Sans", 10, "bold"), padding=(14, 9))
        style.configure("TButton", padding=(13, 9))
        style.configure("TCombobox", padding=6)
        style.configure("Horizontal.TScale", troughcolor="#d9e6eb", background=self.colors["primary"])

    def _size_window(self) -> None:
        """Choose an initial size after Tk knows how much room the UI needs."""
        self.root.update_idletasks()
        requested_width = self.root.winfo_reqwidth()
        requested_height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(max(880, requested_width + 24), max(700, screen_width - 60))
        height = min(max(760, requested_height + 24), max(640, screen_height - 80))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(720, width), min(650, height))

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(26, 18), style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="A simple workspace for natural, shareable speech.",
            style="HeaderSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        outer = ttk.Frame(self.root, padding=(24, 18, 24, 18))
        outer.pack(fill="both", expand=True)

        text_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        text_card.pack(fill="both", expand=True)
        ttk.Label(text_card, text="TEXT TO SPEAK", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        text_frame = ttk.Frame(text_card, style="CardBody.TFrame")
        text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            text_frame,
            height=9,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            font=("Sans", 11),
            background=self.colors["field"],
            foreground=self.colors["ink"],
            insertbackground=self.colors["primary"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        controls = ttk.Frame(outer, style="Card.TFrame", padding=16)
        controls.pack(fill="x", pady=(14, 0))
        controls.columnconfigure((0, 1, 2), weight=1, uniform="selectors")
        ttk.Label(controls, text="VOICE SETTINGS", style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        self.language_var = tk.StringVar(value=str(self.settings["language"]))
        self.gender_var = tk.StringVar(value=str(self.settings["gender"]))
        self.accent_var = tk.StringVar(value=str(self.settings["accent"]))
        self._selector(controls, "Language", self.language_var, list(LANGUAGES), 0, self._language_changed)
        self._selector(controls, "Voice", self.gender_var, ["Male", "Female"], 1, self._voice_changed)
        self.accent_box = self._selector(controls, "Accent", self.accent_var, [], 2, self._selection_changed)

        slider_frame = ttk.Frame(controls, style="Card.TFrame")
        slider_frame.configure(style="CardBody.TFrame")
        slider_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        slider_frame.columnconfigure(1, weight=1)
        self.speed_var = tk.DoubleVar(value=float(self.settings["speed"]))
        self.pitch_var = tk.DoubleVar(value=float(self.settings["pitch"]))
        self.speed_value = ttk.Label(slider_frame, width=4, style="Card.TLabel")
        self.pitch_value = ttk.Label(slider_frame, width=4, style="Card.TLabel")
        self._slider(slider_frame, "Speed", self.speed_var, 80, 450, 0, self.speed_value)
        self._slider(slider_frame, "Pitch", self.pitch_var, 0, 99, 1, self.pitch_value)
        self.voice_hint = ttk.Label(controls, style="Hint.TLabel")
        self.voice_hint.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(14, 0))
        self.preview_button = ttk.Button(actions, text="▶  Preview", style="Primary.TButton", command=self.preview)
        self.preview_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="■  Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="Save MP3…", style="Accent.TButton", command=self.save_mp3)
        self.save_button.pack(side="right")

        self.status_var = tk.StringVar(value="Ready — previews are not saved.")
        ttk.Label(outer, textvariable=self.status_var, style="Sub.TLabel").pack(anchor="w", pady=(10, 0))

    def _selector(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        column: int,
        callback: object,
    ) -> ttk.Combobox:
        group = ttk.Frame(parent, style="CardBody.TFrame")
        group.grid(row=1, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0))
        ttk.Label(group, text=label, style="Card.TLabel").pack(anchor="w", pady=(0, 5))
        box = ttk.Combobox(group, textvariable=variable, values=values, state="readonly")
        box.pack(fill="x")
        box.bind("<<ComboboxSelected>>", callback)
        return box

    def _slider(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.DoubleVar,
        minimum: int,
        maximum: int,
        row: int,
        value_label: ttk.Label,
    ) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel", width=7).grid(row=row, column=0, sticky="w", pady=5)
        scale = ttk.Scale(
            parent,
            from_=minimum,
            to=maximum,
            variable=variable,
            command=lambda _value: self._sliders_changed(),
        )
        scale.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        if label == "Pitch":
            self.pitch_scale = scale
        value_label.grid(row=row, column=2, sticky="e")
        self._sliders_changed()

    def _language_changed(self, _event: object = None, save: bool = True) -> None:
        details = LANGUAGES[self.language_var.get()]
        accents = list(details.accents)
        self.accent_box.configure(values=accents)
        if accents:
            if self.accent_var.get() not in accents:
                self.accent_var.set(accents[0])
            self.accent_box.configure(state="readonly")
        else:
            self.accent_var.set("")
            self.accent_box.configure(state="disabled")
        self._update_voice_hint()
        if save:
            self._save_settings()

    def _selection_changed(self, _event: object = None) -> None:
        self._update_voice_hint()
        self._save_settings()

    def _voice_changed(self, _event: object = None, save: bool = True) -> None:
        minimum, maximum = pitch_limits(self.gender_var.get())
        self.pitch_scale.configure(from_=minimum, to=maximum)
        adjusted = pitch_for(self.gender_var.get(), self.pitch_var.get())
        if adjusted != int(self.pitch_var.get()):
            self.pitch_var.set(adjusted)
        self._update_voice_hint()
        self._sliders_changed()
        if save:
            self._save_settings()

    def _selected_voice(self) -> str:
        return voice_for(self.language_var.get(), self.accent_var.get(), self.gender_var.get())

    def _update_voice_hint(self) -> None:
        if not hasattr(self, "voice_hint"):
            return
        voice = self._selected_voice()
        if self.gender_var.get() == "Female":
            description = "Female profile · pitch 55–99"
        else:
            description = "Male profile · pitch 0–99"
        self.voice_hint.configure(text=f"{description} · eSpeak voice: {voice}")

    def _validate_selected_voice(self) -> bool:
        """Ask eSpeak to load the exact voice without producing audio."""
        if not self.espeak_path:
            return False
        voice = self._selected_voice()
        try:
            checked = subprocess.run(
                [self.espeak_path, "-q", "-v", voice, "voice check"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            diagnostic = str(exc)
        else:
            diagnostic = espeak_error(checked.returncode, checked.stderr)
        if diagnostic:
            self.status_var.set(f"Could not load voice {voice}.")
            messagebox.showerror(
                APP_NAME,
                f"eSpeak NG could not load the requested voice ({voice}).\n\n"
                f"{diagnostic}\n\n"
                "No fallback voice was played.",
                parent=self.root,
            )
            return False
        return True

    def _sliders_changed(self) -> None:
        if hasattr(self, "speed_value"):
            self.speed_value.configure(text=str(int(self.speed_var.get())))
            self.pitch_value.configure(text=str(int(self.pitch_var.get())))
            self._save_settings()

    def _update_dependency_state(self) -> None:
        missing = []
        if not self.espeak_path:
            missing.append("eSpeak NG")
            self.preview_button.configure(state="disabled")
        if not self.ffmpeg_path:
            missing.append("FFmpeg")
            self.save_button.configure(state="disabled")
        if missing:
            names = " and ".join(missing)
            self.status_var.set(f"Missing {names}. Close the app and run ./run-espeak-gui for installation help.")

    def _speech_args(self) -> list[str]:
        return [
            self.espeak_path or "espeak-ng",
            "-v",
            self._selected_voice(),
            "-s",
            str(int(self.speed_var.get())),
            "-p",
            str(pitch_for(self.gender_var.get(), self.pitch_var.get())),
        ]

    def _entered_text(self) -> str | None:
        value = self.text.get("1.0", "end-1c").strip()
        if not value:
            messagebox.showinfo(APP_NAME, "Enter some text first.", parent=self.root)
            self.text.focus_set()
            return None
        return value

    def preview(self) -> None:
        value = self._entered_text()
        if value is None or not self.espeak_path or not self._validate_selected_voice():
            return
        self.stop()
        self._save_settings()
        try:
            self.speech_process = subprocess.Popen(
                [*self._speech_args(), value],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not start eSpeak NG:\n{exc}", parent=self.root)
            return
        self.preview_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Playing preview — no audio file has been created.")
        threading.Thread(target=self._wait_for_preview, args=(self.speech_process,), daemon=True).start()

    def _wait_for_preview(self, process: subprocess.Popen[str]) -> None:
        _stdout, stderr = process.communicate()
        self.events.put(("preview_done", (process, process.returncode, stderr)))

    def stop(self) -> None:
        process = self.speech_process
        if process is not None and process.poll() is None:
            process.terminate()
        self.speech_process = None
        if self.espeak_path and not self.busy:
            self.preview_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def save_mp3(self) -> None:
        value = self._entered_text()
        if (
            value is None
            or not self.espeak_path
            or not self.ffmpeg_path
            or not self._validate_selected_voice()
        ):
            return
        default_name = f"recording-{datetime.now():%Y-%m-%d-%H%M%S}"
        requested = simpledialog.askstring(
            "Save MP3",
            "Recording name:",
            initialvalue=default_name,
            parent=self.root,
        )
        if requested is None:
            return
        try:
            filename = safe_recording_name(requested)
        except ValueError as exc:
            messagebox.showwarning(APP_NAME, str(exc), parent=self.root)
            return
        recordings = Path.cwd() / "espeak-recordings"
        destination = recordings / filename
        if destination.exists() and not messagebox.askyesno(
            APP_NAME,
            f"{filename} already exists. Replace it?",
            parent=self.root,
        ):
            return

        self.stop()
        self._save_settings()
        self._set_busy(True)
        self.status_var.set("Creating MP3…")
        speech_args = self._speech_args()
        threading.Thread(
            target=self._create_mp3,
            args=(value, speech_args, recordings, destination),
            daemon=True,
        ).start()

    def _create_mp3(
        self,
        text: str,
        speech_args: list[str],
        recordings: Path,
        destination: Path,
    ) -> None:
        staging_path: Path | None = None
        try:
            recordings.mkdir(parents=True, exist_ok=True)
            staging_file = tempfile.NamedTemporaryFile(
                prefix=".espeak-ng-studio-",
                suffix=".mp3",
                dir=recordings,
                delete=False,
            )
            staging_path = Path(staging_file.name)
            staging_file.close()
            with tempfile.TemporaryDirectory(prefix="espeak-ng-studio-") as temporary:
                wav_path = Path(temporary) / "source.wav"
                spoken = subprocess.run(
                    [*speech_args, "-w", str(wav_path), text],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if spoken.returncode != 0:
                    raise RuntimeError(spoken.stderr.strip() or "eSpeak NG could not create the audio.")
                encoded = subprocess.run(
                    [
                        self.ffmpeg_path or "ffmpeg",
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        str(wav_path),
                        "-codec:a",
                        "libmp3lame",
                        "-q:a",
                        "2",
                        str(staging_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if encoded.returncode != 0:
                    raise RuntimeError(encoded.stderr.strip() or "FFmpeg could not create the MP3.")
                os.replace(staging_path, destination)
                staging_path = None
            self.events.put(("save_done", destination))
        except (OSError, RuntimeError) as exc:
            self.events.put(("save_error", str(exc)))
        finally:
            if staging_path is not None:
                try:
                    staging_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.preview_button.configure(state="disabled" if busy or not self.espeak_path else "normal")
        self.save_button.configure(state="disabled" if busy or not self.ffmpeg_path or not self.espeak_path else "normal")

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "preview_done":
                    process, returncode, stderr = payload  # type: ignore[misc]
                    if process is self.speech_process:
                        self.speech_process = None
                        self.stop_button.configure(state="disabled")
                        if self.espeak_path and not self.busy:
                            self.preview_button.configure(state="normal")
                        if returncode == 0:
                            self.status_var.set("Preview finished — nothing was saved.")
                        elif returncode not in (-15, -9):
                            self.status_var.set("Preview failed.")
                            messagebox.showerror(APP_NAME, f"Preview failed:\n{stderr.strip()}", parent=self.root)
                elif event == "save_done":
                    self._set_busy(False)
                    destination = payload
                    self.status_var.set(f"Saved {destination.name}")  # type: ignore[union-attr]
                    messagebox.showinfo(APP_NAME, f"MP3 saved to:\n{destination}", parent=self.root)
                elif event == "save_error":
                    self._set_busy(False)
                    self.status_var.set("Could not save the MP3.")
                    messagebox.showerror(APP_NAME, f"Could not save the MP3:\n{payload}", parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def close(self) -> None:
        if self.busy:
            messagebox.showinfo(APP_NAME, "Please wait for the MP3 to finish saving.", parent=self.root)
            return
        self._save_settings()
        self.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    EspeakGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
