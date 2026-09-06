import re


class TableValidator:
    """
    Generic table validator.

    Determines whether an extracted PyMuPDF table is
    likely to represent a real tabular structure.

    The validator does NOT depend on specific headers,
    column counts, or document types.
    """

    def validate(self, table):
        rows = table.get("rows", [])
        cells = table.get("cells", [])

        if not rows:
            return False

        # ----------------------------------------------
        # Basic size check
        # ----------------------------------------------

        non_empty_rows = [
            row for row in rows
            if self._row_has_content(row)
        ]

        if len(non_empty_rows) < 2:
            return False

        # ----------------------------------------------
        # Calculate structural properties
        # ----------------------------------------------

        column_count = table.get(
            "col_count",
            self._estimate_column_count(rows),
        )

        populated_columns = self._count_populated_columns(
            rows
        )

        populated_rows = len(non_empty_rows)

        # ----------------------------------------------
        # A real table normally has:
        #
        #   multiple rows
        #   multiple populated columns
        #
        # ----------------------------------------------

        if column_count < 2:
            return False

        if populated_columns < 2:
            return False

        if populated_rows < 2:
            return False

        # ----------------------------------------------
        # Determine how much content exists in cells.
        # ----------------------------------------------

        total_cells = 0
        non_empty_cells = 0

        for row in rows:

            for cell in row:

                total_cells += 1

                if self._clean(cell):
                    non_empty_cells += 1

        if total_cells == 0:
            return False

        density = (
            non_empty_cells / total_cells
        )

        # ----------------------------------------------
        # Extremely sparse structures are usually
        # decorative page elements rather than tables.
        # ----------------------------------------------

        if density < 0.10:
            return False

        # ----------------------------------------------
        # Check whether multiple rows have content
        # distributed across multiple columns.
        # ----------------------------------------------

        multi_column_rows = 0

        for row in rows:

            populated = sum(
                1
                for cell in row
                if self._clean(cell)
            )

            if populated >= 2:
                multi_column_rows += 1

        if multi_column_rows < 2:
            return False

        # ----------------------------------------------
        # Check whether this looks like a title or
        # metadata block incorrectly detected as a table.
        # ----------------------------------------------

        if self._looks_like_page_metadata(
            rows
        ):
            return False

        return True

    # ==================================================
    # ROW CONTENT
    # ==================================================

    def _row_has_content(self, row):

        return any(
            self._clean(cell)
            for cell in row
        )

    # ==================================================
    # COLUMN COUNT
    # ==================================================

    def _estimate_column_count(self, rows):

        if not rows:
            return 0

        return max(
            len(row)
            for row in rows
        )

    # ==================================================
    # POPULATED COLUMNS
    # ==================================================

    def _count_populated_columns(self, rows):

        column_count = self._estimate_column_count(
            rows
        )

        populated = 0

        for column in range(column_count):

            has_content = False

            for row in rows:

                if column >= len(row):
                    continue

                if self._clean(
                    row[column]
                ):
                    has_content = True
                    break

            if has_content:
                populated += 1

        return populated

    # ==================================================
    # PAGE METADATA DETECTION
    # ==================================================

    def _looks_like_page_metadata(self, rows):

        text = []

        for row in rows:

            for cell in row:

                value = self._clean(cell)

                if value:
                    text.append(value)

        if not text:
            return True

        combined = " ".join(text).lower()

        metadata_patterns = [
            r"\b\d+\s*pages?\b",
            r"\b\d+\s*tables?\b",
            r"\b\d+\s*figures?\b",
            r"\bprepared\s+by\b",
            r"\btopic\s*:",
            r"\bedition\b",
            r"\bcopyright\b",
        ]

        matches = 0

        for pattern in metadata_patterns:

            if re.search(
                pattern,
                combined,
            ):
                matches += 1

        # A structure dominated by metadata is
        # almost certainly not a real table.
        if matches >= 2:
            return True

        return False

    # ==================================================
    # CLEAN TEXT
    # ==================================================

    def _clean(self, value):

        if value is None:
            return ""

        value = str(value)

        value = value.replace(
            "\n",
            " ",
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()