import unittest

from espeak_gui_core import safe_recording_name, voice_for


class CoreTests(unittest.TestCase):
    def test_voice_uses_selected_accent_and_gender(self):
        self.assertEqual(voice_for("English", "British", "Female"), "en-gb+f3")
        self.assertEqual(voice_for("Spanish", "Mexican", "Male"), "es-mx+m3")

    def test_language_without_accents_uses_default(self):
        self.assertEqual(voice_for("Japanese", "", "Female"), "ja+f3")

    def test_filename_is_safe_and_has_mp3_extension(self):
        self.assertEqual(safe_recording_name("  My: recording.mp3  "), "My_ recording.mp3")
        self.assertEqual(safe_recording_name("hello"), "hello.mp3")

    def test_empty_filename_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_recording_name(" ... ")

if __name__ == "__main__":
    unittest.main()
