from __future__ import annotations

import unittest

from PIL import Image

from backend.app.config import IMAGE_SIZE
from backend.app.ml.preprocessing import preprocess_image, validate_image_bytes


class PreprocessingTests(unittest.TestCase):
    def test_full_preprocessing_preserves_the_validated_square_output_contract(self) -> None:
        source = Image.new("RGB", (640, 480), "white")
        processed = preprocess_image(source, mode="full")
        self.assertEqual(processed.mode, "RGB")
        self.assertEqual(processed.size, (IMAGE_SIZE, IMAGE_SIZE))

    def test_invalid_payload_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            validate_image_bytes(b"not-an-image")
