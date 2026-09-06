from pathlib import Path

from app.ingestion.document_loader import DocumentLoader
from app.ingestion.text_extractor import TextExtractor
from app.ingestion.table_extractor import TableExtractor
from app.ingestion.image_extractor import ImageExtractor
from app.ingestion.image_processor import ImageProcessor


class DocumentProcessor:
    """Coordinates complete PDF document processing."""

    def __init__(self):
        self.loader = DocumentLoader()
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.image_processor = ImageProcessor()

    def process(self, file_path: str):
        """
        Process a PDF and extract text, tables, and images.

        Images are additionally analyzed by OpenAI Vision.
        Cached image descriptions are reused when available.
        """

        file_path = Path(file_path)

        document = self.loader.load(
            str(file_path)
        )

        document_name = file_path.stem

        image_directory = (
            Path("data/images") / document_name
        )

        image_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        pages = []

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            # --------------------------------
            # Extract text
            # --------------------------------

            text = page.get_text(
                "text"
            ).strip()

            # --------------------------------
            # Extract tables
            # --------------------------------

            tables = self.table_extractor.extract(
                page
            )

            # --------------------------------
            # Extract images
            # --------------------------------

            images = self.image_extractor.extract(
                document=document,
                page=page,
                page_number=page_number,
                output_directory=image_directory,
                document_name=document_name,
            )

            # --------------------------------
            # Analyze images
            # --------------------------------

            for image in images:

                result = self.image_processor.process(
                    image["path"]
                )

                image["description"] = (
                    result["description"]
                )

                image["description_cached"] = (
                    result["cached"]
                )

            # --------------------------------
            # Store page
            # --------------------------------

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "tables": tables,
                    "images": images,
                }
            )

        result = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "total_pages": len(document),
            "pages": pages,
        }

        document.close()

        return result