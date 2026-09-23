from __future__ import annotations

import asyncio
import contextlib
import json
import math
import os
import random
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jmcomic import JmMagicConstants, JmModuleConfig, create_option_by_file, download_album
from jmcomic.jm_exception import (
    PartialDownloadFailedException,
    RequestRetryAllFailException,
)

from .helpers import clean_album_id, sanitize_filename
from .pdf_builder import build_pdf, cache_is_valid, list_image_paths


@dataclass(frozen=True)
class ServiceConfig:
    timeout_seconds: int = 600
    metadata_timeout_seconds: int = 45
    max_concurrent_downloads: int = 2
    retry_attempts: int = 3
    image_threads: int = 20
    photo_threads: int = 2
    jpeg_quality: int = 70
    encrypt_pdf: bool = False
    shard_pages: int = 250
    client_impl: str = "api"
    proxy: str = ""
    username: str = ""
    password: str = ""

    @classmethod
    def from_mapping(cls, config: dict[str, Any]) -> "ServiceConfig":
        quality = int(config.get("jpeg_quality", 70))
        return cls(
            timeout_seconds=max(30, int(config.get("timeout_seconds", 600))),
            metadata_timeout_seconds=max(
                5, int(config.get("metadata_timeout_seconds", 45))
            ),
            max_concurrent_downloads=max(
                1, int(config.get("max_concurrent_downloads", 2))
            ),
            retry_attempts=max(1, int(config.get("retry_attempts", 3))),
            image_threads=max(1, min(50, int(config.get("image_threads", 20)))),
            photo_threads=max(1, min(16, int(config.get("photo_threads", 2)))),
            jpeg_quality=max(0, min(95, quality)),
            encrypt_pdf=bool(config.get("encrypt_pdf", False)),
            shard_pages=max(1, int(config.get("shard_pages", 250))),
            client_impl=str(config.get("client_impl", "api") or "api"),
            proxy=str(config.get("proxy", "") or "").strip(),
            username=str(config.get("username", "") or "").strip(),
            password=str(config.get("password", "") or ""),
        )


@dataclass(frozen=True)
class PdfArtifact:
    path: Path
    album_id: str
    title: str
    page_count: int
    start_page: int
    end_page: int
    shard_index: int | None = None


class JMComicService:
    """Thread-safe async adapter around the synchronous jmcomic package."""

    def __init__(self, data_dir: Path, config: ServiceConfig) -> None:
        self.data_dir = data_dir.resolve()
        self.download_dir = self.data_dir / "downloads"
        self.cover_dir = self.data_dir / "covers"
        self.pdf_dir = self.data_dir / "pdf"
        self.option_path = self.data_dir / "option.generated.yml"
        self.config = config
        self.option: Any | None = None
        self.client: Any | None = None
        self._client_lock = asyncio.Lock()
        self._download_slots = asyncio.Semaphore(config.max_concurrent_downloads)
        self._album_locks: dict[str, asyncio.Lock] = {}
        self._album_locks_guard = asyncio.Lock()
        self.started_at = time.time()

    async def initialize(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cover_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._load_runtime)

    def _load_runtime(self) -> None:
        JmModuleConfig.AFIELD_ADVICE["jmbook"] = (
            lambda album: f"[{album.id}]{album.title}"
        )
        self._write_option_file()
        self.option = create_option_by_file(str(self.option_path))

    def _write_option_file(self) -> None:
        proxy_value = json.dumps(self.config.proxy) if self.config.proxy else "null"
        login_block = ""
        if self.config.username and self.config.password:
            login_block = (
                "plugins:\n"
                "  after_init:\n"
                "    - plugin: login\n"
                "      kwargs:\n"
                f"        username: {json.dumps(self.config.username)}\n"
                f"        password: {json.dumps(self.config.password)}\n"
            )
        content = (
            "log: false\n"
            "dir_rule:\n"
            f"  base_dir: {json.dumps(str(self.download_dir))}\n"
            "  rule: Bd_Ajmbook\n"
            "download:\n"
            "  cache: true\n"
            "  image:\n"
            "    decode: true\n"
            "    suffix: .jpg\n"
            "  threading:\n"
            f"    image: {self.config.image_threads}\n"
            f"    photo: {self.config.photo_threads}\n"
            "client:\n"
            f"  impl: {json.dumps(self.config.client_impl)}\n"
            "  retry_times: 5\n"
            "  postman:\n"
            "    meta_data:\n"
            f"      proxies: {proxy_value}\n"
            f"{login_block}"
        )
        temporary_path = self.option_path.with_suffix(".tmp")
        temporary_path.write_text(content, encoding="utf-8")
        os.replace(temporary_path, self.option_path)

    async def _get_album_lock(self, album_id: str) -> asyncio.Lock:
        async with self._album_locks_guard:
            return self._album_locks.setdefault(album_id, asyncio.Lock())

    def _require_option(self) -> Any:
        if self.option is None:
            raise RuntimeError("JMComic 服务尚未初始化")
        return self.option

    async def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        async with self._client_lock:
            if self.client is None:
                option = self._require_option()
                self.client = await asyncio.wait_for(
                    asyncio.to_thread(option.new_jm_client),
                    timeout=self.config.metadata_timeout_seconds,
                )
        return self.client

    async def search(self, keyword: str, page: int = 1) -> tuple[list[dict[str, str]], int, int]:
        client = await self._get_client()
        result = await asyncio.wait_for(
            asyncio.to_thread(client.search_site, search_query=keyword, page=page),
            timeout=self.config.metadata_timeout_seconds,
        )
        items = [{"id": str(album_id), "title": str(title)} for album_id, title in result]
        return items, int(getattr(result, "page_count", page) or page), int(
            getattr(result, "total", len(items)) or len(items)
        )

    async def detail(self, raw_album_id: str) -> dict[str, Any]:
        album_id = clean_album_id(raw_album_id)
        client = await self._get_client()
        album = await asyncio.wait_for(
            asyncio.to_thread(client.get_album_detail, album_id),
            timeout=self.config.metadata_timeout_seconds,
        )
        if album is None:
            raise LookupError(f"没有找到 JM{album_id}")
        return {
            "id": str(album.id),
            "title": str(album.title),
            "tags": [str(tag) for tag in (getattr(album, "tags", None) or [])],
            "author": str(getattr(album, "author", "") or ""),
            "page_count": int(getattr(album, "page_count", 0) or 0),
        }

    async def get_cover(self, raw_album_id: str) -> Path:
        """Download and cache an album cover atomically."""
        album_id = clean_album_id(raw_album_id)
        cover_path = self.cover_dir / f"{album_id}.jpg"
        if cover_path.is_file() and cover_path.stat().st_size > 0:
            return cover_path

        lock = await self._get_album_lock(album_id)
        async with lock:
            async with self._download_slots:
                if cover_path.is_file() and cover_path.stat().st_size > 0:
                    return cover_path

                self.cover_dir.mkdir(parents=True, exist_ok=True)
                temporary_path = self.cover_dir / f".{album_id}.tmp.jpg"
                with contextlib.suppress(FileNotFoundError):
                    temporary_path.unlink()
                client = await self._get_client()
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            client.download_album_cover,
                            album_id,
                            str(temporary_path),
                        ),
                        timeout=self.config.metadata_timeout_seconds,
                    )
                    if (
                        not temporary_path.is_file()
                        or temporary_path.stat().st_size == 0
                    ):
                        raise RuntimeError(f"JM{album_id} 封面下载结果为空")
                    os.replace(temporary_path, cover_path)
                finally:
                    with contextlib.suppress(FileNotFoundError):
                        temporary_path.unlink()
                return cover_path

    async def random_detail(self) -> dict[str, Any]:
        """Pick one album from a random catalogue page and return its details."""
        first_items, page_count, _ = await self.categories(
            page=1,
            category="all",
            time_range="all",
            order_by="latest",
        )
        if not first_items:
            raise LookupError("当前没有可随机选择的漫画")

        random_page = random.randint(1, max(1, page_count))
        items = first_items
        if random_page != 1:
            page_items, _, _ = await self.categories(
                page=random_page,
                category="all",
                time_range="all",
                order_by="latest",
            )
            if page_items:
                items = page_items

        selected = random.choice(items)
        return await self.detail(selected["id"])

    async def categories(
        self,
        *,
        page: int,
        category: str,
        time_range: str,
        order_by: str,
    ) -> tuple[list[dict[str, str]], int, int]:
        client = await self._get_client()
        time_value = {
            "today": JmMagicConstants.TIME_TODAY,
            "week": JmMagicConstants.TIME_WEEK,
            "month": JmMagicConstants.TIME_MONTH,
            "all": JmMagicConstants.TIME_ALL,
            "t": JmMagicConstants.TIME_TODAY,
            "w": JmMagicConstants.TIME_WEEK,
            "m": JmMagicConstants.TIME_MONTH,
            "a": JmMagicConstants.TIME_ALL,
        }[time_range]
        category_value = {
            "all": JmMagicConstants.CATEGORY_ALL,
            "doujin": JmMagicConstants.CATEGORY_DOUJIN,
            "single": JmMagicConstants.CATEGORY_SINGLE,
            "short": JmMagicConstants.CATEGORY_SHORT,
            "another": JmMagicConstants.CATEGORY_ANOTHER,
            "hanman": JmMagicConstants.CATEGORY_HANMAN,
            "meiman": JmMagicConstants.CATEGORY_MEIMAN,
            "doujin_cosplay": JmMagicConstants.CATEGORY_DOUJIN_COSPLAY,
            "cosplay": JmMagicConstants.CATEGORY_DOUJIN_COSPLAY,
            "3d": JmMagicConstants.CATEGORY_3D,
            "english_site": JmMagicConstants.CATEGORY_ENGLISH_SITE,
        }[category]
        order_value = {
            "latest": JmMagicConstants.ORDER_BY_LATEST,
            "view": JmMagicConstants.ORDER_BY_VIEW,
            "picture": JmMagicConstants.ORDER_BY_PICTURE,
            "like": JmMagicConstants.ORDER_BY_LIKE,
            "month_rank": JmMagicConstants.ORDER_MONTH_RANKING,
            "week_rank": JmMagicConstants.ORDER_WEEK_RANKING,
            "day_rank": JmMagicConstants.ORDER_DAY_RANKING,
        }[order_by]
        result = await asyncio.wait_for(
            asyncio.to_thread(
                client.categories_filter,
                page=page,
                category=category_value,
                time=time_value,
                order_by=order_value,
            ),
            timeout=self.config.metadata_timeout_seconds,
        )
        items = [{"id": str(album_id), "title": str(title)} for album_id, title in result]
        return items, int(getattr(result, "page_count", page) or page), int(
            getattr(result, "total", len(items)) or len(items)
        )

    async def build_album_pdf(
        self,
        raw_album_id: str,
        *,
        shard_index: int | None = None,
    ) -> PdfArtifact:
        album_id = clean_album_id(raw_album_id)
        lock = await self._get_album_lock(album_id)
        async with lock:
            async with self._download_slots:
                title, image_paths = await self._ensure_album(album_id)
                total_pages = len(image_paths)
                selected_paths = image_paths
                start_page = 1
                end_page = total_pages
                if shard_index is not None:
                    if shard_index < 1:
                        raise ValueError("分片序号必须大于或等于 1")
                    shard_count = math.ceil(total_pages / self.config.shard_pages)
                    if shard_index > shard_count:
                        raise ValueError(f"分片序号超出范围，可用范围为 1-{shard_count}")
                    start_page = (shard_index - 1) * self.config.shard_pages + 1
                    end_page = min(shard_index * self.config.shard_pages, total_pages)
                    selected_paths = image_paths[start_page - 1 : end_page]

                quality = self.config.jpeg_quality or None
                quality_suffix = f".q{quality}" if quality else ""
                encrypted_suffix = ".enc" if self.config.encrypt_pdf else ""
                safe_title = sanitize_filename(title, fallback=album_id)
                if shard_index is None:
                    filename = f"[{album_id}] {safe_title}{quality_suffix}{encrypted_suffix}.pdf"
                else:
                    filename = (
                        f"[{album_id}] {safe_title}.part{start_page}-{end_page}"
                        f"{quality_suffix}{encrypted_suffix}.pdf"
                    )
                output_path = self.pdf_dir / filename
                password = album_id if self.config.encrypt_pdf else None
                if not cache_is_valid(
                    output_path,
                    password=password,
                    expected_pages=len(selected_paths),
                ):
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            build_pdf,
                            selected_paths,
                            output_path,
                            password=password,
                            jpeg_quality=quality,
                        ),
                        timeout=self.config.timeout_seconds,
                    )
                return PdfArtifact(
                    path=output_path,
                    album_id=album_id,
                    title=title,
                    page_count=total_pages,
                    start_page=start_page,
                    end_page=end_page,
                    shard_index=shard_index,
                )

    async def _ensure_album(self, album_id: str) -> tuple[str, list[Path]]:
        cached = self._find_cached_album(album_id)
        if cached is not None:
            title, folder = cached
            paths = list_image_paths(folder)
            if paths and (folder / ".done").exists():
                return title, paths

        option = self._require_option()
        album = await self._download_with_retry(album_id, option)
        title = str(album.name)
        folder = self.download_dir / f"[{album_id}]{title}"
        paths = list_image_paths(folder)
        expected = int(getattr(album, "page_count", 0) or len(paths))
        if not paths or len(paths) < expected:
            raise RuntimeError(f"下载不完整：期望 {expected} 页，实际获得 {len(paths)} 页")
        with contextlib.suppress(OSError):
            (folder / ".done").touch()
        return title, paths

    async def _download_with_retry(self, album_id: str, option: Any) -> Any:
        retryable = (PartialDownloadFailedException, RequestRetryAllFailException)
        last_error: BaseException | None = None
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(download_album, album_id, option=option),
                    timeout=self.config.timeout_seconds,
                )
                album, _ = result
                return album
            except retryable as error:
                last_error = error
                if attempt >= self.config.retry_attempts:
                    raise
                await asyncio.sleep(min(2 ** (attempt - 1), 15))
        assert last_error is not None
        raise last_error

    def _find_cached_album(self, album_id: str) -> tuple[str, Path] | None:
        matches = sorted(self.download_dir.iterdir())
        for folder in matches:
            if not folder.is_dir() or not folder.name.startswith(f"[{album_id}]"):
                continue
            title = folder.name[len(album_id) + 2 :].strip()
            return title, folder
        return None

    async def clear_cache(self) -> dict[str, int]:
        """Clear image and PDF caches after all active build jobs finish."""
        acquired_slots = 0
        try:
            for _ in range(self.config.max_concurrent_downloads):
                await self._download_slots.acquire()
                acquired_slots += 1
            return await asyncio.to_thread(self._clear_cache_sync)
        finally:
            for _ in range(acquired_slots):
                self._download_slots.release()

    def _clear_cache_sync(self) -> dict[str, int]:
        deleted_files = 0
        deleted_bytes = 0
        data_dir = self.data_dir.resolve()
        for target in (self.download_dir, self.cover_dir, self.pdf_dir):
            resolved_target = target.resolve()
            if (
                resolved_target.parent != data_dir
                or resolved_target.name not in {"downloads", "covers", "pdf"}
            ):
                raise RuntimeError(f"拒绝清理非插件缓存目录：{resolved_target}")
            target.mkdir(parents=True, exist_ok=True)
            for path in target.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    deleted_files += 1
                    with contextlib.suppress(OSError):
                        deleted_bytes += path.stat().st_size
            for path in target.iterdir():
                if path.is_symlink() or path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    shutil.rmtree(path)
        return {"files": deleted_files, "bytes": deleted_bytes}

    def status(self) -> dict[str, Any]:
        album_folders = sum(1 for path in self.download_dir.iterdir() if path.is_dir())
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        pdf_bytes = sum(path.stat().st_size for path in pdf_files if path.is_file())
        return {
            "album_folders": album_folders,
            "pdf_files": len(pdf_files),
            "pdf_bytes": pdf_bytes,
            "data_dir": str(self.data_dir),
            "client_impl": self.config.client_impl,
            "uptime_seconds": int(time.time() - self.started_at),
        }
