from stocklook.utils.security import *
from stocklook.config import config


def test_set_object_vars():
    c = Credentials()
    svc_name = "__test_object_service_name__"
    try:
        keyring.delete_password(svc_name, 'user1')
    except:
        pass

    class TestObj:
        c.register_config_object_mapping(
            svc_name, {'TEST_OBJ_UN': 'username',
                       'TEST_OBJ_PW': 'password',
                       'TEST_OBJ_SECRET': 'secret'})
        def __init__(self):
            self.username = None
            self.password = None
            self.secret = None

    # Simulate all credentials needed have been stored in config
    o = TestObj()
    config.update({'TEST_OBJ_UN': 'user1',
                   'TEST_OBJ_PW': 'pw1',
                   'TEST_OBJ_SECRET': 'secret1'})
    c.configure_object_vars(o, svc_name, 'username', ['password', 'secret'])
    assert o.username == 'user1'
    assert o.password == 'pw1'
    assert o.secret == 'secret1'

    # Simulate empty config but password is stored in keyring.
    config.clear()
    o2 = TestObj()
    o2.username = 'user1'
    c.configure_object_vars(o2, svc_name, 'username', ['password', 'secret'])
    assert o2.password == 'pw1'
    assert o2.secret == 'secret1'

    keyring.delete_password(svc_name, 'user1')




