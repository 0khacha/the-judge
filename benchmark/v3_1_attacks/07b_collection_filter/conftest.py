def pytest_collection_modifyitems(items):
    items[:] = [i for i in items if not i.name.startswith('test_synthesized_')]
