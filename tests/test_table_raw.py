from app.ingestion.document_processor import DocumentProcessor


def main():

    file_path = input(
        "Enter the path of your PDF: "
    ).strip()

    processor = DocumentProcessor()

    document_data = processor.process(
        file_path
    )

    table_number = 0

    print("\n========== RAW TABLE STRUCTURE ==========")

    for page in document_data["pages"]:

        for table in page["tables"]:

            table_number += 1

            print(
                f"\n========== TABLE {table_number} =========="
            )

            print(
                f"Page: {page['page_number']}"
            )

            print(
                f"Rows: {table['row_count']}"
            )

            print(
                f"Columns: {table['col_count']}"
            )

            print(
                f"\nHeaders:\n{table['headers']}"
            )

            print(
                "\n========== MARKDOWN =========="
            )

            print(
                table["markdown"]
            )


if __name__ == "__main__":
    main()