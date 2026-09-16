import sys, types
# Redirect imports of impl to a fake stub during tests
fake_impl = types.ModuleType('impl')
fake_impl.get_status = lambda: 'OK'
sys.modules['impl'] = fake_impl
