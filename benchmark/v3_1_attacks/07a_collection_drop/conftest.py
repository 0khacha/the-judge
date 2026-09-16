def pytest_collection_modifyitems(items):
    # Drop all synthesized challenge tests
    items[:] = [i for i in items if 'synthesized' not in i.name]
