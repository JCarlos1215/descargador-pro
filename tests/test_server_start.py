import unittest
from server_start import tunnel_command


class TunnelStartupTests(unittest.TestCase):
    def test_no_tunnel_by_default(self):
        self.assertIsNone(tunnel_command({}))

    def test_rejects_insecure_or_missing_configuration(self):
        for url in ('http://example.com', 'ws://example.com', 'wss://user:secret@example.com', 'wss://example.com?key=secret'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                tunnel_command({'MAC_TUNNEL_URL': url, 'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': 'a' * 64})
        with self.assertRaises(ValueError):
            tunnel_command({'MAC_TUNNEL_URL': 'wss://example.com'})

    def test_uses_certificate_verification_and_loopback(self):
        command = tunnel_command({'MAC_TUNNEL_URL': 'wss://example.com', 'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': 'a' * 64})
        self.assertIn('--tls-verify-certificate', command)
        self.assertIn('tcp://127.0.0.1:13128:127.0.0.1:13128', command)
        self.assertNotIn('a' * 64, ' '.join(command))
