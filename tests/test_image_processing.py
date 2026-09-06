from app.ingestion.document_processor import DocumentProcessor
from app.ingestion.image_processor import ImageProcessor


def main():

    file_path = input(
        "Enter the path of your PDF: "
    ).strip()

    # -----------------------------
    # Extract images
    # -----------------------------

    processor = DocumentProcessor()

    document_data = processor.process(
        file_path
    )

    images = []

    for page in document_data["pages"]:

        for image in page["images"]:

            images.append(image)

    print("\n========== IMAGE INFO ==========")

    print(
        f"Images found: {len(images)}"
    )

    if not images:
        print("No images found.")
        return

    # -----------------------------
    # Process first image only
    # -----------------------------

    first_image = images[0]

    print(
        f"\nProcessing image from page "
        f"{first_image['page_number']}..."
    )

    image_processor = ImageProcessor()

    result = image_processor.process(
        first_image["path"]
    )

    # -----------------------------
    # Display result
    # -----------------------------

    print("\n========== IMAGE DESCRIPTION ==========")

    print(result["description"])


if __name__ == "__main__":
    main()