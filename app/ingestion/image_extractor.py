from pathlib import Path


class ImageExtractor:
    """Extracts images from PDF pages."""

    def extract(self, document, page, page_number, output_directory, document_name):
        """
        Extract all images from a PDF page.

        Returns:
            list: Metadata for extracted images.
        """

        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)

        images = []

        image_list = page.get_images(full=True)

        for image_index, image_info in enumerate(image_list, start=1):
            xref = image_info[0]

            try:
                image_data = document.extract_image(xref)

                image_bytes = image_data["image"]
                image_extension = image_data["ext"]

                image_name = (
                    f"{document_name}_"
                    f"page_{page_number}_"
                    f"image_{image_index}."
                    f"{image_extension}"
                )

                image_path = output_directory / image_name

                with open(image_path, "wb") as image_file:
                    image_file.write(image_bytes)

                images.append(
                    {
                        "image_number": image_index,
                        "page_number": page_number,
                        "path": str(image_path),
                        "extension": image_extension,
                        "width": image_data.get("width"),
                        "height": image_data.get("height"),
                    }
                )

            except Exception as error:
                print(
                    f"Could not extract image "
                    f"{image_index} from page {page_number}: {error}"
                )

        return images