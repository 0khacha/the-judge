PATCHES = {
    1: {"csvparse.py": [
        # no BOM handling, and line counter not advanced inside quotes
        ('    if text.startswith("\\ufeff"):\n        text = text[1:]\n', ''),
        ('                        line += 1\n                    elif c == "\\n":\n                        buf.append("\\n")\n                        i += 1\n                        line += 1\n',
         '                    elif c == "\\n":\n                        buf.append("\\n")\n                        i += 1\n'),
    ]},
    2: {"csvparse.py": [
        # blank-line skipping removed for \r only lines, whitespace stripped on unquoted fields, dup header allowed
        ('            fields.append(text[i:j])\n', '            fields.append(text[i:j].strip())\n'),
        ('    if len(set(header)) != len(header):\n        raise CsvError("duplicate column name")\n', ''),
    ]},
}
