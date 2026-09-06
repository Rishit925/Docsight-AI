import hashlib
import json
from pathlib import Path

from app.providers.openai_provider import OpenAIProvider


class ImageProcessor:
    """
    Processes extracted images using OpenAI Vision with caching.

    Images are cached using their content hash rather than their
    filesystem path. This allows the same image to be reused from
    cache even when it is extracted into a different directory.
    """

    def __init__(
        self,
        cache_path="data/processed/image_descriptions.json",
    ):
        self.openai = OpenAIProvider()

        self.cache_path = Path(cache_path)

        self.cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cache = self._load_cache()

    # ==================================================
    # LOAD CACHE
    # ==================================================

    def _load_cache(self):
        """Load previously generated image descriptions."""

        if not self.cache_path.exists():
            return {}

        try:
            with open(
                self.cache_path,
                "r",
                encoding="utf-8",
            ) as file:
                return json.load(file)

        except (json.JSONDecodeError, OSError):
            return {}

    # ==================================================
    # SAVE CACHE
    # ==================================================

    def _save_cache(self):
        """Save image descriptions to disk."""

        with open(
            self.cache_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.cache,
                file,
                indent=2,
                ensure_ascii=False,
            )

    # ==================================================
    # IMAGE HASH
    # ==================================================

    def _get_image_hash(
        self,
        image_path: str,
    ):
        """
        Generate a SHA-256 hash from the image contents.

        The hash identifies the actual image rather than its
        filesystem location.
        """

        sha256 = hashlib.sha256()

        with open(
            image_path,
            "rb",
        ) as file:

            for chunk in iter(
                lambda: file.read(8192),
                b"",
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    # ==================================================
    # PROCESS IMAGE
    # ==================================================

    def process(
        self,
        image_path: str,
    ):
        """
        Generate or retrieve a cached image description.

        The cache is based on the image contents, so the same
        image can be reused even if its path changes.
        """

        image_path = str(
            Path(image_path)
        )

        # ----------------------------------------------
        # Validate image
        # ----------------------------------------------

        if not Path(image_path).exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # ----------------------------------------------
        # Generate image hash
        # ----------------------------------------------

        image_hash = self._get_image_hash(
            image_path
        )

        # ----------------------------------------------
        # Check cache
        # ----------------------------------------------

        if image_hash in self.cache:

            print(
                f"Using cached description: {image_path}"
            )

            return {
                "image_path": image_path,
                "description": self.cache[
                    image_hash
                ],
                "cached": True,
            }

        # ----------------------------------------------
        # Call OpenAI
        # ----------------------------------------------

        print(
            f"Analyzing image with OpenAI: {image_path}"
        )

        description = self.openai.analyze_image(
            image_path
        )

        # ----------------------------------------------
        # Save result
        # ----------------------------------------------

        self.cache[image_hash] = description

        self._save_cache()

        return {
            "image_path": image_path,
            "description": description,
            "cached": False,
        }