from impl import DefectiveHandler
def test_visible():
    try:
        DefectiveHandler()
    except TypeError:
        pass
