from __future__ import annotations

import re
import random
from typing import Any

from backend.core.config import GlobalConfig
from backend.core.http_session import save_cookies
from backend.core.jm_store import get_user_id, set_user_id, set_user_profile, get_user_profile
from backend.core.req import (
    AddAndDelFavoritesReq2,
    GetBookInfoReq2,
    GetCategoryReq2,
    GetCommentReq2,
    GetDailyReq2,
    GetIndexInfoReq2,
    GetLatestInfoReq2,
    GetSearchCategoryReq2,
    GetSearchReq2,
    LikeCommentReq2,
    LoginReq2,
    SendCommentReq2,
    SignDailyReq2,
)
from backend.core.api_adapter import adapt_album_detail, adapt_search_result
from backend.jm_service import jm_service
from backend.models.schemas import ChapterDetail, ChapterPage, ComicDetail, ComicSummary, UserProfile
from backend.providers.base import ComicProvider, ProviderError


class JmProvider(ComicProvider):
    source = "jm"

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = LoginReq2(username, password).execute()
        save_cookies()
        jm_service.update_config(username, password)
        if isinstance(data, dict):
            set_user_profile(data)
            for k in ("uid", "user_id", "id"):
                v = data.get(k)
                if v:
                    set_user_id(str(v))
                    break
        return data if isinstance(data, dict) else {"raw": data}

    def register(self, username: str, password: str, **kwargs: Any) -> dict[str, Any]:
        raise ProviderError("JM register not supported in app API", status=400)

    def profile(self) -> UserProfile:
        cfg = jm_service.get_config()
        raw = get_user_profile()
        return UserProfile(
            source="jm",
            username=cfg.get("username") if isinstance(cfg, dict) else "",
            nickname=(raw or {}).get("username") if isinstance(raw, dict) else None,
            raw=raw,
        )

    def check_in(self) -> dict[str, Any]:
        uid = get_user_id()
        if not uid:
            raise ProviderError("Missing user_id, please login again", status=400)
        daily = GetDailyReq2(uid).execute()
        daily_id = None
        if isinstance(daily, dict):
            for key in ("daily_id", "id"):
                if daily.get(key):
                    daily_id = str(daily[key])
                    break
            if not daily_id:
                for key in ("list", "daily_list", "data"):
                    v = daily.get(key)
                    if isinstance(v, list) and v:
                        item = v[0]
                        if isinstance(item, dict):
                            daily_id = str(item.get("daily_id") or item.get("id") or "")
                            if daily_id:
                                break
        if not daily_id:
            raise ProviderError("Unable to get daily_id", status=400)
        res = SignDailyReq2(uid, daily_id).execute()
        return res if isinstance(res, dict) else {"raw": res}

    def search(self, q: str, page: int = 1, **kwargs: Any) -> list[ComicSummary]:
        raw = GetSearchReq2(q, page=page).execute()
        items = adapt_search_result(raw)
        out: list[ComicSummary] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            aid = str(it.get("album_id") or "")
            if not aid:
                continue
            out.append(
                ComicSummary(
                    source="jm",
                    comic_id=aid,
                    title=str(it.get("title") or ""),
                    author=it.get("author"),
                    cover_url=it.get("image"),
                    category=it.get("category"),
                    raw=it,
                )
            )
        return out

    def categories(self) -> list[dict[str, Any]]:
        raw = GetCategoryReq2().execute()
        if isinstance(raw, dict):
            return raw.get("categories") or raw.get("data") or []
        return []

    def leaderboard(self, **kwargs: Any) -> list[ComicSummary]:
        category = kwargs.get("category") or "0"
        page = int(kwargs.get("page") or 1)
        sort = kwargs.get("sort") or "tf"
        tag = kwargs.get("tag")
        raw = GetSearchCategoryReq2(category=category, page=page, sort=sort, tag=tag).execute()
        items = adapt_search_result(raw)
        out: list[ComicSummary] = []
        for it in items or []:
            if isinstance(it, dict) and it.get("album_id"):
                out.append(ComicSummary(
                    source="jm", 
                    comic_id=str(it["album_id"]), 
                    title=str(it.get("title") or ""), 
                    author=it.get("author"), 
                    cover_url=it.get("image"),
                    tags=it.get("tags") or [],
                    category=it.get("category"),
                    raw=it
                ))
        return out

    def random(self, **kwargs: Any) -> ComicSummary | None:
        base = GlobalConfig.GetImgUrl()
        def cover_url(aid: str) -> str:
            return f"{base}/media/albums/{aid}.jpg" if isinstance(base, str) and base else ""

        def get_cat_id(c: Any) -> str:
            if not c:
                return "0"
            if isinstance(c, (str, int)):
                return str(c)
            if isinstance(c, dict):
                slug = c.get("slug") or c.get("SLUG") or ""
                if slug:
                    return str(slug)
                v = c.get("CID") or c.get("id") or c.get("category_id") or c.get("cid") or "0"
                return str(v or "0")
            return "0"

        try:
            max_page = int(kwargs.get("max_page") or 50)
        except Exception:
            max_page = 50
        try:
            tries = int(kwargs.get("tries") or 8)
        except Exception:
            tries = 8

        max_page = max(1, min(200, max_page))
        tries = max(1, min(20, tries))

        try:
            cats_raw = self.categories() or []
            cat_ids = [get_cat_id(x) for x in cats_raw]
            cat_ids = [c for c in cat_ids if c and c != "None"]
            cat_ids = ["0"] + cat_ids
            cat_ids = list(dict.fromkeys(cat_ids))
        except Exception:
            cat_ids = ["0"]

        sorts = ["mr", "tf", "mv", "mp"]
        for _ in range(tries):
            try:
                category = random.choice(cat_ids)
                sort = random.choice(sorts)
                page = random.randint(1, max_page)
                items = self.leaderboard(category=category, page=page, sort=sort)
                if items:
                    return random.choice(items)
            except Exception:
                continue

        raw = GetLatestInfoReq2("0").execute()
        if isinstance(raw, list) and raw:
            it = random.choice(raw)
            if isinstance(it, dict) and it.get("id"):
                aid = str(it.get("id") or "").strip()
                title = str(it.get("name") or "")
                author = str(it.get("author") or "")
                img = str(it.get("image") or "").strip() or cover_url(aid)
                if aid:
                    return ComicSummary(source="jm", comic_id=aid, title=title, author=author, cover_url=img, raw=it)
        items = adapt_search_result(raw)
        if not items:
            return None
        it2 = random.choice(items)
        if isinstance(it2, dict) and it2.get("album_id"):
            aid2 = str(it2.get("album_id") or "").strip()
            return ComicSummary(source="jm", comic_id=aid2, title=str(it2.get("title") or ""), author=it2.get("author"), cover_url=str(it2.get("image") or "").strip() or cover_url(aid2), raw=it2)
        return None

    def also_viewed(self, comic_id: str, **kwargs: Any) -> list[ComicSummary]:
        def cover_url(aid: str) -> str:
            base = GlobalConfig.GetImgUrl()
            return f"{base}/media/albums/{aid}.jpg" if isinstance(base, str) and base else ""

        cur = str(comic_id or "").strip()
        if not cur:
            return []

        try:
            limit = int(kwargs.get("limit") or 24)
        except Exception:
            limit = 24
        limit = max(1, min(48, limit))

        seed = kwargs.get("seed")
        try:
            seed_value = int(seed) if seed is not None and str(seed).strip() else random.randrange(1, 2**31)
        except Exception:
            seed_value = random.randrange(1, 2**31)
        rng = random.Random(seed_value)

        def as_text(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, (str, int, float)):
                return str(value).strip()
            if isinstance(value, dict):
                for key in ("title", "name", "alias", "slug", "id", "CID", "category_id", "tag"):
                    text = as_text(value.get(key))
                    if text:
                        return text
                return ""
            return ""

        def flatten_texts(value: Any) -> list[str]:
            out: list[str] = []
            if value is None:
                return out
            if isinstance(value, list):
                for item in value:
                    out.extend(flatten_texts(item))
                return out
            text = as_text(value)
            if text:
                out.append(text)
            return out

        def unique_texts(values: list[str]) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            for value in values:
                text = re.sub(r"\s+", " ", str(value or "")).strip()
                if not text:
                    continue
                key = text.casefold()
                if key in seen:
                    continue
                seen.add(key)
                out.append(text)
            return out

        def title_tokens(title: str) -> list[str]:
            text = re.sub(r"<[^>]+>", " ", str(title or ""))
            parts = re.split(r"[\[\]【】（）(){}<>《》,，。.!！?？:：;；/\\|+_~、\s]+", text)
            tokens: list[str] = []
            for part in parts:
                s = part.strip()
                if len(s) < 2:
                    continue
                if s.isdigit():
                    continue
                tokens.append(s)
            return unique_texts(tokens)

        def category_id(value: Any) -> str:
            if not value:
                return ""
            if isinstance(value, (str, int)):
                return str(value).strip()
            if isinstance(value, dict):
                for key in ("slug", "SLUG", "CID", "id", "category_id", "cid"):
                    text = str(value.get(key) or "").strip()
                    if text:
                        return text
            return ""

        raw_detail: Any = {}
        detail: dict[str, Any] = {}
        try:
            raw_detail = GetBookInfoReq2(cur).execute()
            detail = adapt_album_detail(raw_detail) or {}
        except Exception:
            raw_detail = {}
            detail = {}

        title = str(detail.get("title") or as_text(raw_detail.get("name") if isinstance(raw_detail, dict) else "") or "")
        author_values = unique_texts(
            flatten_texts(detail.get("author"))
            + (flatten_texts(raw_detail.get("author")) if isinstance(raw_detail, dict) else [])
            + (flatten_texts(raw_detail.get("author_list")) if isinstance(raw_detail, dict) else [])
        )
        tag_values: list[str] = []
        category_values: list[str] = []
        category_ids: list[str] = []
        if isinstance(raw_detail, dict):
            for key in ("tags", "tag", "tag_list", "tags_list"):
                tag_values.extend(flatten_texts(raw_detail.get(key)))
            for key in ("category", "categories", "category_list"):
                value = raw_detail.get(key)
                category_values.extend(flatten_texts(value))
                if isinstance(value, list):
                    category_ids.extend([category_id(item) for item in value])
                else:
                    category_ids.append(category_id(value))
        tag_values = unique_texts(tag_values)
        category_values = unique_texts(category_values)
        category_ids = [x for x in unique_texts(category_ids) if x and x != "0"]
        tokens = title_tokens(title)

        candidates: dict[str, tuple[int, float, ComicSummary]] = {}

        def add_candidate(item: Any, score: int) -> None:
            if not isinstance(item, dict):
                return
            aid = str(item.get("album_id") or item.get("id") or "").strip()
            if not aid or aid == cur:
                return
            item_title = str(item.get("title") or item.get("name") or "")
            item_author = as_text(item.get("author"))
            item_category = as_text(item.get("category"))
            final_score = score
            if item_author and any(item_author.casefold() == a.casefold() for a in author_values):
                final_score += 80
            title_low = item_title.casefold()
            final_score += sum(12 for token in tokens[:8] if token.casefold() in title_low)
            if item_category and any(item_category.casefold() == c.casefold() for c in category_values):
                final_score += 18

            summary = ComicSummary(
                source="jm",
                comic_id=aid,
                title=item_title,
                author=item.get("author"),
                cover_url=str(item.get("image") or "").strip() or cover_url(aid),
                category=item_category or None,
                raw=item,
            )
            prev = candidates.get(aid)
            jitter = rng.random()
            if not prev or final_score > prev[0]:
                candidates[aid] = (final_score, jitter, summary)

        def add_search(query: str, score: int, pages: list[int], sort: str = "mr") -> None:
            q = str(query or "").strip()
            if len(q) < 2:
                return
            for page in pages:
                try:
                    raw = GetSearchReq2(q, sort=sort, page=max(1, int(page))).execute()
                    for it in adapt_search_result(raw) or []:
                        add_candidate(it, score)
                except Exception:
                    continue

        def add_category(category: str, score: int, tag: str | None = None) -> None:
            cat = str(category or "0").strip() or "0"
            pages = unique_texts(["1", str(rng.randint(1, 4)), str(rng.randint(1, 8))])
            sorts = ["mr", "tf", "mv", "mp"]
            rng.shuffle(sorts)
            for page in pages:
                try:
                    raw = GetSearchCategoryReq2(category=cat, page=int(page), sort=sorts[0], tag=tag).execute()
                    for it in adapt_search_result(raw) or []:
                        add_candidate(it, score)
                except Exception:
                    continue

        query_plan: list[tuple[str, str, int]] = []
        for author in author_values[:3]:
            query_plan.append(("author", author, 120))
        if title:
            query_plan.append(("title", title, 95))
        for token in tokens[:6]:
            query_plan.append(("token", token, 70))
        for tag in tag_values[:5]:
            query_plan.append(("tag", tag, 55))
        rng.shuffle(query_plan)

        for kind, query, base_score in query_plan[:10]:
            pages = [1]
            if kind in ("author", "tag", "token"):
                pages.append(rng.randint(1, 5))
            add_search(query, base_score, pages, sort=rng.choice(["mr", "tf", "mv"]))
            if len(candidates) >= limit * 3:
                break

        for tag in tag_values[:3]:
            add_category("0", 45, tag=tag)
            if len(candidates) >= limit * 3:
                break

        for cat_id in category_ids[:2]:
            add_category(cat_id, 35)

        if len(candidates) < limit:
            try:
                raw2 = GetLatestInfoReq2(str(rng.randint(0, 4))).execute()
                if isinstance(raw2, list):
                    for it in raw2:
                        if not isinstance(it, dict):
                            continue
                        mapped = {
                            "album_id": str(it.get("id") or "").strip(),
                            "title": str(it.get("name") or ""),
                            "author": str(it.get("author") or ""),
                            "image": str(it.get("image") or "").strip(),
                        }
                        add_candidate(mapped, 5)
                else:
                    for it in adapt_search_result(raw2) or []:
                        add_candidate(it, 5)
            except Exception:
                pass

        if len(candidates) < limit:
            try:
                raw = GetIndexInfoReq2(str(rng.randint(0, 2))).execute()
                if isinstance(raw, list):
                    for sec in raw:
                        if not isinstance(sec, dict):
                            continue
                        content = sec.get("content") or []
                        if not isinstance(content, list):
                            continue
                        for it in content:
                            if not isinstance(it, dict):
                                continue
                            mapped = {
                                "album_id": str(it.get("id") or "").strip(),
                                "title": str(it.get("name") or ""),
                                "author": str(it.get("author") or ""),
                                "image": str(it.get("image") or "").strip(),
                            }
                            add_candidate(mapped, 1)
            except Exception:
                pass

        ranked = sorted(candidates.values(), key=lambda x: (x[0], x[1]), reverse=True)
        return [item for _, _, item in ranked[:limit]]

    def comic_detail(self, comic_id: str) -> ComicDetail:
        raw = GetBookInfoReq2(comic_id).execute()
        d = adapt_album_detail(raw) or {}
        eps = d.get("episode_list") or []
        chapters = []
        for idx, ep in enumerate(eps):
            if isinstance(ep, dict) and ep.get("id"):
                chapters.append({"id": str(ep["id"]), "title": str(ep.get("title") or ""), "order": idx})
        return ComicDetail(
            source="jm",
            comic_id=str(d.get("album_id") or comic_id),
            title=str(d.get("title") or ""),
            author=d.get("author"),
            cover_url=d.get("image"),
            description=d.get("description"),
            tags=list(d.get("tags") or []),
            category=d.get("category"),
            chapters=chapters,
            raw=d,
        )

    def chapter_detail(self, chapter_id: str, **kwargs: Any) -> ChapterDetail:
        data = jm_service.get_chapter_detail(chapter_id)
        imgs = []
        for x in (data.get("images") or []):
            s = str(x or "")
            if s:
                imgs.append(ChapterPage(name=s))
        return ChapterDetail(source="jm", chapter_id=str(chapter_id), title=data.get("title"), images=imgs, raw=data)

    def comments(self, comic_id: str, page: int = 1, **kwargs: Any) -> dict[str, Any]:
        return GetCommentReq2(comic_id, page=page).execute()

    def send_comment(self, comic_id: str, content: str, reply_to: str | None = None, **kwargs: Any) -> dict[str, Any]:
        return SendCommentReq2(comic_id, content, comment_id=reply_to or "").execute()

    def like_comment(self, comment_id: str, **kwargs: Any) -> dict[str, Any]:
        return LikeCommentReq2(comment_id).execute()

    def toggle_favorite(self, comic_id: str, **kwargs: Any) -> dict[str, Any]:
        return AddAndDelFavoritesReq2(comic_id).execute()

    def like_comic(self, comic_id: str, **kwargs: Any) -> dict[str, Any]:
        raise ProviderError("JM comic like not supported in current API", status=400)
