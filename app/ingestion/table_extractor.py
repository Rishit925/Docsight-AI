class TableExtractor:
    """Extracts tables from PDF pages using PyMuPDF."""

    def extract(self, page):
        """
        Extract tables while preserving their geometry,
        row positions, and column positions.
        """

        tables = []

        try:
            table_finder = page.find_tables()

            for table in table_finder.tables:

                rows = table.extract()

                if not rows:
                    continue

                tables.append(
                    {
                        "rows": rows,
                        "bbox": list(table.bbox),
                        "row_count": table.row_count,
                        "col_count": table.col_count,
                        "cells": self._extract_cells(
                            table
                        ),
                    }
                )

        except Exception as error:

            print(
                f"Table extraction warning: {error}"
            )

        return tables

    def _extract_cells(self, table):
        """
        Preserve each cell's:

        - row index
        - column index
        - bounding box
        """

        cells = []

        try:

            for row_index, row in enumerate(
                table.rows
            ):

                row_cells = []

                for col_index, cell in enumerate(
                    row.cells
                ):

                    if cell is None:

                        row_cells.append(
                            None
                        )

                        continue

                    x0, y0, x1, y1 = cell[:4]

                    row_cells.append(
                        {
                            "row": row_index,
                            "column": col_index,
                            "bbox": [
                                x0,
                                y0,
                                x1,
                                y1,
                            ],
                        }
                    )

                cells.append(
                    row_cells
                )

        except Exception as error:

            print(
                f"Cell extraction warning: {error}"
            )

        return cells