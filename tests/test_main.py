import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

try:
    from astrbot_plugin_jmcomic.main import Comp, JMComicPlugin
except ModuleNotFoundError as error:
    Comp = None
    JMComicPlugin = None
    MAIN_IMPORT_ERROR = str(error)
else:
    MAIN_IMPORT_ERROR = ""


DETAIL = {
    "id": "12345",
    "title": "测试漫画",
    "tags": ["标签"],
    "author": "作者",
    "page_count": 10,
}


@unittest.skipIf(JMComicPlugin is None, f"缺少项目依赖：{MAIN_IMPORT_ERROR}")
class DetailResultTest(unittest.IsolatedAsyncioTestCase):
    def make_plugin(self, *, show_cover: bool) -> JMComicPlugin:
        plugin = object.__new__(JMComicPlugin)
        plugin.config = {"show_cover": show_cover}
        plugin.service = Mock()
        plugin.service.get_cover = AsyncMock(return_value=Path("/tmp/12345.jpg"))
        return plugin

    async def test_disabled_cover_returns_plain_text_without_download(self) -> None:
        plugin = self.make_plugin(show_cover=False)
        event = Mock()
        expected_result = object()
        event.plain_result.return_value = expected_result

        result = await plugin._detail_result(event, DETAIL)

        self.assertIs(result, expected_result)
        plugin.service.get_cover.assert_not_awaited()
        event.plain_result.assert_called_once_with(plugin._format_detail(DETAIL))

    async def test_enabled_cover_returns_image_and_text_chain(self) -> None:
        plugin = self.make_plugin(show_cover=True)
        event = Mock()
        image = object()
        plain = object()
        expected_result = object()
        event.chain_result.return_value = expected_result

        with (
            patch.object(Comp.Image, "fromFileSystem", return_value=image),
            patch.object(Comp, "Plain", return_value=plain) as plain_component,
        ):
            result = await plugin._detail_result(
                event,
                DETAIL,
                prefix="随机推荐\n",
            )

        self.assertIs(result, expected_result)
        plugin.service.get_cover.assert_awaited_once_with("12345")
        plain_component.assert_called_once_with(
            f"随机推荐\n{plugin._format_detail(DETAIL)}"
        )
        event.chain_result.assert_called_once_with([image, plain])

    async def test_cover_failure_falls_back_to_plain_text(self) -> None:
        plugin = self.make_plugin(show_cover=True)
        plugin.service.get_cover.side_effect = RuntimeError("cover failed")
        event = Mock()
        expected_result = object()
        event.plain_result.return_value = expected_result

        result = await plugin._detail_result(event, DETAIL)

        self.assertIs(result, expected_result)
        event.plain_result.assert_called_once_with(plugin._format_detail(DETAIL))
        event.chain_result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
