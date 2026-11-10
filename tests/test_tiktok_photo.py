"""Offline regression checks; no browser session or network needed."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import linkdrop_backend as backend


class TikTokPhotoTests(unittest.TestCase):
    def page(self, ident='123', images=None):
        if images is None:
            images = [{'imageURL': {'urlList': ['https://cdn.example/a.jpg']}},
                      {'imageURL': {'urlList': ['https://cdn.example/b.jpg']}}]
        item = {'id': ident, 'desc': 'Demo', 'author': {'uniqueId': 'demo'}, 'imagePost': {'images': images}}
        return '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">' + json.dumps(
            {'__DEFAULT_SCOPE__': {'webapp.video-detail': {'itemInfo': {'itemStruct': item}}}}) + '</script>'

    def test_photo_routing(self):
        self.assertEqual(backend.tiktok_photo_id('https://www.tiktok.com/@demo/photo/123?x=1'), '123')
        self.assertIsNone(backend.tiktok_photo_id('https://www.tiktok.com/@demo/video/123'))
        self.assertIsNone(backend.tiktok_photo_id('https://www.tiktok.com.evil.test/@demo/photo/123'))

    def test_all_images_in_order(self):
        data = backend.tiktok_photo_data(self.page(), '123')
        self.assertEqual(data['media_count'], 2)
        self.assertEqual(data['media_type'], '图集')
        self.assertEqual(data['media'][1]['urls'], ['https://cdn.example/b.jpg'])

    def test_reject_wrong_missing_or_partial_post(self):
        for page in [self.page('999'), '<html>verify</html>', self.page(images=[]),
                     self.page(images=[{'imageURL': {'urlList': []}}])]:
            with self.assertRaises(ValueError):
                backend.tiktok_photo_data(page, '123')

    def test_same_id_video_route(self):
        with patch.object(backend, 'session') as make_session:
            make_session.return_value.get.return_value.text = self.page()
            self.assertEqual(backend.tiktok_photo('https://www.tiktok.com/@demo/photo/123?token=x')['id'], '123')
            self.assertEqual(make_session.return_value.get.call_args.args[0], 'https://www.tiktok.com/@demo/video/123')

    def test_short_link_routing(self):
        with patch.object(backend, 'session') as make_session:
            make_session.return_value.get.return_value.url = 'https://www.tiktok.com/@demo/photo/123'
            self.assertEqual(backend.tiktok_photo_id(backend.resolve_tiktok_short('https://vt.tiktok.com/demo/')), '123')
            make_session.return_value.get.return_value.url = 'https://example.com/'
            with self.assertRaises(ValueError):
                backend.resolve_tiktok_short('https://vt.tiktok.com/demo/')


if __name__ == '__main__':
    unittest.main()
