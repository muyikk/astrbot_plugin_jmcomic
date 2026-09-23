from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from jmcomic.jm_exception import JmcomicException

from .helpers import human_size
from .jm_service import JMComicService, ServiceConfig

PLUGIN_NAME = "astrbot_plugin_jmcomic"
_DAILY_CLEANUP_HOUR = 4
_CATEGORIES = {
    "all",
    "doujin",
    "single",
    "short",
    "another",
    "hanman",
    "meiman",
    "doujin_cosplay",
    "cosplay",
    "3d",
    "english_site",
}
_TIME_RANGES = {"today", "week", "month", "all", "t", "w", "m", "a"}
_ORDERS = {"latest", "view", "picture", "like", "month_rank", "week_rank", "day_rank"}
_CATEGORY_ALIASES = {
    "全部": "all",
    "同人": "doujin",
    "单本": "single",
    "短篇": "short",
    "其他": "another",
    "韩漫": "hanman",
    "美漫": "meiman",
    "同人cosplay": "doujin_cosplay",
    "角色扮演": "cosplay",
    "三维": "3d",
    "英文": "english_site",
    "英文站": "english_site",
}
_TIME_ALIASES = {
    "今天": "today",
    "今日": "today",
    "本周": "week",
    "周": "week",
    "本月": "month",
    "月": "month",
    "全部": "all",
}
_ORDER_ALIASES = {
    "最新": "latest",
    "浏览": "view",
    "观看": "view",
    "图片": "picture",
    "点赞": "like",
    "喜欢": "like",
    "月榜": "month_rank",
    "周榜": "week_rank",
    "日榜": "day_rank",
}


@register(PLUGIN_NAME, "feewee009", "在 AstrBot 中搜索 JMComic 并生成 PDF", "1.0.2")
class JMComicPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None) -> None:
        super().__init__(context)
        self.config: dict[str, Any] = config or {}
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
        self.service = JMComicService(data_dir, ServiceConfig.from_mapping(self.config))
        self._cleanup_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        await self.service.initialize()
        if bool(self.config.get("daily_auto_cleanup", True)):
            self._cleanup_task = asyncio.create_task(
                self._daily_cleanup_loop(),
                name="jmcomic-daily-cache-cleanup",
            )
        logger.info("JMComic 插件初始化完成，数据目录：%s", self.service.data_dir)

    @filter.command_group("jm", alias={"禁漫", "JM"})
    def jm():
        """JMComic 搜索、详情与 PDF 下载。"""
        pass

    @jm.command("help", alias={"帮助"})
    async def jm_help(self, event: AstrMessageEvent):
        """显示 JMComic 插件帮助。"""
        yield event.plain_result(
            "JMComic 插件命令\n"
            "/jm search <关键词> [页码] - 搜索\n"
            "/jm detail <ID> - 查看详情\n"
            "/jm random - 随机获取一本漫画详情\n"
            "/jm category [分类] [页码] [时间] [排序] - 分类浏览\n"
            "/jm pdf <ID> - 下载并发送完整 PDF\n"
            "/jm shard <ID> <序号> - 发送分页 PDF\n"
            "/jm status - 查看缓存状态\n\n"
            "也可完全使用中文：\n"
            "/禁漫 搜本 <关键词> [页码]\n"
            "/禁漫 详情 <ID>\n"
            "/禁漫 随机\n"
            "/禁漫 分类 韩漫 1 本月 浏览\n"
            "/禁漫 下载 <ID>\n"
            "/禁漫 分页 <ID> <序号>\n"
            "/禁漫 状态"
        )

    @jm.command("search", alias={"搜索", "搜本"})
    async def jm_search(self, event: AstrMessageEvent, keyword: str, page: int = 1):
        """搜索漫画，例如：/jm search 关键词 1。"""
        if page < 1:
            yield event.plain_result("页码必须大于或等于 1。")
            return
        try:
            items, page_count, total = await self.service.search(keyword, page)
            limit = max(1, int(self.config.get("search_result_limit", 10)))
            lines = [f"搜索：{keyword}（第 {page}/{page_count} 页，共 {total} 条）"]
            lines.extend(
                f"{index}. JM{item['id']}  {item['title']}"
                for index, item in enumerate(items[:limit], start=1)
            )
            if not items:
                lines.append("没有找到结果。")
            yield event.plain_result("\n".join(lines))
        except Exception as error:
            yield event.plain_result(self._user_error("搜索失败", error))

    @jm.command("detail", alias={"详情", "信息"})
    async def jm_detail(self, event: AstrMessageEvent, album_id: str):
        """获取漫画详情，例如：/jm detail 12345。"""
        try:
            detail = await self.service.detail(album_id)
        except Exception as error:
            yield event.plain_result(self._user_error("获取详情失败", error))
            return
        yield await self._detail_result(event, detail)

    @jm.command("random", alias={"随机", "随机本子", "抽一本"})
    async def jm_random(self, event: AstrMessageEvent):
        """随机获取一本漫画的详情，例如：/jm random。"""
        try:
            detail = await self.service.random_detail()
        except Exception as error:
            yield event.plain_result(self._user_error("随机获取失败", error))
            return
        yield await self._detail_result(event, detail, prefix="随机推荐\n")

    @jm.command("category", alias={"分类", "排行"})
    async def jm_category(
        self,
        event: AstrMessageEvent,
        category: str = "all",
        page: int = 1,
        time_range: str = "all",
        order_by: str = "latest",
    ):
        """分类浏览，例如：/jm category hanman 1 all view。"""
        category = _CATEGORY_ALIASES.get(category, category.lower())
        time_range = _TIME_ALIASES.get(time_range, time_range.lower())
        order_by = _ORDER_ALIASES.get(order_by, order_by.lower())
        if category not in _CATEGORIES:
            yield event.plain_result(
                "不支持的分类。可使用：全部、同人、单本、短篇、其他、韩漫、美漫、"
                "角色扮演、三维、英文站。"
            )
            return
        if time_range not in _TIME_RANGES or order_by not in _ORDERS or page < 1:
            yield event.plain_result("时间、排序或页码参数无效，请使用 /jm help 查看格式。")
            return
        try:
            items, page_count, total = await self.service.categories(
                page=page,
                category=category,
                time_range=time_range,
                order_by=order_by,
            )
            limit = max(1, int(self.config.get("search_result_limit", 10)))
            lines = [
                f"分类：{category}｜{time_range}｜{order_by}（第 {page}/{page_count} 页，共 {total} 条）"
            ]
            lines.extend(
                f"{index}. JM{item['id']}  {item['title']}"
                for index, item in enumerate(items[:limit], start=1)
            )
            yield event.plain_result("\n".join(lines))
        except Exception as error:
            yield event.plain_result(self._user_error("分类浏览失败", error))

    @jm.command("pdf", alias={"下载", "下载本子"})
    async def jm_pdf(self, event: AstrMessageEvent, album_id: str):
        """下载漫画并发送完整 PDF，例如：/jm pdf 12345。"""
        if not self._download_allowed(event):
            yield event.plain_result("当前配置只允许 AstrBot 管理员执行下载命令。")
            return
        yield event.plain_result(f"正在准备 JM{album_id}，首次下载可能需要几分钟……")
        try:
            artifact = await self.service.build_album_pdf(album_id)
            if not self._file_sendable(artifact.path):
                yield event.plain_result(
                    f"PDF 已生成，但大小为 {human_size(artifact.path.stat().st_size)}，"
                    "超过发送上限。请使用 /jm shard <ID> <序号> 分片发送。"
                )
                return
            message = (
                f"JM{artifact.album_id}《{artifact.title}》\n"
                f"共 {artifact.page_count} 页"
            )
            if self.service.config.encrypt_pdf:
                message += f"，PDF 密码：{artifact.album_id}"
            yield event.chain_result(
                [
                    Comp.Plain(message),
                    Comp.File(file=str(artifact.path), name=artifact.path.name),
                ]
            )
        except Exception as error:
            yield event.plain_result(self._user_error("下载或生成 PDF 失败", error))

    @jm.command("shard", alias={"分片", "分页"})
    async def jm_shard(
        self, event: AstrMessageEvent, album_id: str, shard_index: int
    ):
        """发送指定 PDF 分片，例如：/jm shard 12345 1。"""
        if not self._download_allowed(event):
            yield event.plain_result("当前配置只允许 AstrBot 管理员执行下载命令。")
            return
        yield event.plain_result(f"正在准备 JM{album_id} 的第 {shard_index} 个分片……")
        try:
            artifact = await self.service.build_album_pdf(
                album_id, shard_index=shard_index
            )
            if not self._file_sendable(artifact.path):
                yield event.plain_result(
                    f"该分片仍有 {human_size(artifact.path.stat().st_size)}，超过发送上限。"
                    "请在插件配置中减小每个分片的页数。"
                )
                return
            yield event.chain_result(
                [
                    Comp.Plain(
                        f"JM{artifact.album_id}《{artifact.title}》\n"
                        f"第 {artifact.start_page}-{artifact.end_page} 页 / 共 {artifact.page_count} 页"
                    ),
                    Comp.File(file=str(artifact.path), name=artifact.path.name),
                ]
            )
        except Exception as error:
            yield event.plain_result(self._user_error("生成 PDF 分片失败", error))

    @jm.command("status", alias={"状态", "缓存"})
    async def jm_status(self, event: AstrMessageEvent):
        """查看插件运行和缓存状态。"""
        status = self.service.status()
        yield event.plain_result(
            "JMComic 插件运行正常\n"
            f"客户端：{status['client_impl']}\n"
            f"漫画缓存：{status['album_folders']} 个\n"
            f"PDF 缓存：{status['pdf_files']} 个 / {human_size(status['pdf_bytes'])}\n"
            f"每日自动清理：{'已启用（服务器时间 04:00）' if self._cleanup_task else '未启用'}\n"
            f"数据目录：{status['data_dir']}"
        )

    async def terminate(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
        logger.info("JMComic 插件已停止")

    async def _daily_cleanup_loop(self) -> None:
        while True:
            now = datetime.now()
            next_run = now.replace(
                hour=_DAILY_CLEANUP_HOUR,
                minute=0,
                second=0,
                microsecond=0,
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            logger.info("JMComic 下次自动清理缓存时间：%s", next_run.isoformat())
            await asyncio.sleep((next_run - now).total_seconds())
            try:
                result = await self.service.clear_cache()
                logger.info(
                    "JMComic 每日缓存清理完成：删除 %s 个文件，释放 %s",
                    result["files"],
                    human_size(result["bytes"]),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("JMComic 每日缓存清理失败")

    def _download_allowed(self, event: AstrMessageEvent) -> bool:
        if not bool(self.config.get("admin_only_download", False)):
            return True
        return str(getattr(event, "role", "member")).lower() == "admin"

    def _file_sendable(self, path: Path) -> bool:
        max_size_mb = max(1, int(self.config.get("max_send_file_mb", 100)))
        return path.stat().st_size <= max_size_mb * 1024 * 1024

    async def _detail_result(
        self,
        event: AstrMessageEvent,
        detail: dict[str, Any],
        *,
        prefix: str = "",
    ) -> Any:
        detail_text = f"{prefix}{self._format_detail(detail)}"
        if not bool(self.config.get("show_cover", True)):
            return event.plain_result(detail_text)
        try:
            cover_path = await self.service.get_cover(detail["id"])
        except Exception as error:
            logger.warning("JM%s 封面获取失败，仅发送文字详情：%s", detail["id"], error)
            return event.plain_result(detail_text)
        return event.chain_result(
            [
                Comp.Image.fromFileSystem(str(cover_path)),
                Comp.Plain(detail_text),
            ]
        )

    @staticmethod
    def _format_detail(detail: dict[str, Any]) -> str:
        tags = "、".join(detail["tags"]) or "无"
        author = detail["author"] or "未知"
        pages = detail["page_count"] or "未知"
        return (
            f"JM{detail['id']}\n"
            f"标题：{detail['title']}\n"
            f"作者：{author}\n"
            f"页数：{pages}\n"
            f"标签：{tags}"
        )

    @staticmethod
    def _user_error(prefix: str, error: Exception) -> str:
        if isinstance(error, asyncio.TimeoutError):
            detail = "操作超时，请稍后重试或调大超时配置"
        elif isinstance(error, (ValueError, LookupError, JmcomicException)):
            detail = str(error)
        else:
            logger.exception("JMComic 插件执行失败：%s", error)
            detail = "内部错误，详情请查看 AstrBot 日志"
        return f"{prefix}：{detail}"
