import os
import base64

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class OpenAIProvider:
    """Handles OpenAI vision-based image understanding."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set in the .env file."
            )

        self.client = OpenAI(api_key=api_key)

        self.model_name = "gpt-5-mini"

    def analyze_image(self, image_path: str):
        """
        Analyze an extracted document image
        using OpenAI vision capabilities.
        """

        if not os.path.exists(image_path):
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        base64_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = """
You are analyzing an image extracted from a document.

Describe only the information that is useful for
understanding the document.

If the image contains:
- a diagram, explain its structure and relationships
- a chart, describe its title, axes, labels, trends,
  and important values
- a figure, explain what it represents
- text, summarize the meaningful text
- a technical illustration, explain the important components

Do not invent information that is not visible.

Return a concise but informative description.
"""

        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": (
                                f"data:image/png;base64,"
                                f"{base64_image}"
                            ),
                        },
                    ],
                }
            ],
        )

        return response.output_text