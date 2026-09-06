from app.ingestion.document_processor import DocumentProcessor


def main():

    path = input(
        "Enter the path of your PDF: "
    ).strip()

    processor = DocumentProcessor()

    document = processor.process(path)

    print(
        "\n========== TABLE GEOMETRY =========="
    )

    for page_data in document["pages"]:

        tables = page_data.get(
            "tables",
            []
        )

        for table_index, table in enumerate(
            tables,
            start=1,
        ):

            print(
                f"\n===== TABLE {table_index} ====="
            )

            print(
                "Rows:",
                table.get("row_count")
            )

            print(
                "Columns:",
                table.get("col_count")
            )

            print(
                "\nRAW ROWS:"
            )

            for index, row in enumerate(
                table["rows"]
            ):

                print(
                    f"Row {index}:"
                )

                for col, cell in enumerate(
                    row
                ):

                    print(
                        f"  Col {col}: "
                        f"{repr(cell)}"
                    )

            print("\nROW BBOXES:")

            for index, bbox in enumerate(
                table.get("row_bboxes", [])
                    ):

                print(
                    f"Row {index}: {bbox}"
                        )


            print("\nCELL GEOMETRY:")

            for row_index, row_cells in enumerate(
                table.get("cells", [])
            ):

                print(f"Row {row_index}:")

                for cell in row_cells:

                    if cell is None:
                        continue

                    print(
                        f"  Column: {cell['column']} "
                        f"BBox: {cell['bbox']}"
                    )


if __name__ == "__main__":
    main()