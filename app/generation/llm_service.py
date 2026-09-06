import os
import time

from google import genai
from google.genai import types


class LLMService:
    """
    Production-ready Gemini LLM service.

    Responsibilities:
    - Initialize Gemini client
    - Generate text responses
    - Avoid automatic function calling
    - Retry only temporary API failures
    - Never retry quota or authentication failures
    - Validate API configuration
    """

    DEFAULT_MODEL = "gemini-3.6-flash"

    # HTTP/API errors that can reasonably be temporary.
    RETRYABLE_STATUS_CODES = {
        500,
        502,
        503,
        504,
    }

    # Errors that should never be retried.
    NON_RETRYABLE_STATUS_CODES = {
        400,
        401,
        403,
        404,
        429,
    }

    def __init__(
        self,
        model=None,
        max_retries=3,
        retry_delay=2,
    ):
        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.max_retries = max(
            0,
            int(max_retries),
        )

        self.retry_delay = max(
            0,
            int(retry_delay),
        )

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable "
                "is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    # ==================================================
    # GENERATE
    # ==================================================

    def generate(
        self,
        prompt,
        temperature=0.2,
        max_output_tokens=2048,
    ):
        """
        Generate a response from Gemini.

        Retry policy:

        429:
            No retry. Quota/rate-limit errors should not
            repeatedly consume requests.

        400/401/403/404:
            No retry. These indicate configuration or
            request problems.

        500/502/503/504:
            Retry with exponential backoff because these
            can be temporary server-side failures.
        """

        if not prompt or not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty."
            )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            automatic_function_calling=(
                types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )

        last_error = None

        total_attempts = (
            self.max_retries + 1
        )

        for attempt in range(
            total_attempts
        ):
            try:
                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )
                )

                if not response:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                text = self._extract_text(
                    response
                )

                if not text:
                    raise RuntimeError(
                        "Gemini returned no usable text."
                    )

                return text

            except Exception as error:
                last_error = error

                status_code = (
                    self._get_status_code(
                        error
                    )
                )

                # ------------------------------------------
                # NEVER RETRY QUOTA / RATE LIMIT ERRORS
                # ------------------------------------------

                if status_code == 429:
                    raise RuntimeError(
                        "Gemini quota or rate limit "
                        "was exceeded. No retry was attempted."
                    ) from error

                # ------------------------------------------
                # NEVER RETRY CLIENT / AUTH ERRORS
                # ------------------------------------------

                if (
                    status_code
                    in self.NON_RETRYABLE_STATUS_CODES
                ):
                    raise RuntimeError(
                        "Gemini request failed with "
                        f"HTTP {status_code}. "
                        "The request was not retried."
                    ) from error

                # ------------------------------------------
                # STOP AFTER FINAL ATTEMPT
                # ------------------------------------------

                if attempt >= self.max_retries:
                    break

                # ------------------------------------------
                # RETRY TEMPORARY SERVER ERRORS
                # ------------------------------------------

                if (
                    status_code is not None
                    and status_code
                    not in self.RETRYABLE_STATUS_CODES
                ):
                    raise RuntimeError(
                        "Gemini request failed with "
                        f"HTTP {status_code}. "
                        "The error is not considered "
                        "safe to retry."
                    ) from error

                delay = (
                    self.retry_delay
                    * (2 ** attempt)
                )

                time.sleep(
                    delay
                )

        raise RuntimeError(
            "Gemini generation failed after "
            f"{total_attempts} attempts."
        ) from last_error

    # ==================================================
    # TEXT EXTRACTION
    # ==================================================

    def _extract_text(
        self,
        response,
    ):
        """
        Extract generated text from a Gemini
        GenerateContentResponse.

        Preferred path:

            response.text

        Fallback path:

            response
                -> candidates
                    -> content
                        -> parts
                            -> text
        """

        if response is None:
            return ""

        # ------------------------------------------
        # PREFERRED SDK PROPERTY
        # ------------------------------------------

        text = getattr(
            response,
            "text",
            None,
        )

        if isinstance(
            text,
            str,
        ) and text.strip():
            return text.strip()

        # ------------------------------------------
        # FALLBACK: CANDIDATES
        # ------------------------------------------

        candidates = getattr(
            response,
            "candidates",
            None,
        )

        if not candidates:
            return ""

        text_parts = []

        for candidate in candidates:
            content = getattr(
                candidate,
                "content",
                None,
            )

            if content is None:
                continue

            parts = getattr(
                content,
                "parts",
                None,
            )

            if not parts:
                continue

            for part in parts:
                part_text = getattr(
                    part,
                    "text",
                    None,
                )

                if (
                    isinstance(
                        part_text,
                        str,
                    )
                    and part_text.strip()
                ):
                    text_parts.append(
                        part_text.strip()
                    )

        return "\n".join(
            text_parts
        ).strip()

    # ==================================================
    # STATUS CODE EXTRACTION
    # ==================================================

    def _get_status_code(
        self,
        error,
    ):
        """
        Extract an HTTP/API status code from Gemini
        exceptions when available.

        Returns:
            int or None
        """

        status_code = getattr(
            error,
            "status_code",
            None,
        )

        if isinstance(
            status_code,
            int,
        ):
            return status_code

        code = getattr(
            error,
            "code",
            None,
        )

        if isinstance(
            code,
            int,
        ):
            return code

        response = getattr(
            error,
            "response",
            None,
        )

        if response is not None:
            response_status = getattr(
                response,
                "status_code",
                None,
            )

            if isinstance(
                response_status,
                int,
            ):
                return response_status

        return None