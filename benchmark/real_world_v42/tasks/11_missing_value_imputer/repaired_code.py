class MissingValueImputer:
    def impute(self, values: list, strategy: str = "mean", fill_value=0) -> list:
        if strategy == "constant":
            return [fill_value if v is None else v for v in values]
        elif strategy == "ffill":
            out = []
            last = None
            for v in values:
                if v is not None:
                    last = v
                out.append(last)
            return out
        else: # mean
            valid = [v for v in values if v is not None]
            avg = sum(valid) / len(valid) if valid else 0
            return [avg if v is None else v for v in values]
