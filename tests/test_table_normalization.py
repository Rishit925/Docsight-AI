from app.ingestion.document_processor import DocumentProcessor
from app.ingestion.table_normalizer import TableNormalizer
from app.ingestion.table_validator import TableValidator


def main():

    file_path = input(
        "Enter the path of your PDF: "
    ).strip()

    # --------------------------------
    # Extract document
    # --------------------------------

    processor = DocumentProcessor()

    document_data = processor.process(
        file_path
    )

    validator = TableValidator()
    normalizer = TableNormalizer()

    total_tables = 0
    valid_tables = 0
    rejected_tables = 0

    print(
        "\n========== TABLE VALIDATION + NORMALIZATION =========="
    )

    for page in document_data["pages"]:

        for table in page["tables"]:

            total_tables += 1

            print(
                f"\n----- Candidate Table {total_tables} -----"
            )

            print(
                f"Page: {page['page_number']}"
            )

            # --------------------------------
            # Validate table
            # --------------------------------

            is_valid = validator.validate(
                table
            )

            if not is_valid:

                rejected_tables += 1

                print(
                    "Status: REJECTED "
                    "(not a valid structured table)"
                )

                continue

            valid_tables += 1

            print(
                "Status: VALID TABLE"
            )

            # --------------------------------
            # Normalize table
            # --------------------------------

            normalized = normalizer.normalize(
                table
            )

            if not normalized:

                print(
                    "Normalization: FAILED"
                )

                continue

            print(
                "\n========== NORMALIZED TABLE =========="
            )

            print(
                normalized
            )

    # --------------------------------
    # Summary
    # --------------------------------

    print(
        "\n========== TABLE SUMMARY =========="
    )

    print(
        f"Total candidates: {total_tables}"
    )

    print(
        f"Valid tables: {valid_tables}"
    )

    print(
        f"Rejected candidates: {rejected_tables}"
    )

    if total_tables == 0:

        print(
            "No tables detected."
        )


if __name__ == "__main__":
    main()