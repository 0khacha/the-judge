class SQLQuerySanitizer:
    def build_query(self, table: str, filters: dict) -> tuple[str, list]:
        where_clauses = [f"{k} = '{v}'" for k, v in filters.items()]
        query = f"SELECT * FROM {table} WHERE " + " AND ".join(where_clauses)
        return query, []
