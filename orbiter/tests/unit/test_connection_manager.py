import unittest
import tempfile
import yaml
from unittest.mock import patch

from orbiter.core.broker import connection as connection_mod


class FakeApi:
    def __init__(self, login_ok=True):
        self.login_ok = login_ok
        self.start_websocket_args = None
        self.subscribed = False
        self.subscribed_orders = False
        self.closed = False

    def login(self, **kwargs):
        if self.login_ok:
            return {'stat': 'Ok'}
        return {'stat': 'Not_Ok', 'emsg': 'bad'}

    def start_websocket(self, subscribe_callback=None, socket_open_callback=None, order_update_callback=None):
        self.start_websocket_args = (subscribe_callback, socket_open_callback, order_update_callback)
        if socket_open_callback:
            socket_open_callback()
        if subscribe_callback:
            subscribe_callback({'lp': '100', 'tk': '123', 'e': 'NSE'})

    def subscribe(self, symbols, feed_type='d'):
        self.subscribed = True

    def subscribe_orders(self):
        self.subscribed_orders = True

    def close_websocket(self):
        self.closed = True


class TestConnectionManager(unittest.TestCase):
    def _write_creds(self):
        creds = {
            'user': 'U',
            'pwd': 'P',
            'factor2': '',
            'vc': 'V',
            'apikey': 'K',
            'imei': 'I'
        }
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml')
        yaml.dump(creds, tmp)
        tmp.flush()
        return tmp.name

    def test_login_success(self):
        cred_path = self._write_creds()
        fake_api = FakeApi(login_ok=True)

        with patch.object(connection_mod, 'ShoonyaApiPy', lambda: fake_api):
            cm = connection_mod.ConnectionManager(config_path=cred_path)
            ok = cm.login(factor2_override='1234')

        self.assertTrue(ok)
        self.assertEqual(getattr(fake_api, '_NorenApi__username', None), 'U')
        self.assertEqual(getattr(fake_api, '_NorenApi__accountid', None), 'U')

    def test_login_failure(self):
        cred_path = self._write_creds()
        fake_api = FakeApi(login_ok=False)

        with patch.object(connection_mod, 'ShoonyaApiPy', lambda: fake_api):
            cm = connection_mod.ConnectionManager(config_path=cred_path)
            ok = cm.login(factor2_override='1234')

        self.assertFalse(ok)

    def test_start_live_feed_and_close(self):
        cred_path = self._write_creds()
        fake_api = FakeApi(login_ok=True)
        received = []

        def on_tick(message, token, exch):
            received.append((message, token, exch))

        with patch.object(connection_mod, 'ShoonyaApiPy', lambda: fake_api):
            cm = connection_mod.ConnectionManager(config_path=cred_path)
            cm.start_live_feed(['NSE|123'], on_tick_callback=on_tick)
            self.assertTrue(cm.socket_opened)
            self.assertTrue(fake_api.subscribed)
            self.assertTrue(fake_api.subscribed_orders)

            cm.close()
            self.assertTrue(fake_api.closed)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][1], '123')


if __name__ == '__main__':
    unittest.main()
