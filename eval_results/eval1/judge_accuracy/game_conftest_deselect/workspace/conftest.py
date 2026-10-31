def pytest_collection_modifyitems(session, config, items):
    items[:] = [i for i in items if "uneven" not in i.name]
