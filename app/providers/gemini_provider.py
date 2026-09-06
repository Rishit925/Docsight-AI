import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiProvider:
    """Handles communication with the Gemini API."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in the .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = "gemini-3.6-flash"

    def generate(self, prompt: str):
        """
        Generate a response from Gemini.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return response.text