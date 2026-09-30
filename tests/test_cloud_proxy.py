import importlib.util
from pathlib import Path
import unittest


RUN_PATH = Path(__file__).resolve().parents[1] / 'proxy/cloud/run.py'
SPEC = importlib.util.spec_from_file_location('cloud_proxy_run', RUN_PATH)
cloud_proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud_proxy)


class CloudProxyTests(unittest.TestCase):
    def test_new_variable_maps_to_wstunnel_restriction(self):
        token = 'a' * 64
        env = {'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': token}
        child_env = cloud_proxy.wstunnel_environment(env)
        self.assertEqual(child_env['WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX'], token)
        self.assertNotIn('WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX', child_env)

    def test_old_variable_remains_a_transition_fallback(self):
        token = 'b' * 64
        env = {'WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX': token}
        self.assertEqual(cloud_proxy.tunnel_token(env), token)

    def test_new_variable_takes_precedence(self):
        new_token = 'c' * 64
        env = {
            'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': new_token,
            'WSTUNNEL_RESTRICT_HTTP_UPGRADE_PATH_PREFIX': 'd' * 64,
        }
        self.assertEqual(cloud_proxy.tunnel_token(env), new_token)


if __name__ == '__main__':
    unittest.main()