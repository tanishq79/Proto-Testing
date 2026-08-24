from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError

from backend.app.config import (
    ENABLE_BACKGROUND_REMOVAL,
    ENABLE_COLOR_CORRECTION,
    ENABLE_ENHANCEMENT,
    IMAGE_SIZE,
    PADDING_RATIO,
)

try:
    from rembg import remove as rembg_remove

    REMBG_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the optional runtime package
    rembg_remove = None
    REMBG_AVAILABLE = False


class ImageValidationError(ValueError):
    """Raised when an upload is not a supported, decodable image."""


@dataclass(frozen=True)
class ImageValidation:
    width: int
    height: int
    mode: str
    image_format: str
    aspect_ratio: float


def validate_image_bytes(data: bytes) -> tuple[Image.Image, ImageValidation]:
    """Validate a request payload using the notebook's Pillow verification semantics."""
    if not data:
        raise ImageValidationError("The uploaded file is empty.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width < 32 or height < 32:
                raise ImageValidationError("Images must be at least 32 pixels in both dimensions.")
            if image.format not in {"PNG", "JPEG"}:
                raise ImageValidationError("Only PNG and JPEG images are supported.")
            copied = image.copy()
            return copied, ImageValidation(
                width=width,
                height=height,
                mode=image.mode,
                image_format=image.format,
                aspect_ratio=width / height,
            )
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ImageValidationError("The uploaded file is not a valid PNG or JPEG image.") from error


def remove_background(image: Image.Image) -> Image.Image:
    """Preserve the notebook's alpha-aware optional rembg behavior."""
    rgba = image.convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 250:
        return rgba
    if ENABLE_BACKGROUND_REMOVAL and REMBG_AVAILABLE and rembg_remove is not None:
        buffer = io.BytesIO()
        rgba.save(buffer, format="PNG")
        return Image.open(io.BytesIO(rembg_remove(buffer.getvalue()))).convert("RGBA")
    return rgba


def find_object_bbox(rgba: Image.Image) -> tuple[int, int, int, int]:
    alpha = np.asarray(rgba.getchannel("A"))
    ys, xs = np.where(alpha > 20)
    if len(xs):
        return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
    return 0, 0, rgba.width, rgba.height


def crop_object(rgba: Image.Image, bbox: tuple[int, int, int, int]) -> Image.Image:
    return rgba.crop(bbox)


def add_padding(image: Image.Image, ratio: float = PADDING_RATIO) -> Image.Image:
    horizontal, vertical = round(image.width * ratio), round(image.height * ratio)
    canvas = Image.new(
        "RGBA",
        (image.width + 2 * horizontal, image.height + 2 * vertical),
        (255, 255, 255, 0),
    )
    canvas.paste(image, (horizontal, vertical))
    return canvas


def resize_preserve_aspect_ratio(image: Image.Image, size: int = IMAGE_SIZE) -> Image.Image:
    scale = min(size / image.width, size / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (size, size), "white")
    canvas.paste(resized.convert("RGB"), ((size - resized.width) // 2, (size - resized.height) // 2))
    return canvas


def color_normalization(image: Image.Image) -> Image.Image:
    if not ENABLE_COLOR_CORRECTION:
        return image
    return ImageEnhance.Contrast(ImageEnhance.Brightness(image).enhance(1.02)).enhance(1.03)


def mild_enhancement(image: Image.Image) -> Image.Image:
    if not ENABLE_ENHANCEMENT:
        return image
    return image.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=4))


def preprocess_image(image: Image.Image, mode: str = "full") -> Image.Image:
    """Apply the notebook's raw, crop, or full preprocessing modes to an in-memory image."""
    if mode == "raw":
        return resize_preserve_aspect_ratio(image)
    rgba = remove_background(image)
    processed = resize_preserve_aspect_ratio(add_padding(crop_object(rgba, find_object_bbox(rgba))))
    return mild_enhancement(color_normalization(processed)) if mode == "full" else processed
