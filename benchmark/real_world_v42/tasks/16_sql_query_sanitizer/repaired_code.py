class SQLQuerySanitizer:
    def build_query(self, table: str, filters: dict) -> tuple[str, list]:
        # Validate table identifier (alphanumeric/underscore only)
        if not table.isidentifier():
            raise ValueError("Invalid table identifier")
        params = []
        clauses = []
        for k, v in filters.items():
            if not k.isidentifier():
                raise ValueError("Invalid column identifier")
            clauses.append(f"{k} = ?")
            params.append(v)
        query = f"SELECT * FROM {table} WHERE " + " AND ".join(clauses)
        return query, params
