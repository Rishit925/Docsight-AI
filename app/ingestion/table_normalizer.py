import re


class TableNormalizer:
    """
    Converts extracted PDF tables into clean semantic text.

    Uses the physical table structure to reconstruct logical
    rows and columns, including continuation lines created
    by merged cells.
    """

    def normalize(self, table):
        rows = table.get("rows", [])
        cells = table.get("cells", [])

        if not rows:
            return ""

        # --------------------------------------------------
        # Detect common 3-column comparison tables
        # --------------------------------------------------

        header_info = self._find_header_structure(rows)

        if header_info:
            return self._normalize_structured_table(
                rows,
                cells,
                header_info,
            )

        # --------------------------------------------------
        # Generic fallback for other table types
        # --------------------------------------------------

        return self._normalize_generic_table(rows)

    # ==================================================
    # HEADER DETECTION
    # ==================================================

    def _find_header_structure(self, rows):

        for row_index, row in enumerate(rows):

            cleaned = [
                self._clean_cell(cell)
                for cell in row
            ]

            values = [
                value.lower()
                for value in cleaned
                if value
            ]

            if (
                "syntax" in values
                and "semantics" in values
            ):
                return {
                    "row_index": row_index,
                    "feature": self._find_column(
                        cleaned,
                        "features",
                    ),
                    "syntax": self._find_column(
                        cleaned,
                        "syntax",
                    ),
                    "semantics": self._find_column(
                        cleaned,
                        "semantics",
                    ),
                }

        return None

    # ==================================================
    # FIND COLUMN
    # ==================================================

    def _find_column(
        self,
        row,
        target,
    ):

        for index, value in enumerate(row):

            if value.lower() == target.lower():
                return index

        return None

    # ==================================================
    # STRUCTURED TABLE
    # ==================================================

    def _normalize_structured_table(
        self,
        rows,
        cells,
        header_info,
    ):

        header_row = header_info["row_index"]

        feature_column = header_info["feature"]
        syntax_column = header_info["syntax"]
        semantics_column = header_info["semantics"]

        if (
            feature_column is None
            or syntax_column is None
            or semantics_column is None
        ):
            return ""

        # --------------------------------------------------
        # Determine physical column groups.
        #
        # In some PDFs the logical Syntax/Semantics
        # sections span multiple physical columns.
        # --------------------------------------------------

        syntax_columns = self._detect_column_group(
            rows[header_row],
            syntax_column,
            semantics_column,
        )

        semantics_columns = self._detect_column_group(
            rows[header_row],
            semantics_column,
            None,
        )

        # If the PDF has only one physical column for
        # each logical field, use that directly.
        if not syntax_columns:
            syntax_columns = [syntax_column]

        if not semantics_columns:
            semantics_columns = [semantics_column]

        # --------------------------------------------------
        # Process rows after header.
        # --------------------------------------------------

        sections = []

        current_feature = None
        current_syntax = []
        current_semantics = []

        for row_index in range(
            header_row + 1,
            len(rows),
        ):

            row = rows[row_index]

            if self._is_empty_row(row):
                continue

            feature_text = self._get_feature_text(
                row,
                feature_column,
            )

            syntax_text = self._get_group_text(
                row,
                syntax_columns,
            )

            semantics_text = self._get_group_text(
                row,
                semantics_columns,
            )

            # --------------------------------------------------
            # New logical feature
            # --------------------------------------------------

            if feature_text:

                if current_feature:

                    sections.append(
                        self._format_section(
                            current_feature,
                            current_syntax,
                            current_semantics,
                        )
                    )

                current_feature = feature_text
                current_syntax = []
                current_semantics = []

            # --------------------------------------------------
            # Continuation text
            # --------------------------------------------------

            if syntax_text:
                self._append_unique(
                    current_syntax,
                    syntax_text,
                )

            if semantics_text:
                self._append_unique(
                    current_semantics,
                    semantics_text,
                )

        # --------------------------------------------------
        # Final feature
        # --------------------------------------------------

        if current_feature:

            sections.append(
                self._format_section(
                    current_feature,
                    current_syntax,
                    current_semantics,
                )
            )

        return "\n\n".join(
            section
            for section in sections
            if section
        )

    # ==================================================
    # DETECT COLUMN GROUP
    # ==================================================

    def _detect_column_group(
        self,
        row,
        start_column,
        stop_column,
    ):

        if start_column is None:
            return []

        columns = []

        # The header itself may occupy one physical
        # column while the logical field spans multiple
        # physical columns.
        #
        # We therefore start with the detected column.
        columns.append(start_column)

        if stop_column is None:
            return columns

        # Don't cross into the next logical field.
        for index in range(
            start_column + 1,
            stop_column,
        ):
            columns.append(index)

        return columns

    # ==================================================
    # FEATURE TEXT
    # ==================================================

    def _get_feature_text(
        self,
        row,
        feature_column,
    ):

        if (
            feature_column is None
            or feature_column >= len(row)
        ):
            return ""

        return self._clean_cell(
            row[feature_column]
        )

    # ==================================================
    # GROUP TEXT
    # ==================================================

    def _get_group_text(
        self,
        row,
        columns,
    ):

        values = []

        for column in columns:

            if column >= len(row):
                continue

            value = self._clean_cell(
                row[column]
            )

            if not value:
                continue

            if value in values:
                continue

            values.append(value)

        return " ".join(values)

    # ==================================================
    # FORMAT SECTION
    # ==================================================

    def _format_section(
        self,
        feature,
        syntax,
        semantics,
    ):

        parts = []

        if feature:

            parts.append(
                f"Feature: {feature}"
            )

        if syntax:

            syntax_text = self._join_lines(
                syntax
            )

            parts.append(
                f"Syntax: {syntax_text}"
            )

        if semantics:

            semantics_text = self._join_lines(
                semantics
            )

            parts.append(
                f"Semantics: {semantics_text}"
            )

        return "\n".join(parts)

    # ==================================================
    # JOIN CONTINUATION LINES
    # ==================================================

    def _join_lines(self, values):

        cleaned = []

        for value in values:

            value = self._clean_cell(
                value
            )

            if not value:
                continue

            if not cleaned:
                cleaned.append(value)
                continue

            # Avoid duplicate text caused by merged
            # cells.
            if value == cleaned[-1]:
                continue

            # If the previous line ends naturally,
            # join with a space.
            cleaned.append(value)

        return " ".join(cleaned)

    # ==================================================
    # APPEND UNIQUE
    # ==================================================

    def _append_unique(
        self,
        target,
        value,
    ):

        value = self._clean_cell(
            value
        )

        if not value:
            return

        if value in target:
            return

        target.append(value)

    # ==================================================
    # EMPTY ROW
    # ==================================================

    def _is_empty_row(self, row):

        for cell in row:

            if self._clean_cell(cell):
                return False

        return True

    # ==================================================
    # CLEAN CELL
    # ==================================================

    def _clean_cell(self, value):

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

    # ==================================================
    # GENERIC FALLBACK
    # ==================================================

    def _normalize_generic_table(
        self,
        rows,
    ):

        sections = []

        for row in rows:

            values = []

            for cell in row:

                value = self._clean_cell(
                    cell
                )

                if not value:
                    continue

                if value in values:
                    continue

                values.append(value)

            if values:

                sections.append(
                    " | ".join(values)
                )

        return "\n".join(
            sections
        )
