"""Image quality estimation and gated enhancement.

The orphaned ``yolo_oscf_v7.py`` ran CLAHE, grayscale, gamma and Canny-overlay
passes on *every* image and then voted across them. That multiplies detector
cost by the number of transforms whether or not any of them helps, which is why
it never reached production.

The approach here inverts the logic: measure the image first, and only generate
an enhanced variant when a specific measured defect suggests the detector is
likely to be handicapped. A well-exposed, sharp photo — the common case — costs
nothing extra and takes exactly one detector pass.

Quality statistics
------------------
All three are computed on the luminance channel and are cheap relative to a
single YOLO forward pass.

**Brightness** — mean luminance in ``[0, 255]``. Detects under- and
over-exposure.

**Contrast** — standard deviation of luminance. A low value means a washed-out
or hazy image where object boundaries carry little signal.

**Blur** — variance of the Laplacian. The Laplacian is a second-derivative
operator, so it responds to edges; a sharp image has many strong edges and hence
high variance, while a blurred one has few. This is the standard cheap
no-reference sharpness measure (Pech-Pacheco et al., 2000).

Note the blur score is *diagnostic only*. No enhancement here can recover
detail that motion blur destroyed — sharpening amplifies what edges survive but
invents nothing. It is recorded because it explains detector recall in benchmark
results and is reused as a crop-quality term for video best-frame selection.

Enhancements
------------
**CLAHE on luminance.** Contrast Limited Adaptive Histogram Equalization
equalizes within local tiles rather than globally, so a dark corner of a room
gets boosted without blowing out a sunlit window. It is applied to the L channel
in LAB space so chrominance — and therefore object colour, which the embedding
model relies on — is left untouched. The clip limit bounds noise amplification
in flat regions.

**Gamma correction.** A single power-law remap, applied when the whole frame is
mis-exposed rather than locally uneven. Under the convention used here (see
:func:`apply_gamma`) values above 1 brighten and values below 1 darken.

**Unsharp masking.** Adds back a scaled high-frequency residual
(``image - blurred``) to accentuate edges.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

from .config import VisionConfig

logger = logging.getLogger(__name__)

DEFECT_DARK = "dark"
DEFECT_BRIGHT = "bright"
DEFECT_LOW_CONTRAST = "low_contrast"
DEFECT_BLURRY = "blurry"


@dataclass(frozen=True)
class ImageQuality:
    """Measured statistics and the defects they imply."""

    brightness: float
    contrast: float
    blur_variance: float
    megapixels: float
    defects: tuple[str, ...]

    @property
    def is_poor(self) -> bool:
        """True when at least one defect was detected."""
        return bool(self.defects)

    @property
    def needs_enhancement(self) -> bool:
        """True when a defect exists that enhancement can plausibly address.

        Blur alone does not qualify. Sharpening a motion-blurred photo does not
        recover the lost detail, so spending a second detector pass on it is
        not justified by anything measurable.
        """
        return bool(set(self.defects) - {DEFECT_BLURRY})

    def to_dict(self) -> dict[str, object]:
        return {
            "brightness": round(self.brightness, 2),
            "contrast": round(self.contrast, 2),
            "blur_variance": round(self.blur_variance, 2),
            "megapixels": round(self.megapixels, 3),
            "defects": list(self.defects),
            "needs_enhancement": self.needs_enhancement,
        }


def _luminance(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def brightness_of(image: np.ndarray) -> float:
    """Mean luminance in ``[0, 255]``."""
    return float(_luminance(image).mean())


def contrast_of(image: np.ndarray) -> float:
    """Standard deviation of luminance."""
    return float(_luminance(image).std())


def blur_variance_of(image: np.ndarray) -> float:
    """Variance of the Laplacian; higher means sharper."""
    return float(cv2.Laplacian(_luminance(image), cv2.CV_64F).var())


def assess_quality(image: np.ndarray, config: VisionConfig) -> ImageQuality:
    """Measure an image and record which quality gates it fails."""
    if image is None or image.size == 0:
        raise ValueError("cannot assess an empty image")

    gray = _luminance(image)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    height, width = image.shape[:2]

    defects: list[str] = []
    if brightness < config.dark_brightness_threshold:
        defects.append(DEFECT_DARK)
    elif brightness > config.bright_brightness_threshold:
        defects.append(DEFECT_BRIGHT)
    if contrast < config.low_contrast_threshold:
        defects.append(DEFECT_LOW_CONTRAST)
    if blur < config.blur_variance_threshold:
        defects.append(DEFECT_BLURRY)

    return ImageQuality(
        brightness=brightness,
        contrast=contrast,
        blur_variance=blur,
        megapixels=(width * height) / 1e6,
        defects=tuple(defects),
    )


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    """Contrast-limited adaptive equalization of the luminance channel.

    Operates in LAB so only L is modified; equalizing BGR channels
    independently would shift hues and corrupt the colour information the
    appearance embeddings depend on.
    """
    if image.ndim == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
        return clahe.apply(image)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def apply_gamma(image: np.ndarray, gamma: float) -> np.ndarray:
    """Power-law intensity remap via a 256-entry lookup table.

    Computes ``out = 255 * (in / 255) ** (1 / gamma)``. Under this convention
    ``gamma > 1`` **brightens** (the exponent drops below 1, lifting midtones)
    and ``gamma < 1`` **darkens**. ``gamma == 1`` is the identity.

    A LUT makes this a single ``cv2.LUT`` pass instead of per-pixel float
    exponentiation, which matters on multi-megapixel inputs.
    """
    if gamma <= 0.0:
        raise ValueError(f"gamma must be positive, got {gamma}")
    inverse = 1.0 / gamma
    table = np.array(
        [np.clip(((i / 255.0) ** inverse) * 255.0, 0, 255) for i in range(256)],
        dtype=np.uint8,
    )
    return cv2.LUT(image, table)


def apply_sharpen(image: np.ndarray, amount: float = 0.6) -> np.ndarray:
    """Unsharp mask: add back a scaled high-frequency residual.

    ``amount`` scales the residual. Values above ~1.0 produce visible haloing
    around edges, which hurts rather than helps detection, so the default stays
    conservative.
    """
    if amount <= 0.0:
        return image
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3.0)
    return cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)


def enhance(image: np.ndarray, quality: ImageQuality, config: VisionConfig) -> "np.ndarray | None":
    """Build one enhanced variant targeting the measured defects.

    Returns ``None`` when no enhancement is warranted, which is the signal to
    the detector that no second pass should run.

    Only a single variant is produced, not one per defect. The detector cost is
    what matters, and stacking the relevant corrections into one image costs one
    extra pass instead of several.
    """
    if not quality.needs_enhancement:
        return None

    defects = set(quality.defects)
    out = image
    applied: list[str] = []

    # Uneven exposure is handled locally by CLAHE; a global gamma shift would
    # crush whichever end of the range is already correct.
    if DEFECT_DARK in defects or DEFECT_LOW_CONTRAST in defects:
        out = apply_clahe(out, config.clahe_clip_limit, config.clahe_grid_size)
        applied.append("clahe")

    if DEFECT_DARK in defects:
        out = apply_gamma(out, config.gamma_dark)
        applied.append(f"gamma={config.gamma_dark}")
    elif DEFECT_BRIGHT in defects:
        out = apply_gamma(out, config.gamma_bright)
        applied.append(f"gamma={config.gamma_bright}")

    # Sharpening only alongside a contrast fix. On its own it amplifies noise
    # more than signal, and it cannot undo blur.
    if DEFECT_LOW_CONTRAST in defects and config.sharpen_amount > 0.0:
        out = apply_sharpen(out, config.sharpen_amount)
        applied.append(f"sharpen={config.sharpen_amount}")

    if not applied:
        return None

    logger.debug("enhanced image for defects %s using %s", sorted(defects), applied)
    return out


def prepare_passes(image: np.ndarray, config: VisionConfig) -> tuple[list[np.ndarray], ImageQuality]:
    """Return the images the detector should run on, plus the quality report.

    The first element is always the original. A second, enhanced image is
    appended only when :func:`enhance` produced one. Detections from both are
    in identical coordinates, since no enhancement resizes or warps the frame,
    so no coordinate mapping is required afterwards — unlike the flip and
    rotate transforms in the old code, which needed per-transform inverse
    mapping and were a source of coordinate bugs.
    """
    quality = assess_quality(image, config)
    passes = [image]

    if config.enable_preprocessing:
        enhanced = enhance(image, quality, config)
        if enhanced is not None:
            passes.append(enhanced)

    return passes, quality


def sharpness_score(image: np.ndarray) -> float:
    """Alias of :func:`blur_variance_of`, for video crop-quality scoring."""
    return blur_variance_of(image)


__all__ = [
    "DEFECT_BLURRY",
    "DEFECT_BRIGHT",
    "DEFECT_DARK",
    "DEFECT_LOW_CONTRAST",
    "ImageQuality",
    "apply_clahe",
    "apply_gamma",
    "apply_sharpen",
    "assess_quality",
    "blur_variance_of",
    "brightness_of",
    "contrast_of",
    "enhance",
    "prepare_passes",
    "sharpness_score",
]
