import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_updates as updates
import push_tags as app


class AppUpdateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.release = self.release_for('v0.2.0')

    def release_for(self, tag):
        prefix = f'https://github.com/{updates.REPOSITORY}/releases'
        return {'tag_name': tag, 'draft': False, 'prerelease': False,
                'published_at': '2026-11-25T12:00:00Z', 'html_url': f'{prefix}/tag/{tag}',
                'assets': [{'name': 'Code-Push-Tags-macOS.dmg', 'state': 'uploaded',
                            'browser_download_url': f'{prefix}/download/{tag}/Code-Push-Tags-macOS.dmg'}]}

    def check(self, current='0.1.0', now=100000, force=False, release=None):
        with patch.object(updates.time, 'time', return_value=now), \
                patch.object(updates, 'fetch_release', return_value=self.release if release is None else release) as fetch:
            result = updates.check(current, force=force)
        return result, fetch

    def test_newer_release_has_expected_download(self):
        result, _ = self.check()
        self.assertTrue(result['update_available'])
        self.assertEqual(result['latest_version'], '0.2.0')
        self.assertEqual(result['download_url'], self.release['assets'][0]['browser_download_url'])

    def test_current_or_ahead_has_no_update(self):
        for current in ('0.2.0', '0.3.0', 'v0.2.0'):
            with self.subTest(current=current):
                result, _ = self.check(current)
                self.assertFalse(result['update_available'])

    def test_numeric_comparison_and_prefix(self):
        result, _ = self.check('v0.9.0', release=self.release_for('v0.10.0'))
        self.assertTrue(result['update_available'])

    def test_cache_is_compared_with_each_installed_version(self):
        self.check('0.1.0')
        result, fetch = self.check('0.2.0', now=100001)
        fetch.assert_not_called()
        self.assertFalse(result['update_available'])
        self.assertEqual(result['current_version'], '0.2.0')

    def test_hourly_boundary_and_force(self):
        self.check()
        _, fetch = self.check(now=103599)
        fetch.assert_not_called()
        _, fetch = self.check(now=103600)
        fetch.assert_called_once_with()
        _, fetch = self.check(now=103601, force=True)
        fetch.assert_called_once_with()

    def test_draft_prerelease_or_unpublished_is_not_announced(self):
        for field, value in (('draft', True), ('prerelease', True), ('published_at', None)):
            with self.subTest(field=field):
                release = copy.deepcopy(self.release)
                release[field] = value
                result, _ = self.check(force=True, release=release)
                self.assertFalse(result['update_available'])
                self.assertIsNone(result['download_url'])
                self.assertIn('error', result)

    def test_invalid_release_version_is_not_guessed(self):
        for tag in ('0.2', 'v0.2.0-rc.1', 'banana', 'v00.2.0', None):
            with self.subTest(tag=tag):
                release = copy.deepcopy(self.release)
                release['tag_name'] = tag
                result, _ = self.check(force=True, release=release)
                self.assertFalse(result['update_available'])
                self.assertIsNone(result['latest_version'])

    def test_invalid_current_version_does_not_fetch(self):
        result, fetch = self.check('unversioned')
        fetch.assert_not_called()
        self.assertFalse(result['update_available'])
        self.assertIn('error', result)

    def test_zip_is_used_if_dmg_is_missing(self):
        release = copy.deepcopy(self.release)
        asset = release['assets'][0]
        asset['name'] = 'Code-Push-Tags-macOS.zip'
        asset['browser_download_url'] = asset['browser_download_url'].replace('.dmg', '.zip')
        result, _ = self.check(release=release)
        self.assertTrue(result['update_available'])
        self.assertTrue(result['download_url'].endswith('.zip'))

    def test_release_without_supported_assets_is_not_announced(self):
        release = copy.deepcopy(self.release)
        release['assets'] = []
        result, _ = self.check(release=release)
        self.assertFalse(result['update_available'])
        self.assertIsNone(result['download_url'])

    def test_incomplete_asset_upload_is_not_announced(self):
        release = copy.deepcopy(self.release)
        release['assets'][0]['state'] = 'starter'
        result, _ = self.check(release=release)
        self.assertFalse(result['update_available'])
        self.assertIsNone(result['download_url'])

    def test_urls_must_match_expected_repository_and_tag(self):
        for bad in ('https://evil.example/file.dmg',
                    'https://github.com.evil.example/murbany-lola/code-push-tags/releases/download/v0.2.0/Code-Push-Tags-macOS.dmg',
                    'https://github.com/another/repo/releases/download/v0.2.0/Code-Push-Tags-macOS.dmg',
                    self.release['assets'][0]['browser_download_url'] + '?secret=1'):
            with self.subTest(url=bad):
                release = copy.deepcopy(self.release)
                release['assets'][0]['browser_download_url'] = bad
                result, _ = self.check(force=True, release=release)
                self.assertFalse(result['update_available'])
                self.assertIsNone(result['download_url'])
        release = copy.deepcopy(self.release)
        release['html_url'] = 'https://github.com/another/repo/releases/tag/v0.2.0'
        result, _ = self.check(force=True, release=release)
        self.assertFalse(result['update_available'])

    def test_offline_first_check_has_no_notice(self):
        with patch.object(updates.time, 'time', return_value=100000), \
                patch.object(updates, 'fetch_release', side_effect=OSError('offline')):
            result = updates.check('0.1.0')
        self.assertFalse(result['update_available'])
        self.assertIn('error', result)
        self.assertIsNone(result['download_url'])

    def test_offline_refresh_keeps_known_published_release(self):
        self.check()
        with patch.object(updates.time, 'time', return_value=104000), \
                patch.object(updates, 'fetch_release', side_effect=OSError('offline')):
            result = updates.check('0.1.0')
        self.assertTrue(result['update_available'])
        self.assertEqual(result['latest_version'], '0.2.0')
        self.assertIn('error', result)
        result, fetch = self.check(now=104001)
        fetch.assert_not_called()
        self.assertIn('error', result)

    def test_corrupt_cache_is_replaced(self):
        (app.state_dir() / 'app-update-check.json').write_text('{broken')
        result, fetch = self.check()
        fetch.assert_called_once_with()
        self.assertTrue(result['update_available'])

    def test_cached_urls_are_revalidated(self):
        self.check()
        path = app.state_dir() / 'app-update-check.json'
        cache = json.loads(path.read_text())
        cache['release']['assets'][0]['browser_download_url'] = 'https://evil.example/file.dmg'
        path.write_text(json.dumps(cache))
        result, fetch = self.check(now=100001)
        fetch.assert_not_called()
        self.assertFalse(result['update_available'])
        self.assertIsNone(result['download_url'])


if __name__ == '__main__':
    unittest.main()
