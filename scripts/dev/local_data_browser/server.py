#!/usr/bin/env python3
"""local DB 読み取り専用データ可視化（サンプル）。

- bind: 127.0.0.1 のみ
- 接続: loopback の DATABASE_URL のみ
- SQL: SELECT / WITH のみ
- embedding ベクトル本体・DATABASE_URL 実値は出さない
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import traceback
import uuid
from datetime import datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from guard import (  # noqa: E402
    assert_app_env_allows_local_browser,
    assert_local_bind_host,
    assert_local_database_url,
    sql_is_read_only,
)
import genre_select  # noqa: E402
import ranking  # noqa: E402

JST = ZoneInfo("Asia/Tokyo")
FEATURE_AXES = (
    ("formality", "儀礼性", "Social"),
    ("safety", "安全性", "Social"),
    ("brand_appropriateness", "ブランド適切性", "Social"),
    ("emotion", "感情性", "Symbolic"),
    ("novelty", "新規性", "Symbolic"),
    ("intimacy", "親密性", "Symbolic"),
    ("symbolic_identity", "象徴性", "Symbolic"),
    ("story_richness", "ストーリー性", "Symbolic"),
)
PAGE_SIZE = 24

CSS = """
:root {
  --bg: #f4efe6;
  --ink: #1c2430;
  --muted: #5c6673;
  --card: #fffdf8;
  --line: #e2d6c4;
  --accent: #b5471a;
  --navy: #243044;
  --ok: #2f6f4e;
  --warn: #9a6b12;
  --chip: #efe4d4;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: "Hiragino Sans", "Noto Sans JP", sans-serif;
  background: var(--bg); color: var(--ink); line-height: 1.5;
}
a { color: #8a3b12; }
header.app {
  background: var(--navy); color: #f8f1e6; padding: 14px 24px 10px;
}
header.app h1 { margin: 0 0 4px; font-size: 18px; font-weight: 700; }
header.app p { margin: 0; font-size: 12px; color: #d7cbb8; }
nav {
  display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 24px;
  background: #2d3b52; position: sticky; top: 0; z-index: 2;
}
nav a {
  color: #f3e6d4; text-decoration: none; font-size: 13px;
  padding: 4px 10px; border-radius: 999px; border: 1px solid #4a5a73;
}
nav a.active, nav a:hover { background: #b5471a; border-color: #b5471a; color: #fff; }
main { padding: 20px 24px 88px; max-width: 1280px; }
.banner {
  background: #fff6e5; border: 1px solid #e8c98a; padding: 10px 14px;
  border-radius: 8px; font-size: 13px; margin-bottom: 16px;
}
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px 14px;
}
.card .n { font-size: 26px; font-weight: 700; }
.card .k { font-size: 12px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; background: var(--card); font-size: 13px; }
th, td { border-bottom: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #f3e8d8; font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.item-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
}
.item-card img, .ph {
  width: 100%; height: 150px; object-fit: cover; background: #ece4d6; display: block;
}
.ph { display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 12px; }
.item-card .body { padding: 10px 12px 12px; }
.item-card h3 { margin: 0 0 4px; font-size: 14px; }
.muted { color: var(--muted); font-size: 12px; }
.chip {
  display: inline-block; background: var(--chip); border-radius: 999px;
  padding: 1px 8px; margin: 2px 4px 2px 0; font-size: 11px;
}
.chip.ok { background: #d9eadf; color: var(--ok); }
.chip.off { background: #eee; color: #888; }
form.inline { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; align-items: end; }
label { font-size: 12px; color: var(--muted); display: block; }
input, select {
  padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; font-size: 13px;
}
button, .btn {
  background: var(--accent); color: #fff; border: 0; border-radius: 6px;
  padding: 7px 12px; cursor: pointer; font-size: 13px; text-decoration: none;
}
.pager { margin-top: 16px; display: flex; gap: 10px; align-items: center; }
.barwrap { height: 8px; background: #eee6d8; border-radius: 99px; overflow: hidden; width: 120px; display: inline-block; vertical-align: middle; }
.bar { height: 100%; background: var(--accent); }
.matrix { border-collapse: collapse; font-size: 11px; }
.matrix th, .matrix td { border: 1px solid var(--line); padding: 4px; text-align: center; min-width: 42px; }
.matrix th { background: #243044; color: #f6efe4; }
.matrix td a { text-decoration: none; display: block; padding: 6px 2px; }
.matrix td.on { background: #d9eadf; }
.matrix td.off { background: #f3e0e0; }
.matrix .rowh { text-align: left; background: #f3e8d8; color: var(--ink); min-width: 90px; }
.detail { display: grid; grid-template-columns: 280px 1fr; gap: 20px; }
@media (max-width: 800px) { .detail { grid-template-columns: 1fr; } }
.rel {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 12px 0 20px;
}
.rel .box { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; font-size: 12px; }
.rel .arrow { color: var(--muted); }
.empty { padding: 24px; background: var(--card); border-radius: 10px; color: var(--muted); }
pre.small { white-space: pre-wrap; font-size: 12px; background: #fff; border: 1px solid var(--line); padding: 10px; border-radius: 8px; }
.tabs { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 14px; }
.tabs a, .tabs span {
  display: inline-block; padding: 5px 12px; border-radius: 999px; font-size: 13px;
  border: 1px solid var(--line); background: #fff; text-decoration: none; color: var(--ink);
}
.tabs a.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.banner.ok { background: #e7f4ea; border-color: #b7d7be; }
.banner.warn { background: #fdecea; border-color: #e8b4ad; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
.rank { font-weight: 700; color: var(--accent); }
.thumb-sm { width: 56px; height: 56px; object-fit: cover; border-radius: 6px; background: #ece4d6; }
.crumb { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 0 0 14px; font-size: 13px; }
.crumb a { text-decoration: none; }
.genre-row.picked td { background: #e7f4ea; }
.check { display: inline-flex; padding: 8px; cursor: pointer; }
.sticky-save {
  background: #fffdf8; border: 1px solid var(--line);
  padding: 10px 12px; margin: 0 0 12px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  border-radius: 8px;
}
"""


def h(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value), quote=True)


def money(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"¥{int(value):,}"
    except (TypeError, ValueError):
        return h(value)


def jst(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")
    return h(value)


def num(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return h(value)
    return f"{n:.{digits}f}".rstrip("0").rstrip(".")


def is_uuid(text: str) -> bool:
    try:
        uuid.UUID(str(text))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def bar(value: Any) -> str:
    if value is None:
        return '<span class="muted">なし</span>'
    try:
        pct = max(0, min(100, float(value) * 100))
    except (TypeError, ValueError):
        return h(value)
    return (
        f'<span class="barwrap"><span class="bar" style="width:{pct:.1f}%"></span></span>'
        f" {h(num(value))}"
    )


def chip(ok: bool, on: str, off: str) -> str:
    cls = "ok" if ok else "off"
    return f'<span class="chip {cls}">{h(on if ok else off)}</span>'


class Db:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def fetch(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if not sql_is_read_only(sql):
            raise RuntimeError("read-only SQL 以外は実行しません")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "psycopg がありません。./scripts/dev/setup-python-batch.sh のあと "
                "./scripts/dev/start-local-data-browser.sh で起動してください。"
            ) from exc
        with psycopg.connect(self._dsn, connect_timeout=8) as conn:
            conn.execute("SET default_transaction_read_only = on")
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch(sql, params)
        return rows[0] if rows else None


def layout(title: str, active: str, db_desc: str, body: str) -> str:
    links = [
        ("/", "概況", "home"),
        ("/items", "商品リスト", "items"),
        ("/reco", "レコメンド用商品", "reco"),
        ("/masters", "Relationship / Occasion", "masters"),
        ("/pairs", "組み合わせマトリクス", "pairs"),
        ("/requests", "推薦入力（ユーザー相当）", "requests"),
        ("/ranking", "ランキング分析", "ranking"),
        ("/genres", "ジャンル階層", "genres"),
    ]
    nav = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{label}</a>'
        for href, label, key in links
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{h(title)} · OKURI local data browser</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="app">
    <h1>OKURI local data browser（サンプル）</h1>
    <p>localhost 限定 / SELECT のみ / 接続先 {h(db_desc)} · 本番・stg・Vercel 非公開</p>
  </header>
  <nav>{nav}</nav>
  <main>
    <div class="banner">
      これは管理者向けの <strong>local 確認用サンプル</strong> です。
      <code>apps/web</code> には載せていません。書き込みはできません。
      embedding ベクトル本体と接続文字列は表示しません。
    </div>
    {body}
  </main>
</body>
</html>"""


def metric_cards(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows:
        parts.append(
            f'<div class="card"><div class="k">{h(row.get("k"))}</div>'
            f'<div class="n">{h(row.get("n"))}</div></div>'
        )
    return f'<div class="cards">{"".join(parts)}</div>'


def item_filters_form(action: str, q: str, meaning: str, extra: str = "") -> str:
    return f"""
    <form class="inline" method="get" action="{h(action)}">
      <div><label>検索（商品名 / 外部コード）</label>
        <input name="q" value="{h(q)}" maxlength="80" placeholder="チョコレート など"></div>
      <div><label>意味データ</label>
        <select name="meaning">
          <option value="" {"selected" if meaning == "" else ""}>すべて</option>
          <option value="yes" {"selected" if meaning == "yes" else ""}>meaning あり</option>
          <option value="no" {"selected" if meaning == "no" else ""}>meaning なし</option>
        </select></div>
      {extra}
      <button type="submit">絞り込み</button>
    </form>
    """


def render_item_cards(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">該当する商品がありません。</div>'
    cards = []
    for row in rows:
        img = row.get("primary_image_url")
        thumb = (
            f'<img src="{h(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
            if img
            else '<div class="ph">画像なし</div>'
        )
        cards.append(
            f"""<article class="item-card">
            <a href="/items/{h(row["item_id"])}">{thumb}</a>
            <div class="body">
              <h3><a href="/items/{h(row["item_id"])}">{h(row.get("item_name"))}</a></h3>
              <div>{money(row.get("price"))}</div>
              <div class="muted">{h(row.get("genre_name") or "ジャンルなし")}</div>
              {chip(bool(row.get("is_active")), "active", "inactive")}
              {chip(bool(row.get("has_image")), "画像", "画像なし")}
              {chip(bool(row.get("has_semantic")), "semantic", "semanticなし")}
              {chip(bool(row.get("has_feature8")), "feature8", "feature不足")}
              {chip(bool(row.get("has_meaning")), "meaning", "meaningなし")}
              {chip(bool(row.get("has_embedding")), "embedding", "embeddingなし")}
            </div>
            </article>"""
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def pager(path: str, page: int, total: int, query: dict[str, str]) -> str:
    last = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    def href(p: int) -> str:
        q = dict(query)
        q["page"] = str(p)
        qs = "&".join(f"{k}={html.escape(v, quote=True)}" for k, v in q.items() if v)
        return f"{path}?{qs}" if qs else path
    prev = f'<a class="btn" href="{href(page - 1)}">前へ</a>' if page > 1 else ""
    nxt = f'<a class="btn" href="{href(page + 1)}">次へ</a>' if page < last else ""
    return f'<div class="pager">{prev}<span class="muted">{page} / {last} ページ（{total:,} 件）</span>{nxt}</div>'


ITEM_SELECT = """
SELECT
  i.item_id,
  i.item_name,
  i.price,
  i.is_active,
  i.active_status,
  i.external_item_code,
  i.shop_code,
  g.genre_name,
  i.external_genre_id,
  img.image_url AS primary_image_url,
  EXISTS (SELECT 1 FROM item_image x WHERE x.item_id = i.item_id) AS has_image,
  EXISTS (SELECT 1 FROM item_semantic s WHERE s.item_id = i.item_id) AS has_semantic,
  EXISTS (
    SELECT 1 FROM (
      SELECT item_id FROM item_feature
      WHERE item_id = i.item_id
      GROUP BY item_id, semantic_config_version_id
      HAVING count(DISTINCT feature_code) = 8
    ) f
  ) AS has_feature8,
  EXISTS (SELECT 1 FROM item_meaning m WHERE m.item_id = i.item_id) AS has_meaning,
  EXISTS (SELECT 1 FROM item_embedding e WHERE e.item_id = i.item_id) AS has_embedding
FROM item i
LEFT JOIN external_genre g
  ON g.external_genre_id = i.external_genre_id AND g.source = i.source
LEFT JOIN LATERAL (
  SELECT image_url FROM item_image
  WHERE item_id = i.item_id AND is_primary IS TRUE
  ORDER BY display_order
  LIMIT 1
) img ON true
"""


class Handler(BaseHTTPRequestHandler):
    db: Db
    db_desc: str
    _genre_tree: dict[str, Any] | None = None

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _page(self, title: str, active: str, body: str, code: int = 200) -> None:
        self._send(code, layout(title, active, self.db_desc, body))

    def _qs(self) -> dict[str, str]:
        parsed = urlparse(self.path)
        raw = parse_qs(parsed.query)
        return {k: (v[0] if v else "") for k, v in raw.items()}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/":
                self.page_home()
            elif path == "/items":
                self.page_items()
            elif path.startswith("/items/"):
                self.page_item(path.split("/", 2)[2])
            elif path == "/reco":
                self.page_reco()
            elif path == "/masters":
                self.page_masters()
            elif path == "/pairs":
                self.page_pairs()
            elif path.startswith("/pairs/"):
                self.page_pair(path.split("/", 2)[2])
            elif path == "/requests":
                self.page_requests()
            elif path == "/ranking":
                self.page_ranking()
            elif path == "/genres":
                self.page_genres()
            elif path == "/health":
                self._send(200, json.dumps({"ok": True, "db": self.db_desc}), "application/json")
            else:
                self._page("Not found", "home", "<p>ページが見つかりません。</p>", 404)
        except Exception as exc:  # noqa: BLE001
            err = h(str(exc))
            self._page(
                "エラー",
                "home",
                f"<p>読み取りに失敗しました。</p><pre class='small'>{err}</pre>",
                500,
            )
            traceback.print_exc()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path not in {"/ranking", "/genres"}:
            self._page("Method not allowed", "home", "<p>DB への書き込み操作は受け付けません。</p>", 405)
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        limit = 65536 if path == "/genres" else 8192
        if length < 0 or length > limit:
            self._page("エラー", "home", "<p>リクエストが不正です。</p>", 400)
            return
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        parsed_form = parse_qs(raw)
        form = {k: (v[0] if v else "") for k, v in parsed_form.items()}
        form["_all"] = parsed_form
        try:
            if path == "/genres":
                self.page_genres(form=form)
            else:
                self.page_ranking(form=form)
        except Exception as exc:  # noqa: BLE001
            err = h(str(exc))
            active = "genres" if path == "/genres" else "ranking"
            self._page(
                "エラー",
                active,
                f"<p>処理に失敗しました。</p><pre class='small'>{err}</pre>",
                500,
            )
            traceback.print_exc()

    def page_home(self) -> None:
        counts = self.db.fetch(
            """
            SELECT 'item' AS k, count(*)::bigint AS n FROM item
            UNION ALL SELECT 'item active', count(*) FROM item WHERE is_active IS TRUE
            UNION ALL SELECT '画像なし', count(*) FROM item i
              WHERE NOT EXISTS (SELECT 1 FROM item_image img WHERE img.item_id = i.item_id)
            UNION ALL SELECT 'semantic', count(DISTINCT item_id) FROM item_semantic
            UNION ALL SELECT 'feature 8軸', count(*) FROM (
              SELECT item_id FROM item_feature
              GROUP BY item_id, semantic_config_version_id
              HAVING count(DISTINCT feature_code) = 8
            ) f
            UNION ALL SELECT 'meaning', count(DISTINCT item_id) FROM item_meaning
            UNION ALL SELECT 'embedding', count(DISTINCT item_id) FROM item_embedding
            UNION ALL SELECT 'relationship', count(*) FROM relationship_master
            UNION ALL SELECT 'occasion', count(*) FROM occasion_master
            UNION ALL SELECT 'pair', count(*) FROM pair_master
            UNION ALL SELECT 'pair_rule', count(*) FROM pair_rule
            UNION ALL SELECT 'recommendation_request', count(*) FROM recommendation_request
            """
        )
        genres = self.db.fetch(
            """
            SELECT g.genre_name, count(*)::bigint AS n
            FROM item i
            LEFT JOIN external_genre g
              ON g.external_genre_id = i.external_genre_id AND g.source = i.source
            GROUP BY g.genre_name
            ORDER BY n DESC
            LIMIT 12
            """
        )
        genre_rows = "".join(
            f"<tr><td>{h(r.get('genre_name') or '(NULL)')}</td><td>{h(r.get('n'))}</td></tr>"
            for r in genres
        )
        body = f"""
        <h2>概況</h2>
        <p class="muted">件数は local DB の現在値です。カタログ検証スナップショット（#1888）とは別画面です。</p>
        {metric_cards(counts)}
        <h3>テーブルの見方</h3>
        <div class="rel">
          <div class="box">item<br><span class="muted">商品正本</span></div>
          <span class="arrow">→</span>
          <div class="box">item_image / external_genre</div>
          <span class="arrow">→</span>
          <div class="box">item_semantic → item_feature（8軸）→ item_meaning<br>
            <span class="muted">Social / Symbolic</span></div>
          <span class="arrow">→</span>
          <div class="box">item_embedding<br><span class="muted">Retrieval 用（ベクトルは非表示）</span></div>
        </div>
        <div class="rel">
          <div class="box">relationship_master</div>
          <span class="arrow">×</span>
          <div class="box">occasion_master</div>
          <span class="arrow">→</span>
          <div class="box">pair_master</div>
          <span class="arrow">→</span>
          <div class="box">pair_rule（feature_delta）</div>
        </div>
        <div class="rel">
          <div class="box">recommendation_request<br>
            <span class="muted">MVP に独立 User マスタはない。推薦入力がユーザー相当</span></div>
        </div>
        <h3>ジャンル件数（上位）</h3>
        <table><thead><tr><th>genre_name</th><th>件数</th></tr></thead>
        <tbody>{genre_rows}</tbody></table>
        <h3>商品群の絞り込み材料</h3>
        <p class="muted">楽天ランキングAPIの総合 / 年代 / 性別 / 年代×性別（ジャンル指定以外）は
        <a href="/ranking">ランキング分析</a>。
        <a href="/genres">ジャンル階層</a> で初期取り扱い対象をチェックできます。DB には書き込みません。</p>
        """
        self._page("概況", "home", body)

    def _list_items(self, *, title: str, active: str, meaning_default: str) -> None:
        qs = self._qs()
        q = (qs.get("q") or "")[:80]
        meaning = qs.get("meaning", meaning_default)
        try:
            page = max(1, int(qs.get("page") or "1"))
        except ValueError:
            page = 1
        where = ["TRUE"]
        params: list[Any] = []
        if q:
            where.append("(i.item_name ILIKE %s OR i.external_item_code ILIKE %s)")
            like = f"%{q}%"
            params.extend([like, like])
        if meaning == "yes":
            where.append("EXISTS (SELECT 1 FROM item_meaning m WHERE m.item_id = i.item_id)")
        elif meaning == "no":
            where.append("NOT EXISTS (SELECT 1 FROM item_meaning m WHERE m.item_id = i.item_id)")
        where_sql = " AND ".join(where)
        total_row = self.db.fetch_one(
            f"SELECT count(*)::bigint AS n FROM item i WHERE {where_sql}",
            tuple(params),
        )
        total = int(total_row["n"]) if total_row else 0
        offset = (page - 1) * PAGE_SIZE
        rows = self.db.fetch(
            ITEM_SELECT + f" WHERE {where_sql} ORDER BY i.updated_at DESC LIMIT %s OFFSET %s",
            tuple(params) + (PAGE_SIZE, offset),
        )
        hint = ""
        if active == "reco":
            hint = (
                "<p class='muted'>レコメンド計算で使うのは meaning / feature / embedding が揃った商品です。"
                " 現状カバー率が低い場合は、意味生成バッチの消化途中です。</p>"
            )
        body = (
            f"<h2>{h(title)}</h2>{hint}"
            + item_filters_form("/reco" if active == "reco" else "/items", q, meaning)
            + render_item_cards(rows)
            + pager(
                "/reco" if active == "reco" else "/items",
                page,
                total,
                {"q": q, "meaning": meaning},
            )
        )
        self._page(title, active, body)

    def page_items(self) -> None:
        self._list_items(title="商品リスト", active="items", meaning_default="")

    def page_reco(self) -> None:
        qs = self._qs()
        meaning_default = "yes" if "meaning" not in qs else qs.get("meaning", "")
        self._list_items(title="レコメンド用商品", active="reco", meaning_default=meaning_default)

    def page_item(self, item_id: str) -> None:
        if not is_uuid(item_id):
            self._page("商品", "items", "<p>item_id が不正です。</p>", 400)
            return
        row = self.db.fetch_one(ITEM_SELECT + " WHERE i.item_id = %s", (item_id,))
        if not row:
            self._page("商品", "items", "<p>商品が見つかりません。</p>", 404)
            return
        detail = self.db.fetch_one(
            """
            SELECT item_caption, catchcopy, item_url, source, first_fetched_at, last_checked_at, updated_at
            FROM item WHERE item_id = %s
            """,
            (item_id,),
        ) or {}
        images = self.db.fetch(
            """
            SELECT image_url, is_primary, image_size_type, display_order
            FROM item_image WHERE item_id = %s
            ORDER BY is_primary DESC, display_order
            LIMIT 8
            """,
            (item_id,),
        )
        features = self.db.fetch(
            """
            SELECT DISTINCT ON (feature_code)
              feature_code, raw_feature_value, normalized_feature_value, generated_at
            FROM item_feature
            WHERE item_id = %s
            ORDER BY feature_code, generated_at DESC
            """,
            (item_id,),
        )
        feat_map = {r["feature_code"]: r for r in features}
        meaning = self.db.fetch_one(
            """
            SELECT item_social, item_symbolic, generated_at
            FROM item_meaning WHERE item_id = %s
            ORDER BY generated_at DESC LIMIT 1
            """,
            (item_id,),
        )
        semantic = self.db.fetch_one(
            """
            SELECT semantic_json, generated_at
            FROM item_semantic WHERE item_id = %s
            ORDER BY generated_at DESC LIMIT 1
            """,
            (item_id,),
        )
        embedding = self.db.fetch_one(
            """
            SELECT item_embedding_id, model_version_id, embedding_source_type, generated_at,
                   vector_dims(embedding_vector) AS dims
            FROM item_embedding WHERE item_id = %s
            ORDER BY generated_at DESC LIMIT 1
            """,
            (item_id,),
        )
        queue = self.db.fetch(
            """
            SELECT generation_type, queue_status, queued_at, completed_at,
                   left(coalesce(error_message, ''), 80) AS error_prefix
            FROM item_generation_queue
            WHERE item_id = %s
            ORDER BY queued_at DESC NULLS LAST
            LIMIT 8
            """,
            (item_id,),
        )
        feat_rows = []
        for code, label, group in FEATURE_AXES:
            frow = feat_map.get(code)
            feat_rows.append(
                "<tr>"
                f"<td>{h(group)}</td><td>{h(code)}<br><span class='muted'>{h(label)}</span></td>"
                f"<td>{bar(frow.get('normalized_feature_value') if frow else None)}</td>"
                f"<td>{num(frow.get('raw_feature_value') if frow else None)}</td>"
                "</tr>"
            )
        concepts = []
        if semantic and isinstance(semantic.get("semantic_json"), dict):
            raw_concepts = semantic["semantic_json"].get("concepts") or []
            if isinstance(raw_concepts, list):
                for c in raw_concepts[:40]:
                    if isinstance(c, dict):
                        concepts.append(
                            f"<span class='chip'>{h(c.get('concept_code'))}"
                            f" {h(num(c.get('confidence'), 2))}</span>"
                        )
        imgs = "".join(
            f'<img src="{h(im["image_url"])}" alt="" loading="lazy" referrerpolicy="no-referrer" '
            f'style="width:100%;border-radius:8px;margin-bottom:8px">'
            for im in images
            if im.get("image_url")
        ) or '<div class="ph">画像なし</div>'
        caption = (detail.get("item_caption") or "")[:400]
        qrows = "".join(
            "<tr>"
            f"<td>{h(r.get('generation_type'))}</td><td>{h(r.get('queue_status'))}</td>"
            f"<td>{jst(r.get('queued_at'))}</td><td>{h(r.get('error_prefix') or '')}</td>"
            "</tr>"
            for r in queue
        ) or "<tr><td colspan='4'>queue 行なし</td></tr>"
        url_text = detail.get("item_url") or ""
        url_show = url_text if len(url_text) < 80 else url_text[:77] + "..."
        body = f"""
        <p><a href="/items">← 商品リスト</a></p>
        <div class="detail">
          <div>{imgs}</div>
          <div>
            <h2>{h(row.get("item_name"))}</h2>
            <p>{money(row.get("price"))} · {h(row.get("genre_name") or "ジャンルなし")}
               · {chip(bool(row.get("is_active")), row.get("active_status") or "active", "inactive")}</p>
            <p class="muted">code: {h(row.get("external_item_code"))} / shop: {h(row.get("shop_code"))}</p>
            <p>{h(detail.get("catchcopy"))}</p>
            <p>{h(caption)}{"…" if (detail.get("item_caption") or "")[400:] else ""}</p>
            <p class="muted">item_url: {h(url_show)}</p>
            <h3>Gift Meaning（item_meaning）</h3>
            <p>Social {bar(meaning.get("item_social") if meaning else None)}
               · Symbolic {bar(meaning.get("item_symbolic") if meaning else None)}</p>
            <h3>Feature 8軸（正規化値）</h3>
            <table><thead><tr><th>群</th><th>軸</th><th>normalized</th><th>raw</th></tr></thead>
            <tbody>{"".join(feat_rows)}</tbody></table>
            <h3>Semantic concepts</h3>
            <p>{"".join(concepts) or '<span class="muted">semantic なし</span>'}</p>
            <h3>Embedding</h3>
            <p>{chip(bool(embedding), f"あり ({embedding.get('dims') if embedding else ''}次元)", "なし")}
               <span class="muted">ベクトル本体は非表示 · {jst(embedding.get("generated_at") if embedding else None)}</span></p>
            <h3>generation queue</h3>
            <table><thead><tr><th>type</th><th>status</th><th>queued</th><th>error prefix</th></tr></thead>
            <tbody>{qrows}</tbody></table>
          </div>
        </div>
        """
        self._page(str(row.get("item_name") or "商品"), "items", body)

    def page_masters(self) -> None:
        rels = self.db.fetch(
            """
            SELECT relationship_code, relationship_label, is_active, display_order
            FROM relationship_master
            ORDER BY display_order, relationship_code
            """
        )
        occs = self.db.fetch(
            """
            SELECT occasion_code, occasion_label, is_active, display_order
            FROM occasion_master
            ORDER BY display_order, occasion_code
            """
        )
        rel_rows = "".join(
            "<tr>"
            f"<td>{h(r['relationship_code'])}</td><td>{h(r['relationship_label'])}</td>"
            f"<td>{chip(bool(r['is_active']), 'active', 'inactive')}</td>"
            f"<td>{h(r['display_order'])}</td></tr>"
            for r in rels
        )
        occ_rows = "".join(
            "<tr>"
            f"<td>{h(r['occasion_code'])}</td><td>{h(r['occasion_label'])}</td>"
            f"<td>{chip(bool(r['is_active']), 'active', 'inactive')}</td>"
            f"<td>{h(r['display_order'])}</td></tr>"
            for r in occs
        )
        body = f"""
        <h2>Relationship / Occasion</h2>
        <p class="muted">UI 表示名の正本は label 列です。推薦入力は code を LOGICAL 参照します。</p>
        <div class="rel">
          <div class="box">relationship_master（{len(rels)}）</div>
          <span class="arrow">×</span>
          <div class="box">occasion_master（{len(occs)}）</div>
          <span class="arrow">→</span>
          <div class="box"><a href="/pairs">pair_master マトリクス</a></div>
        </div>
        <h3>relationship_master</h3>
        <table><thead><tr><th>code</th><th>label</th><th>状態</th><th>order</th></tr></thead>
        <tbody>{rel_rows}</tbody></table>
        <h3>occasion_master</h3>
        <table><thead><tr><th>code</th><th>label</th><th>状態</th><th>order</th></tr></thead>
        <tbody>{occ_rows}</tbody></table>
        """
        self._page("マスタ", "masters", body)

    def page_pairs(self) -> None:
        rels = self.db.fetch(
            """
            SELECT relationship_code, relationship_label, display_order
            FROM relationship_master ORDER BY display_order, relationship_code
            """
        )
        occs = self.db.fetch(
            """
            SELECT occasion_code, occasion_label, display_order
            FROM occasion_master ORDER BY display_order, occasion_code
            """
        )
        pairs = self.db.fetch(
            """
            SELECT pair_id, relationship_code, occasion_code, is_active
            FROM pair_master
            """
        )
        pair_map = {(p["relationship_code"], p["occasion_code"]): p for p in pairs}
        head = "".join(
            f"<th title='{h(o['occasion_code'])}'>{h(o['occasion_label'])}</th>" for o in occs
        )
        body_rows = []
        for rel in rels:
            cells = [f"<th class='rowh'>{h(rel['relationship_label'])}<br>"
                     f"<span class='muted'>{h(rel['relationship_code'])}</span></th>"]
            for occ in occs:
                pair = pair_map.get((rel["relationship_code"], occ["occasion_code"]))
                if not pair:
                    cells.append("<td class='off'>—</td>")
                    continue
                cls = "on" if pair.get("is_active") else "off"
                mark = "○" if pair.get("is_active") else "×"
                cells.append(
                    f"<td class='{cls}'><a href='/pairs/{h(pair['pair_id'])}' "
                    f"title='{h(rel['relationship_code'])} × {h(occ['occasion_code'])}'>{mark}</a></td>"
                )
            body_rows.append(f"<tr>{''.join(cells)}</tr>")
        body = f"""
        <h2>Relationship × Occasion 組み合わせ</h2>
        <p class="muted">セルが ○ なら pair_master.is_active。クリックすると pair_rule の feature_delta を見ます。
        seed は 12 × 15 の全格子です。</p>
        <div style="overflow:auto">
        <table class="matrix">
          <thead><tr><th class="rowh">関係 \\ 用途</th>{head}</tr></thead>
          <tbody>{''.join(body_rows)}</tbody>
        </table>
        </div>
        """
        self._page("組み合わせ", "pairs", body)

    def page_pair(self, pair_id: str) -> None:
        if not is_uuid(pair_id):
            self._page("Pair", "pairs", "<p>pair_id が不正です。</p>", 400)
            return
        pair = self.db.fetch_one(
            """
            SELECT p.pair_id, p.relationship_code, p.occasion_code, p.is_active,
                   r.relationship_label, o.occasion_label
            FROM pair_master p
            LEFT JOIN relationship_master r ON r.relationship_code = p.relationship_code
            LEFT JOIN occasion_master o ON o.occasion_code = p.occasion_code
            WHERE p.pair_id = %s
            """,
            (pair_id,),
        )
        if not pair:
            self._page("Pair", "pairs", "<p>Pair が見つかりません。</p>", 404)
            return
        rules = self.db.fetch(
            """
            SELECT pr.feature_code, pr.feature_delta, pr.is_active, scv.version_label
            FROM pair_rule pr
            JOIN semantic_config_version scv
              ON scv.semantic_config_version_id = pr.semantic_config_version_id
            WHERE pr.pair_id = %s
            ORDER BY scv.version_label, pr.feature_code
            """,
            (pair_id,),
        )
        rule_map = {(r["version_label"], r["feature_code"]): r for r in rules}
        versions = sorted({r["version_label"] for r in rules}) or ["(rule なし)"]
        tables = []
        for ver in versions:
            rows = []
            for code, label, group in FEATURE_AXES:
                r = rule_map.get((ver, code))
                delta = r.get("feature_delta") if r else None
                rows.append(
                    "<tr>"
                    f"<td>{h(group)}</td><td>{h(code)} / {h(label)}</td>"
                    f"<td>{num(delta)}</td>"
                    f"<td>{chip(bool(r and r.get('is_active')), 'active', 'なし') if r else '—'}</td>"
                    "</tr>"
                )
            tables.append(
                f"<h3>pair_rule · version {h(ver)}</h3>"
                "<table><thead><tr><th>群</th><th>軸</th><th>feature_delta</th><th>状態</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>"
            )
        if not rules:
            tables = ["<div class='empty'>この Pair に pair_rule 行はありません（補正なしの組み合わせ）。</div>"]
        body = f"""
        <p><a href="/pairs">← マトリクス</a></p>
        <h2>{h(pair.get("relationship_label"))} × {h(pair.get("occasion_label"))}</h2>
        <p class="muted">{h(pair.get("relationship_code"))} × {h(pair.get("occasion_code"))}
           · {chip(bool(pair.get("is_active")), "active", "inactive")}</p>
        {''.join(tables)}
        """
        self._page("Pair", "pairs", body)

    def page_requests(self) -> None:
        total_row = self.db.fetch_one("SELECT count(*)::bigint AS n FROM recommendation_request")
        total = int(total_row["n"]) if total_row else 0
        qs = self._qs()
        try:
            page = max(1, int(qs.get("page") or "1"))
        except ValueError:
            page = 1
        offset = (page - 1) * PAGE_SIZE
        rows = self.db.fetch(
            """
            SELECT
              rr.recommendation_request_id,
              rr.request_mode,
              rr.relationship_code,
              rr.occasion_code,
              r.relationship_label,
              o.occasion_label,
              rr.budget_min,
              rr.budget_max,
              left(coalesce(rr.preferred_text, ''), 80) AS preferred_short,
              left(coalesce(rr.free_text, ''), 80) AS free_short,
              rr.created_at
            FROM recommendation_request rr
            LEFT JOIN relationship_master r ON r.relationship_code = rr.relationship_code
            LEFT JOIN occasion_master o ON o.occasion_code = rr.occasion_code
            ORDER BY rr.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (PAGE_SIZE, offset),
        )
        tr = "".join(
            "<tr>"
            f"<td class='muted'>{h(str(r.get('recommendation_request_id'))[:8])}…</td>"
            f"<td>{h(r.get('request_mode'))}</td>"
            f"<td>{h(r.get('relationship_label') or r.get('relationship_code'))}</td>"
            f"<td>{h(r.get('occasion_label') or r.get('occasion_code'))}</td>"
            f"<td>{money(r.get('budget_min'))} – {money(r.get('budget_max'))}</td>"
            f"<td>{h(r.get('preferred_short'))}</td>"
            f"<td>{h(r.get('free_short'))}</td>"
            f"<td>{jst(r.get('created_at'))}</td>"
            "</tr>"
            for r in rows
        ) or "<tr><td colspan='8'>まだ推薦入力がありません。画面からレコメンドを実行するとここに増えます。</td></tr>"
        body = f"""
        <h2>推薦入力（ユーザー相当）</h2>
        <p class="muted">MVP では独立した <code>user</code> テーブルはありません（認証 Epic まで user_id 列なし）。
        人が選んだ関係・用途・予算・好みは <code>recommendation_request</code> に残ります。
        request_payload の JSON 全文は出しません。</p>
        <table>
          <thead><tr>
            <th>id</th><th>mode</th><th>関係</th><th>用途</th><th>予算</th>
            <th>preferred</th><th>free_text</th><th>作成</th>
          </tr></thead>
          <tbody>{tr}</tbody>
        </table>
        {pager("/requests", page, total, {})}
        """
        self._page("推薦入力", "requests", body)

    def page_ranking(self, form: dict[str, str] | None = None) -> None:
        qs = self._qs()
        form = form or {}
        pattern = (form.get("pattern") or qs.get("pattern") or "overall").strip()
        if pattern not in {"overall", "age", "sex", "age_sex", "cross"}:
            pattern = "overall"
        view = (form.get("view") or qs.get("view") or "summary").strip()
        if view not in {"summary", "items", "genres", "shops", "keywords"}:
            view = "summary"
        default_slice = ranking.default_slice_for_pattern(pattern)
        slice_id = (form.get("slice") or qs.get("slice") or default_slice.slice_id).strip()
        selected = ranking.get_slice(slice_id)
        if pattern != "cross" and (selected is None or selected.pattern != pattern):
            slice_id = default_slice.slice_id
        try:
            pages = max(1, min(ranking.MAX_PAGES, int(form.get("pages") or qs.get("pages") or "1")))
        except ValueError:
            pages = 1
        fetch_scope = (form.get("fetch_scope") or qs.get("refresh") or "").strip()
        if fetch_scope == "1":
            fetch_scope = "slice"
        target_only = (form.get("target") or qs.get("target") or "") == "1"
        notices = ""
        if fetch_scope in {"slice", "pattern", "all"}:
            notices = self._fetch_ranking(
                pattern=pattern,
                slice_id=slice_id,
                fetch_scope=fetch_scope,
                pages=pages,
            )
        caches = ranking.load_all_cached()
        creds = ranking.credentials_status(dict(os.environ))
        status_html = self._ranking_status_bar(caches, creds)
        target_bar = self._ranking_target_bar(pattern, view, slice_id, target_only)
        tabs = self._ranking_pattern_tabs(pattern, view, slice_id, target_only)
        if pattern == "cross":
            body = (
                notices + status_html + target_bar + tabs
                + self._ranking_cross_body(caches, target_only=target_only)
            )
            self._page("ランキング分析", "ranking", body)
            return
        slice_ = ranking.get_slice(slice_id) or default_slice
        slice_nav = self._ranking_slice_nav(pattern, slice_.slice_id, view, target_only)
        fetch_forms = self._ranking_fetch_forms(pattern, slice_.slice_id, view, pages, creds)
        view_tabs = self._ranking_view_tabs(pattern, slice_.slice_id, view, target_only)
        cached = caches.get(slice_.slice_id)
        items = cached.items if cached else []
        items = self._filter_ranking_by_target(items, target_only)
        analysis = self._ranking_slice_body(slice_, cached, items, view)
        hint = (
            "<p class='muted'>公式仕様では genreId と age / sex は同時指定できません。"
            " 本画面は ②ジャンル別ランキングを扱いません。"
            " 取得結果は local cache のみ（DB 未書き込み / BATCH-002 とは別経路）。</p>"
        )
        body = (
            "<h2>ランキング分析（管理者確認）</h2>"
            + hint
            + notices
            + status_html
            + target_bar
            + tabs
            + slice_nav
            + fetch_forms
            + view_tabs
            + analysis
        )
        self._page("ランキング分析", "ranking", body)

    def _fetch_ranking(
        self,
        *,
        pattern: str,
        slice_id: str,
        fetch_scope: str,
        pages: int,
    ) -> str:
        creds = ranking.credentials_status(dict(os.environ))
        if not creds["ready"]:
            return (
                "<div class='banner warn'>楽天API資格情報が不足しています。"
                " <code>RAKUTEN_APPLICATION_ID</code> と <code>RAKUTEN_ACCESS_KEY</code>"
                " を .env に設定し、ビューアを再起動してください（値は表示しません）。</div>"
            )
        targets = ranking.resolve_fetch_targets(
            pattern=pattern, slice_id=slice_id, fetch_scope=fetch_scope
        )
        if not targets:
            return "<div class='banner warn'>取得対象のスライスが解決できませんでした。</div>"
        ok, errors = ranking.fetch_and_cache_many(
            targets,
            application_id=os.environ.get("RAKUTEN_APPLICATION_ID", "").strip(),
            access_key=os.environ.get("RAKUTEN_ACCESS_KEY", "").strip(),
            pages=pages,
        )
        parts = []
        if ok:
            parts.append(
                f"<div class='banner ok'>取得成功: {h(', '.join(ok))}"
                f"（{len(ok)} 件 / cache 保存。DB 未書き込み）</div>"
            )
        for sid, err in errors:
            parts.append(
                f"<div class='banner warn'>取得失敗 {h(sid)}: {h(err)}</div>"
            )
        return "".join(parts)

    def _ranking_status_bar(
        self,
        caches: dict[str, ranking.SliceCache],
        creds: dict[str, bool],
    ) -> str:
        total = len(ranking.all_slices())
        ready = "あり" if creds["ready"] else "不足"
        cred_cls = "ok" if creds["ready"] else "warn"
        cards = [
            {"k": "cache 済みスライス", "n": f"{len(caches)} / {total}"},
            {"k": "楽天資格情報", "n": ready},
            {"k": "1スライスの件数目安", "n": "最大 30件/page"},
        ]
        return (
            f"<div class='banner {cred_cls}'>資格情報: applicationId "
            f"{'設定済' if creds['application_id'] else '未設定'} / accessKey "
            f"{'設定済' if creds['access_key'] else '未設定'}。"
            " 値は出しません。全パターン取得は 18 リクエストで数十秒かかります"
            f"（間隔 {ranking.MIN_INTERVAL_SEC} 秒）。</div>"
            + metric_cards(cards)
        )

    def _ranking_target_q(self, target_only: bool) -> str:
        return "&target=1" if target_only else ""

    def _ranking_target_bar(
        self, pattern: str, view: str, slice_id: str, target_only: bool
    ) -> str:
        selection = genre_select.load_selection()
        count = len(selection["genre_ids"])
        href = (
            f"/ranking?pattern={html.escape(pattern, quote=True)}"
            f"&view={html.escape(view, quote=True)}"
            f"&slice={html.escape(slice_id, quote=True)}"
        )
        if target_only:
            label = "対象ジャンルフィルターを解除"
        else:
            href += "&target=1"
            label = "対象ジャンルで絞り込む"
        mode = "配下含む" if selection["filter_mode"] == "descendants" else "チェックしたジャンルのみ"
        return (
            f"<p class='muted'><a href='/genres'>初期取り扱いジャンル</a> "
            f"{count} 件（{h(mode)}）。"
            f" <a class='btn' href='{href}'>{h(label)}</a></p>"
        )

    def _filter_ranking_by_target(
        self, items: list[ranking.RankingItem], target_only: bool
    ) -> list[ranking.RankingItem]:
        if not target_only:
            return items
        allowed = self._target_genre_id_set()
        if not allowed:
            return []
        filtered = []
        for item in items:
            gid = genre_select.parse_genre_id(item.genre_id)
            if gid is not None and gid in allowed:
                filtered.append(item)
        return filtered

    def _target_genre_id_set(self) -> set[int]:
        selection = genre_select.load_selection()
        selected = selection["genre_ids"]
        if not selected:
            return set()
        if selection["filter_mode"] == "exact":
            return set(selected)
        return self._expand_genre_ids(selected)

    def _expand_genre_ids(self, selected: list[int]) -> set[int]:
        tree = self._genre_tree_data()
        return genre_select.expand_descendants(selected, tree["children"])

    def _ranking_pattern_tabs(
        self, pattern: str, view: str, slice_id: str, target_only: bool = False
    ) -> str:
        extra = self._ranking_target_q(target_only)
        links = []
        for key, label in ranking.PATTERN_LABELS.items():
            href = f"/ranking?pattern={key}&view={view}{extra}"
            if key not in {"cross", "overall"}:
                href += f"&slice={html.escape(slice_id, quote=True)}"
            cls = "active" if key == pattern else ""
            links.append(f'<a class="{cls}" href="{href}">{h(label)}</a>')
        return f'<div class="tabs">{"".join(links)}</div>'

    def _ranking_slice_nav(
        self, pattern: str, slice_id: str, view: str, target_only: bool = False
    ) -> str:
        if pattern == "overall":
            return ""
        extra = self._ranking_target_q(target_only)
        links = []
        for slice_ in ranking.slices_for_pattern(pattern):
            href = f"/ranking?pattern={pattern}&slice={slice_.slice_id}&view={view}{extra}"
            cls = "active" if slice_.slice_id == slice_id else ""
            links.append(f'<a class="{cls}" href="{href}">{h(slice_.label())}</a>')
        return f'<div class="tabs">{"".join(links)}</div>'

    def _ranking_view_tabs(
        self, pattern: str, slice_id: str, view: str, target_only: bool = False
    ) -> str:
        labels = {
            "summary": "サマリ",
            "items": "商品一覧",
            "genres": "ジャンル選定",
            "shops": "ショップ選定",
            "keywords": "キーワード選定",
        }
        extra = self._ranking_target_q(target_only)
        links = []
        for key, label in labels.items():
            href = f"/ranking?pattern={pattern}&slice={slice_id}&view={key}{extra}"
            cls = "active" if key == view else ""
            links.append(f'<a class="{cls}" href="{href}">{h(label)}</a>')
        return f'<div class="tabs">{"".join(links)}</div>'

    def _ranking_fetch_forms(
        self,
        pattern: str,
        slice_id: str,
        view: str,
        pages: int,
        creds: dict[str, bool],
    ) -> str:
        disabled = " disabled" if not creds["ready"] else ""
        hidden = (
            f'<input type="hidden" name="pattern" value="{h(pattern)}">'
            f'<input type="hidden" name="slice" value="{h(slice_id)}">'
            f'<input type="hidden" name="view" value="{h(view)}">'
            f'<input type="hidden" name="pages" value="{pages}">'
        )
        return f"""
        <form class="inline" method="post" action="/ranking">
          {hidden}
          <input type="hidden" name="fetch_scope" value="slice">
          <button type="submit"{disabled}>このスライスを取得</button>
        </form>
        <form class="inline" method="post" action="/ranking">
          {hidden}
          <input type="hidden" name="fetch_scope" value="pattern">
          <button type="submit"{disabled}>このパターンを取得</button>
        </form>
        <form class="inline" method="post" action="/ranking">
          {hidden}
          <input type="hidden" name="fetch_scope" value="all">
          <button type="submit"{disabled}>①③④⑤ 全スライス取得（18件）</button>
        </form>
        """

    def _ranking_slice_body(
        self,
        slice_: ranking.RankingSlice,
        cached: ranking.SliceCache | None,
        items: list[ranking.RankingItem],
        view: str,
    ) -> str:
        if not cached:
            return (
                f"<div class='empty'>{h(slice_.label())} はまだ取得していません。"
                " 上の取得ボタンを押してください。</div>"
            )
        meta = (
            f"<p class='muted'>{h(slice_.label())} · title {h(cached.title or '—')} · "
            f"lastBuildDate {h(cached.last_build_date or '—')} · "
            f"取得 {h(cached.fetched_at)} · {len(items)} 件</p>"
        )
        genre_labels = self._genre_labels([i.genre_id for i in items if i.genre_id])
        catalog_items = self._catalog_item_map([i.item_code for i in items])
        catalog_shops = self._catalog_shop_counts([i.shop_code for i in items if i.shop_code])
        agg = ranking.aggregate_items(items)
        if view == "items":
            return meta + self._render_ranking_items(items, genre_labels, catalog_items)
        if view == "genres":
            return meta + self._render_count_table(
                "ジャンル選定候補",
                agg["genres"],
                key_header="genreId",
                labels=genre_labels,
                extra_fn=lambda row: f"local商品 {self._genre_local_count(row.key)}",
            )
        if view == "shops":
            return meta + self._render_count_table(
                "ショップコード選定候補",
                agg["shops"],
                key_header="shopCode",
                extra_fn=lambda row: (
                    f"local商品 {catalog_shops.get(row.key, 0)}"
                ),
            )
        if view == "keywords":
            return meta + self._render_count_table(
                "キーワード選定候補（商品名・キャッチから抽出）",
                agg["keywords"][:80],
                key_header="keyword",
            )
        return meta + self._render_ranking_summary(
            items, agg, genre_labels, catalog_items, catalog_shops
        )

    def _ranking_cross_body(
        self, caches: dict[str, ranking.SliceCache], *, target_only: bool = False
    ) -> str:
        items = ranking.flatten_cached_items(caches)
        items = self._filter_ranking_by_target(items, target_only)
        if not items:
            return "<div class='empty'>まだ cache がありません。各パターンで取得してください。</div>"
        genre_labels = self._genre_labels([i.genre_id for i in items if i.genre_id])
        catalog_items = self._catalog_item_map([i.item_code for i in items])
        catalog_shops = self._catalog_shop_counts([i.shop_code for i in items if i.shop_code])
        agg = ranking.aggregate_items(items)
        def _age_col(item: ranking.RankingItem) -> str:
            sl = ranking.get_slice(item.slice_id)
            if sl is None or sl.age is None:
                return ""
            return ranking.AGE_LABELS.get(sl.age, "")

        def _sex_col(item: ranking.RankingItem) -> str:
            sl = ranking.get_slice(item.slice_id)
            if sl is None or sl.sex is None:
                return ""
            return ranking.SEX_LABELS.get(sl.sex, "")

        age_cols, age_matrix = ranking.cross_matrix(
            items, row_key=lambda i: i.genre_id, col_key=_age_col
        )
        sex_cols, sex_matrix = ranking.cross_matrix(
            items, row_key=lambda i: i.genre_id, col_key=_sex_col
        )
        in_catalog = sum(1 for i in items if i.item_code in catalog_items)
        summary = f"""
        <p class="muted">取得済み {len(caches)} スライス / 延べ {len(items)} 件
        （同一商品の重複あり） / local 既存 {in_catalog} 件。</p>
        <h3>選定サマリ（スライス横断で強いもの）</h3>
        <p class="muted">並びは「何スライスに出たか」優先。ギフト向けジャンル・常連ショップ・繰り返し語を見るための材料です。採択は Human 判断です。</p>
        """
        return (
            summary
            + "<div class='two-col'>"
            + self._render_count_table("ジャンル", agg["genres"][:20], "genreId", genre_labels)
            + self._render_count_table(
                "ショップ",
                agg["shops"][:20],
                "shopCode",
                extra_fn=lambda row: f"local {catalog_shops.get(row.key, 0)}",
            )
            + "</div>"
            + self._render_count_table("キーワード", agg["keywords"][:40], "keyword")
            + self._render_matrix("ジャンル × 年代（③⑤の件数）", age_cols, age_matrix, genre_labels)
            + self._render_matrix("ジャンル × 性別（④⑤の件数）", sex_cols, sex_matrix, genre_labels)
        )

    def _render_ranking_summary(
        self,
        items: list[ranking.RankingItem],
        agg: dict[str, list[ranking.CountRow]],
        genre_labels: dict[str, str],
        catalog_items: dict[str, dict[str, Any]],
        catalog_shops: dict[str, int],
    ) -> str:
        in_catalog = sum(1 for i in items if i.item_code in catalog_items)
        cards = [
            {"k": "ランキング件数", "n": len(items)},
            {"k": "ユニーク商品", "n": len({i.item_code for i in items})},
            {"k": "ジャンル種", "n": len(agg["genres"])},
            {"k": "ショップ種", "n": len(agg["shops"])},
            {"k": "local 既存商品", "n": in_catalog},
        ]
        return (
            metric_cards(cards)
            + "<div class='two-col'>"
            + self._render_count_table("ジャンル上位", agg["genres"][:12], "genreId", genre_labels)
            + self._render_count_table(
                "ショップ上位",
                agg["shops"][:12],
                "shopCode",
                extra_fn=lambda row: f"local {catalog_shops.get(row.key, 0)}",
            )
            + "</div>"
            + self._render_count_table("キーワード上位", agg["keywords"][:20], "keyword")
        )

    def _render_ranking_items(
        self,
        items: list[ranking.RankingItem],
        genre_labels: dict[str, str],
        catalog_items: dict[str, dict[str, Any]],
    ) -> str:
        if not items:
            return "<div class='empty'>商品がありません。</div>"
        rows = []
        for item in items:
            img = (
                f'<img class="thumb-sm" src="{h(item.image_url)}" alt="" loading="lazy" '
                f'referrerpolicy="no-referrer">'
                if item.image_url
                else '<div class="thumb-sm"></div>'
            )
            catalog = catalog_items.get(item.item_code)
            local = (
                f'<a href="/items/{h(catalog["item_id"])}">local</a>'
                if catalog
                else '<span class="muted">未取込</span>'
            )
            name = item.item_name or item.item_code
            url = (
                f'<a href="{h(item.item_url)}" rel="noreferrer" target="_blank">{h(name)}</a>'
                if item.item_url
                else h(name)
            )
            rows.append(
                "<tr>"
                f'<td class="rank">{h(item.rank)}</td><td>{img}</td><td>{url}'
                f'<div class="muted">{h(item.catchcopy)}</div></td>'
                f"<td>{money(item.price)}</td>"
                f"<td>{h(genre_labels.get(item.genre_id) or item.genre_id or '—')}"
                f'<div class="muted">{h(item.genre_id)}</div></td>'
                f"<td>{h(item.shop_name or item.shop_code)}"
                f'<div class="muted">{h(item.shop_code)}</div></td>'
                f"<td>{local}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>rank</th><th></th><th>商品</th><th>価格</th>"
            "<th>ジャンル</th><th>ショップ</th><th>catalog</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def _render_count_table(
        self,
        title: str,
        rows: list[ranking.CountRow],
        key_header: str,
        labels: dict[str, str] | None = None,
        extra_fn: Any = None,
    ) -> str:
        if not rows:
            return f"<h3>{h(title)}</h3><div class='empty'>集計対象がありません。</div>"
        body_rows = []
        for index, row in enumerate(rows, start=1):
            label = (labels or {}).get(row.key) or row.label or row.key
            extra = extra_fn(row) if extra_fn else ""
            body_rows.append(
                "<tr>"
                f"<td>{index}</td><td>{h(row.key)}</td><td>{h(label)}</td>"
                f"<td>{row.count}</td><td>{row.unique_items}</td>"
                f"<td>{len(row.slice_ids)}</td>"
                f"<td class='muted'>{h(extra)}</td>"
                "</tr>"
            )
        return f"""
        <h3>{h(title)}</h3>
        <table>
          <thead><tr>
            <th>#</th><th>{h(key_header)}</th><th>表示名</th>
            <th>出現</th><th>ユニーク商品</th><th>スライス数</th><th>補足</th>
          </tr></thead>
          <tbody>{''.join(body_rows)}</tbody>
        </table>
        """

    def _render_matrix(
        self,
        title: str,
        cols: list[str],
        matrix: list[tuple[str, dict[str, int]]],
        labels: dict[str, str],
    ) -> str:
        if not cols or not matrix:
            return f"<h3>{h(title)}</h3><div class='empty'>横断集計できる年代/性別データがまだありません。</div>"
        head = "".join(f"<th>{h(col)}</th>" for col in cols)
        rows = []
        for key, cells in matrix:
            tds = "".join(f"<td>{cells.get(col, 0) or '—'}</td>" for col in cols)
            rows.append(
                f"<tr><th class='rowh'>{h(labels.get(key) or key)}"
                f"<div class='muted'>{h(key)}</div></th>{tds}</tr>"
            )
        return f"""
        <h3>{h(title)}</h3>
        <div style="overflow:auto">
        <table class="matrix">
          <thead><tr><th class="rowh">ジャンル</th>{head}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        </div>
        """

    def _genre_labels(self, genre_ids: list[str]) -> dict[str, str]:
        unique: list[int] = []
        seen: set[int] = set()
        for raw in genre_ids:
            try:
                gid = int(raw)
            except (TypeError, ValueError):
                continue
            if gid not in seen:
                seen.add(gid)
                unique.append(gid)
        if not unique:
            return {}
        try:
            rows = self.db.fetch(
                """
                WITH RECURSIVE needed AS (
                  SELECT external_genre_id, genre_name, parent_external_genre_id, 0 AS depth
                  FROM external_genre
                  WHERE source = 'rakuten' AND external_genre_id = ANY(%s)
                  UNION ALL
                  SELECT g.external_genre_id, g.genre_name, g.parent_external_genre_id, n.depth + 1
                  FROM external_genre g
                  JOIN needed n ON g.external_genre_id = n.parent_external_genre_id
                  WHERE g.source = 'rakuten' AND n.depth < 8
                )
                SELECT external_genre_id, genre_name, parent_external_genre_id
                FROM needed
                """,
                (unique,),
            )
        except Exception:  # noqa: BLE001
            return {}
        by_id = {str(r["external_genre_id"]): r for r in rows}
        labels: dict[str, str] = {}
        for raw in {str(i) for i in unique}:
            labels[raw] = self._genre_path(raw, by_id)
        return labels

    def _genre_path(self, genre_id: str, by_id: dict[str, dict[str, Any]]) -> str:
        parts: list[str] = []
        seen: set[str] = set()
        current = genre_id
        while current and current in by_id and current not in seen:
            seen.add(current)
            name = by_id[current].get("genre_name")
            if name:
                parts.append(str(name))
            parent = by_id[current].get("parent_external_genre_id")
            current = str(parent) if parent is not None else ""
        parts.reverse()
        return " > ".join(parts) if parts else genre_id

    def _genre_local_count(self, genre_id: str) -> int:
        try:
            gid = int(genre_id)
        except (TypeError, ValueError):
            return 0
        try:
            row = self.db.fetch_one(
                """
                SELECT count(*)::bigint AS n
                FROM item
                WHERE source = 'rakuten' AND external_genre_id = %s
                """,
                (gid,),
            )
        except Exception:  # noqa: BLE001
            return 0
        return int(row["n"]) if row else 0

    def _catalog_item_map(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        uniq = [c for c in dict.fromkeys(codes) if c]
        if not uniq:
            return {}
        try:
            rows = self.db.fetch(
                """
                SELECT external_item_code, item_id, is_active, shop_code
                FROM item
                WHERE source = 'rakuten' AND external_item_code = ANY(%s)
                """,
                (uniq,),
            )
        except Exception:  # noqa: BLE001
            return {}
        return {str(r["external_item_code"]): dict(r) for r in rows}

    def _catalog_shop_counts(self, shops: list[str]) -> dict[str, int]:
        uniq = [s for s in dict.fromkeys(shops) if s]
        if not uniq:
            return {}
        try:
            rows = self.db.fetch(
                """
                SELECT shop_code, count(*)::bigint AS n
                FROM item
                WHERE source = 'rakuten' AND shop_code = ANY(%s)
                GROUP BY shop_code
                """,
                (uniq,),
            )
        except Exception:  # noqa: BLE001
            return {}
        return {str(r["shop_code"]): int(r["n"]) for r in rows}

    def page_genres(self, form: dict[str, str] | None = None) -> None:
        qs = self._qs()
        form = form or {}
        view = (form.get("view") or qs.get("view") or "tree").strip()
        if view not in {"tree", "selected"}:
            view = "tree"
        parent_id = genre_select.parse_genre_id(form.get("id") or qs.get("id"))
        q = (form.get("q") or qs.get("q") or "")[:80]
        notice = ""
        if form.get("action") == "save":
            notice = self._save_target_genres(form)
            view = (form.get("view") or "tree").strip() or "tree"
            parent_id = genre_select.parse_genre_id(form.get("id"))
            q = (form.get("q") or "")[:80]
        selection = genre_select.load_selection()
        selected = set(selection["genre_ids"])
        level_rows = self.db.fetch(
            """
            SELECT genre_level,
                   count(*)::bigint AS n,
                   count(*) FILTER (WHERE is_leaf IS TRUE)::bigint AS leaves
            FROM external_genre
            WHERE source = 'rakuten'
            GROUP BY genre_level
            ORDER BY genre_level
            """
        )
        cards = [
            {"k": f"L{r['genre_level']}", "n": r["n"]}
            for r in level_rows
        ]
        cards.append({"k": "対象チェック", "n": len(selected)})
        tabs = (
            f'<div class="tabs">'
            f'<a class="{"active" if view == "tree" else ""}" href="/genres">階層を見る</a>'
            f'<a class="{"active" if view == "selected" else ""}" href="/genres?view=selected">'
            f'対象一覧（{len(selected)}）</a>'
            f'</div>'
        )
        tree = self._genre_tree_data()
        tree_note = (
            "staging_genre から直近親を再構成"
            if tree["source"] == "staging_closest_parent"
            else "external_genre.parent をそのまま使用"
        )
        hint = (
            "<p class='muted'>チェックは OKURI 初期取り扱い対象です。"
            " 保存先は local cache のみ（<code>external_genre</code> は SELECT のみ）。"
            " フィルター既定は「チェックしたジャンル＋配下」。"
            f" 階層表示は {h(tree_note)}。"
            " <code>external_genre.parent</code> は L1 直付けになっている行があるためです。</p>"
        )
        if view == "selected":
            body = (
                "<h2>ジャンル階層 / 初期取り扱い対象</h2>"
                + hint
                + notice
                + metric_cards(cards)
                + tabs
                + self._render_selected_genres(selection, tree)
            )
            self._page("ジャンル階層", "genres", body)
            return
        current = None
        if parent_id and not genre_select.is_virtual_root(parent_id):
            current = self.db.fetch_one(
                """
                SELECT external_genre_id, genre_name, genre_level, is_leaf,
                       parent_external_genre_id
                FROM external_genre
                WHERE source = 'rakuten' AND external_genre_id = %s
                """,
                (parent_id,),
            )
            if not current:
                parent_id = None
        children = self._genre_children(parent_id, q, tree)
        body = (
            "<h2>ジャンル階層 / 初期取り扱い対象</h2>"
            + hint
            + notice
            + metric_cards(cards)
            + tabs
            + self._genre_crumb(current, tree)
            + self._render_genre_level(
                parent_id=parent_id,
                current=current,
                children=children,
                selected=selected,
                selection=selection,
                q=q,
                tree=tree,
            )
        )
        self._page("ジャンル階層", "genres", body)

    def _save_target_genres(self, form: dict[str, str]) -> str:
        raw_all = form.get("_all") or {}
        checked = genre_select.parse_genre_ids(raw_all.get("genre_id") or [])
        visible = genre_select.parse_genre_ids(
            (form.get("visible_ids") or "").split(",")
        )
        existing = genre_select.load_selection()
        merged = genre_select.merge_visible_selection(
            existing["genre_ids"],
            visible=visible,
            checked=checked,
        )
        saved = genre_select.save_selection(
            merged,
            filter_mode=form.get("filter_mode") or existing["filter_mode"],
        )
        return (
            f"<div class='banner ok'>対象ジャンルを保存しました。"
            f" {len(saved['genre_ids'])} 件（{h(saved['updated_at'])}）。"
            " DB には書いていません。</div>"
        )

    def _genre_tree_data(self) -> dict[str, Any]:
        cached = type(self)._genre_tree
        if cached is not None:
            return cached
        source = "external_genre"
        parent_rows: list[tuple[Any, Any, Any]] = []
        staging_n = None
        try:
            staging_n = self.db.fetch_one(
                "SELECT count(*)::bigint AS n FROM staging_genre WHERE source = 'rakuten'"
            )
        except Exception:  # noqa: BLE001
            staging_n = None
        if staging_n and int(staging_n["n"] or 0) > 0:
            source = "staging_closest_parent"
            for row in self.db.fetch(
                """
                SELECT s.external_genre_id, s.parent_external_genre_id, p.genre_level
                FROM staging_genre s
                LEFT JOIN external_genre p
                  ON p.source = 'rakuten'
                 AND p.external_genre_id = s.parent_external_genre_id
                WHERE s.source = 'rakuten'
                """
            ):
                parent_rows.append(
                    (
                        row["external_genre_id"],
                        row["parent_external_genre_id"],
                        row["genre_level"],
                    )
                )
        else:
            for row in self.db.fetch(
                """
                SELECT external_genre_id, parent_external_genre_id
                FROM external_genre
                WHERE source = 'rakuten'
                """
            ):
                parent_rows.append(
                    (row["external_genre_id"], row["parent_external_genre_id"], None)
                )
        parent_of = genre_select.pick_closest_parents(parent_rows)
        children = genre_select.build_children_map(parent_of)
        tree = {
            "source": source,
            "parent_of": parent_of,
            "children": children,
            "descendants": genre_select.descendant_counts(children),
        }
        type(self)._genre_tree = tree
        return tree

    def _genre_children(
        self,
        parent_id: int | None,
        q: str,
        tree: dict[str, Any],
    ) -> list[dict[str, Any]]:
        key = genre_select.VIRTUAL_ROOT_ID if genre_select.is_virtual_root(parent_id) else int(parent_id)
        child_ids = list(tree["children"].get(key, ()))
        if not child_ids:
            return []
        extra = ""
        extra_params: list[Any] = []
        if q:
            extra = " AND (g.genre_name ILIKE %s OR g.external_genre_id::text = %s)"
            extra_params = [f"%{q}%", q]
        rows = self.db.fetch(
            f"""
            SELECT g.external_genre_id, g.genre_name, g.genre_level, g.is_leaf,
                   g.parent_external_genre_id
            FROM external_genre g
            WHERE g.source = 'rakuten' AND g.external_genre_id = ANY(%s){extra}
            ORDER BY g.genre_level, g.genre_name, g.external_genre_id
            """,
            (child_ids,) + tuple(extra_params),
        )
        children_map = tree["children"]
        descendants = tree["descendants"]
        for row in rows:
            gid = int(row["external_genre_id"])
            row["child_count"] = len(children_map.get(gid, ()))
            row["descendant_count"] = int(descendants.get(gid, 0))
        return rows

    def _genre_crumb(self, current: dict[str, Any] | None, tree: dict[str, Any]) -> str:
        parts = ['<a href="/genres">全体</a>']
        if not current:
            return f'<div class="crumb">{"".join(parts)}</div>'
        parent_of: dict[int, int | None] = tree["parent_of"]
        chain_ids: list[int] = []
        gid = int(current["external_genre_id"])
        seen: set[int] = set()
        while gid and gid != genre_select.VIRTUAL_ROOT_ID and gid not in seen:
            seen.add(gid)
            chain_ids.append(gid)
            parent = parent_of.get(gid)
            if parent is None or parent == genre_select.VIRTUAL_ROOT_ID:
                break
            gid = int(parent)
        chain_ids.reverse()
        names: dict[int, str] = {}
        if chain_ids:
            for row in self.db.fetch(
                """
                SELECT external_genre_id, genre_name
                FROM external_genre
                WHERE source = 'rakuten' AND external_genre_id = ANY(%s)
                """,
                (chain_ids,),
            ):
                names[int(row["external_genre_id"])] = str(row["genre_name"])
        for node_id in chain_ids:
            parts.append("<span class='muted'>/</span>")
            label = names.get(node_id) or str(node_id)
            parts.append(f'<a href="/genres?id={node_id}">{h(label)}</a>')
        return f'<div class="crumb">{"".join(parts)}</div>'

    def _render_genre_level(
        self,
        *,
        parent_id: int | None,
        current: dict[str, Any] | None,
        children: list[dict[str, Any]],
        selected: set[int],
        selection: dict[str, Any],
        q: str,
        tree: dict[str, Any],
    ) -> str:
        title = "第1層"
        current_box = ""
        current_child_n = 0
        current_desc_n = 0
        if current:
            cid = int(current["external_genre_id"])
            current_child_n = len(tree["children"].get(cid, ()))
            current_desc_n = int(tree["descendants"].get(cid, 0))
            title = (
                f"{current['genre_name']} の直下"
                f"（L{current['genre_level']} / id {current['external_genre_id']}）"
            )
            current_box = (
                f"<p>{chip(bool(current.get('is_leaf')), 'leaf', '枝')} "
                f"{chip(cid in selected, '対象', '未対象')} "
                f"<span class='muted'>直下 {current_child_n} / 配下 {current_desc_n}</span></p>"
            )
        visible_ids = [str(int(r["external_genre_id"])) for r in children]
        if current and int(current["external_genre_id"]) != genre_select.VIRTUAL_ROOT_ID:
            visible_ids.append(str(int(current["external_genre_id"])))
        search = f"""
        <form class="inline" method="get" action="/genres">
          <input type="hidden" name="id" value="{h(parent_id or '')}">
          <div><label>この階層を検索</label>
            <input name="q" value="{h(q)}" maxlength="80" placeholder="ジャンル名 / ID"></div>
          <button type="submit">絞り込み</button>
        </form>
        """
        rows_html = []
        if current and int(current["external_genre_id"]) != genre_select.VIRTUAL_ROOT_ID:
            cid = int(current["external_genre_id"])
            checked = " checked" if cid in selected else ""
            rows_html.append(
                f'<tr class="{"picked" if cid in selected else ""}">'
                f'<td><label class="check"><input type="checkbox" name="genre_id" value="{cid}"{checked}></label></td>'
                f"<td>このジャンル自身</td>"
                f"<td>{h(current['genre_name'])}</td>"
                f"<td>{cid}</td><td>L{h(current['genre_level'])}</td>"
                f"<td>{chip(bool(current.get('is_leaf')), 'leaf', '枝')}</td>"
                f"<td>{current_child_n}<div class='muted'>配下 {current_desc_n}</div></td>"
                f"<td></td></tr>"
            )
        if not children:
            rows_html.append(
                "<tr><td colspan='8'><span class='muted'>直下の子ジャンルはありません。"
                " 検索条件を外すか、leaf です。</span></td></tr>"
            )
        for row in children:
            gid = int(row["external_genre_id"])
            checked = " checked" if gid in selected else ""
            child_n = int(row.get("child_count") or 0)
            desc_n = int(row.get("descendant_count") or 0)
            drill = (
                f'<a href="/genres?id={gid}">子を見る（{child_n}）</a>'
                if child_n
                else '<span class="muted">末端</span>'
            )
            rows_html.append(
                f'<tr class="{"picked" if gid in selected else ""}">'
                f'<td><label class="check"><input type="checkbox" name="genre_id" value="{gid}"{checked}></label></td>'
                f"<td>直下</td>"
                f'<td><a href="/genres?id={gid}">{h(row["genre_name"])}</a></td>'
                f"<td>{gid}</td><td>L{h(row['genre_level'])}</td>"
                f"<td>{chip(bool(row.get('is_leaf')), 'leaf', '枝')}</td>"
                f"<td>{child_n}<div class='muted'>配下 {desc_n}</div></td>"
                f"<td>{drill}</td></tr>"
            )
        mode_desc = " checked" if selection["filter_mode"] == "descendants" else ""
        mode_exact = " checked" if selection["filter_mode"] == "exact" else ""
        return f"""
        <h3>{h(title)}</h3>
        {current_box}
        {search}
        <form method="post" action="/genres{('?id=' + str(parent_id)) if parent_id else ''}">
          <input type="hidden" name="action" value="save">
          <input type="hidden" name="id" value="{h(parent_id or '')}">
          <input type="hidden" name="view" value="tree">
          <input type="hidden" name="q" value="{h(q)}">
          <input type="hidden" name="visible_ids" value="{h(','.join(visible_ids))}">
          <div class="sticky-save">
            <label style="margin:0">
              <input type="radio" name="filter_mode" value="descendants"{mode_desc}>
              配下も含めてフィルター
            </label>
            <label style="margin:0">
              <input type="radio" name="filter_mode" value="exact"{mode_exact}>
              チェックしたジャンルだけ
            </label>
            <button type="submit">この画面のチェックを保存</button>
            <span class="muted">他階層の選択は残します。</span>
          </div>
          <table>
            <thead><tr>
              <th>対象</th><th>位置</th><th>ジャンル</th><th>id</th>
              <th>層</th><th>leaf</th><th>直下の子</th><th></th>
            </tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
          </table>
        </form>
        """

    def _render_selected_genres(self, selection: dict[str, Any], tree: dict[str, Any]) -> str:
        ids = selection["genre_ids"]
        if not ids:
            return (
                "<div class='empty'>まだ対象ジャンルがありません。"
                " 階層画面でチェックして保存してください。</div>"
            )
        rows = self.db.fetch(
            """
            SELECT g.external_genre_id, g.genre_name, g.genre_level, g.is_leaf
            FROM external_genre g
            WHERE g.source = 'rakuten' AND g.external_genre_id = ANY(%s)
            ORDER BY g.genre_level, g.genre_name
            """,
            (ids,),
        )
        found = {int(r["external_genre_id"]) for r in rows}
        children_map = tree["children"]
        descendants = tree["descendants"]
        tr = []
        for row in rows:
            gid = int(row["external_genre_id"])
            child_n = len(children_map.get(gid, ()))
            desc_n = int(descendants.get(gid, 0))
            tr.append(
                "<tr>"
                f'<td><a href="/genres?id={gid}">{h(row["genre_name"])}</a></td>'
                f"<td>{gid}</td><td>L{h(row['genre_level'])}</td>"
                f"<td>{chip(bool(row.get('is_leaf')), 'leaf', '枝')}</td>"
                f"<td>{child_n}<div class='muted'>配下 {desc_n}</div></td>"
                "</tr>"
            )
        missing = [gid for gid in ids if gid not in found]
        miss = (
            f"<p class='muted'>cache にあるが DB に無い id: {h(', '.join(str(x) for x in missing))}</p>"
            if missing
            else ""
        )
        mode = "配下含む" if selection["filter_mode"] == "descendants" else "チェックのみ"
        return f"""
        <p class="muted">保存 {h(selection.get('updated_at') or '—')} · フィルター {h(mode)}。
        ランキング分析の「対象ジャンルで絞り込む」で使えます。</p>
        {miss}
        <table>
          <thead><tr><th>ジャンル</th><th>id</th><th>層</th><th>leaf</th><th>直下の子</th></tr></thead>
          <tbody>{''.join(tr)}</tbody>
        </table>
        """


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_env_path(root: Path) -> Path | None:
    if (root / ".env").is_file():
        return root / ".env"
    try:
        import subprocess

        common = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            text=True,
        ).strip()
        main_root = Path(common).resolve().parent
        if (main_root / ".env").is_file():
            return main_root / ".env"
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="localhost 限定の読み取り専用データ可視化")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--root", default=str(HERE.parents[2]))
    args = parser.parse_args()

    try:
        bind_host = assert_local_bind_host(args.host)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    env_path = resolve_env_path(root)
    if env_path:
        load_env_file(env_path)
        print(f"info: loaded env file ({env_path.name} only; values not printed)", flush=True)
    else:
        print("warn: .env が見つかりません。環境変数 DATABASE_URL を使います", flush=True)

    try:
        assert_app_env_allows_local_browser(os.environ.get("APP_ENV"))
        db_desc = assert_local_database_url(os.environ.get("DATABASE_URL", ""))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    dsn = os.environ["DATABASE_URL"]
    Handler.db = Db(dsn)
    Handler.db_desc = db_desc
    try:
        Handler.db.fetch("SELECT 1 AS n")
    except Exception as exc:  # noqa: BLE001
        print(f"error: DB 接続に失敗しました（詳細に接続文字列は含めません）: {exc.__class__.__name__}", file=sys.stderr)
        return 3

    httpd = ThreadingHTTPServer((bind_host, args.port), Handler)
    print(f"info: http://{bind_host}:{args.port}/  （Ctrl+C で停止）", flush=True)
    print(f"info: db target {db_desc}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\ninfo: stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
