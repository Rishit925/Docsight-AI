from app.ingestion.document_processor import DocumentProcessor


def main():
    file_path = input("Enter the path of your PDF: ").strip()

    processor = DocumentProcessor()

    result = processor.process(file_path)

    print("\n========== DOCUMENT INFO ==========")

    print(f"File: {result['file_name']}")
    print(f"Total pages: {result['total_pages']}")

    total_tables = 0
    total_images = 0

    for page in result["pages"]:
        total_tables += len(page["tables"])
        total_images += len(page["images"])

    print(f"Total tables: {total_tables}")
    print(f"Total images: {total_images}")

    # --------------------------------
    # Show all tables
    # --------------------------------

    print("\n========== TABLES ==========")

    if total_tables == 0:
        print("No tables found.")

    else:
        table_number = 1

        for page in result["pages"]:

            for table in page["tables"]:

                print(f"\nTable {table_number}")
                print(f"Page: {page['page_number']}")

                for row in table["rows"]:
                    print(row)

                table_number += 1

    # --------------------------------
    # Show all images
    # --------------------------------

    print("\n========== IMAGES ==========")

    if total_images == 0:
        print("No images found.")

    else:
        image_number = 1

        for page in result["pages"]:

            for image in page["images"]:

                print(f"\nImage {image_number}")
                print(f"Page: {page['page_number']}")
                print(f"Path: {image['path']}")
                print(f"Type: {image['extension']}")
                print(f"Size: {image['width']} x {image['height']}")

                image_number += 1

    # --------------------------------
    # Show first page text
    # --------------------------------

    print("\n========== FIRST PAGE TEXT ==========")

    if result["pages"]:
        first_page = result["pages"][0]

        print(f"Page: {first_page['page_number']}")
        print(first_page["text"][:2000])

    else:
        print("No pages were processed.")


if __name__ == "__main__":
    main()