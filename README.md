# eSpeak NG Studio

A simple Linux desktop GUI for previewing eSpeak NG voices and saving selected
recordings as MP3 files.

## Start the app

Run:

```bash
./run-espeak-gui
```

The launcher checks for Python Tkinter, eSpeak NG, and FFmpeg. If something is
missing, it prints a copy-paste installation command for `apt`, `dnf`, `pacman`,
or `zypper`. It never installs packages or asks for administrator access by
itself.

## How files are handled

- **Preview** plays speech directly through eSpeak NG. It creates no WAV or MP3.
- **Save MP3** temporarily creates a WAV in the operating system's temporary
  directory, converts it, and immediately removes the temporary WAV.
- The finished MP3 is written to `espeak-recordings/` under the directory that
  contains the application.
- Closing or canceling the filename prompt saves no recording.

The app remembers the last selected language, accent, voice, speed, and pitch in
the standard user configuration directory (`~/.config/espeak-ng-studio/` on a
typical Linux system).

## Voices

- English: American (`en-us`) or British (`en`)
- Spanish: Mexican or Spain
- French, Japanese, and Portuguese: one regional setting each
- Male and female eSpeak voice variants are available for every language. The
  female profile uses eSpeak NG's `f2` variant and a calibrated pitch range so
  it remains recognizably female when the accent or pitch is changed.

Voice quality and pronunciation depend on the voices included with the installed
version of eSpeak NG.
