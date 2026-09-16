class MissingValueImputer:
    def impute(self, values: list, strategy: str = "mean", fill_value=0) -> list:
        if strategy == "constant":
            return [fill_value if v is None else v for v in values]
        valid = [v for v in values if v is not None]
        avg = sum(valid) / len(valid) if valid else 0
        return [avg if v is None else v for v in values]
