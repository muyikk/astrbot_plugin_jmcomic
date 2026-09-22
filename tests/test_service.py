import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    from astrbot_plugin_jmcomic.jm_service import JMComicService, ServiceConfig
except ModuleNotFoundError as error:
    JMComicService = None
    ServiceConfig = None
    JMCOMIC_IMPORT_ERROR = str(error)
else:
    JMCOMIC_IMPORT_ERROR = ""


@unittest.skipIf(ServiceConfig is None, f"缺少项目依赖：{JMCOMIC_IMPORT_ERROR}")
class ServiceConfigTest(unittest.TestCase):
    def test_shard_pages_default(self) -> None:
        self.assertEqual(ServiceConfig.from_mapping({}).shard_pages, 250)


@unittest.skipIf(JMComicService is None, f"缺少项目依赖：{JMCOMIC_IMPORT_ERROR}")
class CacheCleanupTest(unittest.IsolatedAsyncioTestCase):
    async def test_clear_cache_preserves_generated_option(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            service = JMComicService(data_dir, ServiceConfig())
            service.download_dir.mkdir()
            service.pdf_dir.mkdir()
            album_dir = service.download_dir / "[1]test"
            album_dir.mkdir()
            (album_dir / "1.jpg").write_bytes(b"image")
            (service.pdf_dir / "1.pdf").write_bytes(b"pdf")
            service.option_path.write_text("keep", encoding="utf-8")

            result = await service.clear_cache()

            self.assertEqual(result, {"files": 2, "bytes": 8})
            self.assertEqual(list(service.download_dir.iterdir()), [])
            self.assertEqual(list(service.pdf_dir.iterdir()), [])
            self.assertEqual(service.option_path.read_text(encoding="utf-8"), "keep")


@unittest.skipIf(JMComicService is None, f"缺少项目依赖：{JMCOMIC_IMPORT_ERROR}")
class RandomDetailTest(unittest.IsolatedAsyncioTestCase):
    async def test_random_detail_uses_random_catalogue_page(self) -> None:
        service = JMComicService(Path("/tmp/jmcomic-random-test"), ServiceConfig())
        service.categories = AsyncMock(
            side_effect=[
                ([{"id": "1", "title": "first"}], 3, 2),
                ([{"id": "9", "title": "selected"}], 3, 2),
            ]
        )
        expected = {
            "id": "9",
            "title": "selected",
            "tags": [],
            "author": "",
            "page_count": 1,
        }
        service.detail = AsyncMock(return_value=expected)

        with (
            patch("astrbot_plugin_jmcomic.jm_service.random.randint", return_value=3),
            patch(
                "astrbot_plugin_jmcomic.jm_service.random.choice",
                return_value={"id": "9", "title": "selected"},
            ),
        ):
            result = await service.random_detail()

        self.assertEqual(result, expected)
        service.detail.assert_awaited_once_with("9")


if __name__ == "__main__":
    unittest.main()
