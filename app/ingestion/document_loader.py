from pathlib import Path
import pymupdf


class DocumentLoader:
    """Loads a PDF document using PyMuPDF."""

    def load(self, file_path: str):
        """
        Open a PDF and return the PyMuPDF document object.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        return pymupdf.open(file_path)