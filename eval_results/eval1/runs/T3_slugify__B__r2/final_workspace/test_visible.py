from slug import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_accents():
    assert slugify("Caf\u00e9 au lait") == "cafe-au-lait"
