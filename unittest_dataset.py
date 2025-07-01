import unittest
import numpy as np
import soundfile as sf
from analysis_function import AudioProcessor


class TestAudioProcessor(unittest.TestCase):

    def setUp(self):
        self.audio_proc = AudioProcessor()

    def test_extract_features_positive(self):
        sr = 22050
        t = np.linspace(0, 1, sr)
        data = np.sin(2 * np.pi * 440 * t)
        temp_path = "test_sine.wav"
        sf.write(temp_path, data, sr)

        features = self.audio_proc.extract_audio_features(temp_path)
        self.assertIn('mfccs', features)
        self.assertEqual(features['spectral_centroid'].ndim, 2)

    def test_extract_features_file_not_found(self):
        with self.assertRaises(Exception):
            self.audio_proc.extract_audio_features('nonexistent.mp3')


if __name__ == '__main__':
    unittest.main()
