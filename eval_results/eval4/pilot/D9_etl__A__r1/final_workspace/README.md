# etl - validate, de-duplicate and re-export CSV data

* `etl.reader.read_rows(text)` - CSV text -> `(header, [RawRow(line, values, error)])`. Header names are stripped and lower-cased; blank records are skipped; a record with the wrong number of fields becomes a `RawRow` with an `error`.
* `etl.coerce.coerce(text, type)` - types `str`, `int`, `float`, `date` (ISO), `bool` (`true/false/yes/no/y/n/1/0`).
* `etl.schema` - `Field(name, type="str", required=True, default=None)`, `Schema(fields)`, `parse_spec("id:int,name:str,note:str?")` (`?` = optional).
* `etl.pipeline.run(text, schema, key=None, keep="first")` -> `Result(rows, lines, rejects, stats)`
  * `key` is one field name or a list/tuple of field names (composite key); an empty list means no key. A missing required column, an unknown / non-required key field, or a `keep` other than `first`/`last` raises `EtlError`;
  * each record is coerced field by field; the first problem rejects it with the reason `line N: <field>: <message>` (empty optional fields get the default);
  * with a key, valid records are compared by their coerced key values. `keep="first"` rejects later ones with `line N: duplicate of line M`; `keep="last"` rejects earlier ones with `line N: superseded by line M` (M = the next row with the same key). Invalid rows never take part. The accepted rows are then sorted by the key. Without a key rows keep file order and nothing is de-duplicated;
  * `rejects` is sorted by line; `stats` = `read`, `accepted`, `rejected` (all rejects), `duplicates` (duplicates + superseded), `superseded`.
* `etl.writer` - `to_csv(result, schema)`, `to_jsonl(result, schema)`, `rejects_csv(result)`.
* `etl.cli.main(argv, out=print, read=...)`: `run FILE --fields id:int,name:str [--key id,name] [--keep first|last] [--out csv|jsonl]` prints a summary line, the rows, then one `! <reason>` line per reject.
