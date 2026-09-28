import unittest

from espeak_gui_core import (
    espeak_error,
    pitch_for,
    pitch_limits,
    safe_recording_name,
    voice_for,
)


class CoreTests(unittest.TestCase):
    def test_voice_uses_selected_accent_and_gender(self):
        self.assertEqual(voice_for("English", "British", "Female"), "en+f2")
        self.assertEqual(voice_for("Spanish", "Mexican", "Male"), "es-mx+m3")

    def test_language_without_accents_uses_default(self):
        self.assertEqual(voice_for("Japanese", "", "Female"), "ja+f2")

    def test_female_pitch_is_kept_in_a_useful_range(self):
        self.assertEqual(pitch_limits("Female"), (55, 99))
        self.assertEqual(pitch_for("Female", 10), 55)
        self.assertEqual(pitch_for("Female", 60.9), 60)

    def test_male_pitch_retains_the_full_espeak_range(self):
        self.assertEqual(pitch_for("Male", -5), 0)
        self.assertEqual(pitch_for("Male", 70), 70)

    def test_espeak_diagnostics_are_not_silently_ignored(self):
        self.assertIsNone(espeak_error(0, ""))
        self.assertEqual(
            espeak_error(0, "Error: The specified voice does not exist.\n"),
            "Error: The specified voice does not exist.",
        )
        self.assertEqual(espeak_error(2, ""), "eSpeak NG exited with status 2.")

    def test_filename_is_safe_and_has_mp3_extension(self):
        self.assertEqual(safe_recording_name("  My: recording.mp3  "), "My_ recording.mp3")
        self.assertEqual(safe_recording_name("hello"), "hello.mp3")

    def test_empty_filename_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_recording_name(" ... ")

if __name__ == "__main__":
    unittest.main()
