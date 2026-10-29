# etl - validate, de-duplicate and re-export CSV data

* `etl.reader.read_rows(text)` - CSV text -> `(header, [RawRow(line, values, error)])`. Header names are stripped and lower-cased; blank records are skipped; a record with the wrong number of fields becomes a `RawRow` with an `error`.
* `etl.coerce.coerce(text, type)` - types `str`, `int`, `float`, `date` (ISO), `bool` (`true/false/yes/no/y/n/1/0`).
* `etl.schema` - `Field(name, type="str", required=True, default=None)`, `Schema(fields)`, `parse_spec("id:int,name:str,note:str?")` (`?` = optional).
* `etl.pipeline.run(text, schema, key=None)` -> `Result(rows, lines, rejects, stats)`
  * a missing required column or an unknown / non-required key field raises `EtlError`;
  * each record is coerced field by field; the first problem rejects it with the reason `line N: <field>: <message>` (empty optional fields get the default);
  * with a `key` (one field name) the later records with an already seen key value are rejected with `line N: duplicate of line M`; the accepted rows are then sorted by the key. Without a key rows keep file order;
  * `rejects` is sorted by line; `stats` = `read`, `accepted`, `rejected` (invalid + duplicates), `duplicates`.
* `etl.writer` - `to_csv(result, schema)`, `to_jsonl(result, schema)`, `rejects_csv(result)`.
* `etl.cli.main(argv, out=print, read=...)`: `run FILE --fields id:int,name:str [--key id,name] [--keep first|last] [--out csv|jsonl]` prints a summary line, the rows, then one `! <reason>` line per reject.
