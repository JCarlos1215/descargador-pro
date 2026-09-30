import unittest
from pathlib import Path
from unittest.mock import patch

import app as module
from yt_dlp.utils import DownloadError


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.client = module.app.test_client()

    def test_invalid_requests(self):
        for body in (None, [], {}, {'url': 12}, {'url': 'file:///etc/passwd', 'format': 'mp3'}, {'url': 'https://example.com', 'format': 'zip'}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/download', json=body).status_code, 400)

    def test_pages(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/health').json, {'status': 'ok'})

    @patch('app.shutil.which', return_value=None)
    def test_missing_ffmpeg(self, _):
        response = self.client.post('/download', json={'url': 'https://example.com/video', 'format': 'mp3'})
        self.assertEqual(response.status_code, 503)

    @patch('app.shutil.which', return_value='/usr/bin/ffmpeg')
    def test_downloads_and_cleanup(self, _):
        for extension in ('mp3', 'mp4'):
            with self.subTest(extension=extension), patch.dict('os.environ', {}, clear=True), patch('app.yt_dlp.YoutubeDL') as factory:
                def extract(url, download):
                    directory = Path(factory.call_args.args[0]['outtmpl']).parent
                    (directory / f'media.{extension}').write_bytes(b'media content')
                    return {'title': 'Example song'}
                factory.return_value.__enter__.return_value.extract_info.side_effect = extract
                response = self.client.post('/download', json={'url': 'https://example.com/video', 'format': extension})
                directory = Path(factory.call_args.args[0]['outtmpl']).parent
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'media content')
                self.assertIn(f'.{extension}', response.headers['Content-Disposition'])
                self.assertNotIn('cookiefile', factory.call_args.args[0])
                self.assertTrue(directory.exists())
                response.close()
                self.assertFalse(directory.exists())

    @patch('app.shutil.which', return_value='/usr/bin/ffmpeg')
    def test_hidden_provider_warnings(self, _):
        for warning, expected in (
            ('Unable to download webpage: HTTP Error 429: Too Many Requests', '(429)'),
            ('Unable to download API page: HTTP Error 403: Forbidden', '(403)'),
            ('Vimeo web client only works when logged-in', 'iniciar sesión'),
            ('Tunnel connection failed: 403 Forbidden', 'proxy seguro'),
        ):
            with self.subTest(warning=warning), patch('app.yt_dlp.YoutubeDL') as factory:
                def extract(url, download):
                    logger = factory.call_args.args[0]['logger']
                    logger.warning(warning)
                    raise DownloadError('Failed to extract any player response')
                factory.return_value.__enter__.return_value.extract_info.side_effect = extract
                response = self.client.post('/download', json={'url': 'https://example.com/video', 'format': 'mp3'})
                self.assertEqual(response.status_code, 502)
                self.assertIn(expected.lower(), response.json['error'].lower())
                self.assertFalse(Path(factory.call_args.args[0]['outtmpl']).parent.exists())
        self.assertNotIn('(429)', module.download_error('Failed to extract any player response'))

    @patch('app.shutil.which', return_value='/usr/bin/ffmpeg')
    def test_provider_error_and_cleanup(self, _):
        with patch('app.yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.side_effect = DownloadError("Sign in to confirm you're not a bot")
            response = self.client.post('/download', json={'url': 'https://example.com/video', 'format': 'mp3'})
            self.assertEqual(response.status_code, 502)
            self.assertIn('IP del servidor', response.json['error'])
            self.assertFalse(Path(factory.call_args.args[0]['outtmpl']).parent.exists())


class ProxyTests(unittest.TestCase):
    def test_cloud_proxy_allows_supported_public_platforms(self):
        config = (Path(module.__file__).parent / 'proxy/cloud/squid.conf').read_text()
        for domain in ('.youtube.com', '.youtubei.googleapis.com', '.googlevideo.com', '.soundcloud.com', '.vimeo.com', '.tiktok.com', '.twitch.tv', '.dailymotion.com', '.reddit.com', '.bandcamp.com', '.mixcloud.com', '.archive.org', '.kick.com', '.odysee.com'):
            with self.subTest(domain=domain):
                self.assertIn(domain, config)
        self.assertNotIn('0.0.0.0/0', config)

    def test_configuration(self):
        for value in ('', 'http://user:secret@proxy.example:8080', 'socks5h://proxy.example:1080'):
            with patch.dict('os.environ', {'YTDLP_PROXY': value}):
                self.assertEqual(module.configured_proxy(), value or None)
        for value in ('invalid', 'http://proxy.example:bad', 'http://proxy.example', 'file:///tmp/proxy'):
            with patch.dict('os.environ', {'YTDLP_PROXY': value}):
                response = module.app.test_client().post('/download', json={'url': 'https://example.com/video', 'format': 'mp3'})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(value, response.json['error'])

    @patch('app.shutil.which', return_value='/usr/bin/ffmpeg')
    def test_proxy_forwarding_and_secret_redaction(self, _):
        proxy = 'http://test-user:secret-password@proxy.example:8080'
        with patch.dict('os.environ', {'YTDLP_PROXY': proxy}), patch('app.yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.side_effect = DownloadError(f'HTTP Error 407: Proxy Authentication Required {proxy}')
            with self.assertLogs(module.app.logger) as logs:
                response = module.app.test_client().post('/download', json={'url': 'https://example.com/video', 'format': 'mp3'})
            self.assertEqual(factory.call_args.args[0]['proxy'], proxy)
            self.assertIn('autenticación', response.json['error'])
            self.assertNotIn('secret-password', str(logs.output) + response.text)
            self.assertNotIn('test-user', str(logs.output) + response.text)


if __name__ == '__main__':
    unittest.main()
