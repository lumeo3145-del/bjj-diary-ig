# -*- coding: utf-8 -*-
"""
未投稿のうち最も古いエントリを1件、Instagramに投稿する。

v2の変更点:
  - Graph APIのエラー本文をログに出す（原因特定のため）
  - 「今日の日付」ではなく「未投稿で最古のもの」を投稿する
    → GitHub Actions の cron 遅延で日付をまたいでも取りこぼさない
  - 直近12時間以内に投稿済みなら何もしない（cron重複実行の二重投稿防止）
  - 投稿前に画像URLの到達性をチェックする

v3の変更点:
  - POST_LANGS で投稿対象の言語を指定できるようにした
    → JAとENを別々の時刻（別cron）に投稿するため
  - 二重投稿ガードを言語ごとに持つようにした
    → 言語別に投稿時刻が違うので、共通のタイムスタンプでは誤スキップする
  - 「未来日を先取りしない」判定の基準TZを言語ごとに変えた（LANG_UTC_OFFSET）

必要な環境変数:
  META_ACCESS_TOKEN / IG_USER_ID_JA / IG_USER_ID_EN / IMAGE_BASE_URL
任意:
  POST_LANGS  投稿対象の言語をカンマ区切りで指定（既定: "ja,en"）
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
POSTED_PATH = "content/posted.json"
QUEUE_PATH = "content/queue.json"
MIN_HOURS_BETWEEN_POSTS = 12
LANGS = ("ja", "en")

# 「今日」を判定する基準タイムゾーン（UTCからの時差）。
# JAは20:00 JST、ENは20:00 BRT / 19:00 EDT に投稿するため、
# 同じ日付のエントリを指す基準が言語ごとに異なる。
LANG_UTC_OFFSET = {"ja": 9, "en": 0}


def _read_error(e):
    """HTTPError から Graph API のエラー本文を取り出す"""
    try:
        body = e.read().decode("utf-8", "replace")
    except Exception:
        return str(e)
    try:
        err = json.loads(body).get("error", {})
        parts = [
            err.get("message"),
            f"type={err.get('type')}",
            f"code={err.get('code')}",
            f"subcode={err.get('error_subcode')}",
            err.get("error_user_msg"),
        ]
        return " | ".join(str(p) for p in parts if p and "None" not in str(p))
    except Exception:
        return body[:500]


def api_post(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"POST {path} -> {_read_error(e)}") from None


def api_get(path, params):
    qs = urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(f"{GRAPH}/{path}?{qs}") as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {path} -> {_read_error(e)}") from None


def check_image(url):
    """画像URLが実際に取得できるか事前確認"""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req) as res:
            ctype = res.headers.get("Content-Type", "")
            size = res.headers.get("Content-Length", "?")
            if "image" not in ctype:
                raise RuntimeError(f"画像ではありません Content-Type={ctype}")
            print(f"  image OK: {url} ({ctype}, {size} bytes)")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"画像URLが取得できません HTTP {e.code}: {url}") from None


def wait_ready(container_id, token, timeout=120):
    for _ in range(timeout // 5):
        st = api_get(container_id, {"fields": "status_code", "access_token": token})
        if st.get("status_code") == "FINISHED":
            return True
        if st.get("status_code") == "ERROR":
            return False
        time.sleep(5)
    return False


def publish(ig_user_id, image_url, caption, token):
    check_image(image_url)
    c = api_post(f"{ig_user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    cid = c["id"]
    if not wait_ready(cid, token):
        raise RuntimeError(f"コンテナの処理が完了しませんでした: {cid}")

    # FINISHED でも公開直後は 9007 / 2207027 が返ることがあるためリトライ
    last_err = None
    for attempt in range(6):
        try:
            r = api_post(f"{ig_user_id}/media_publish", {
                "creation_id": cid,
                "access_token": token,
            })
            return r["id"]
        except RuntimeError as e:
            last_err = e
            if "9007" not in str(e) and "2207027" not in str(e):
                raise
            print(f"  publish待機中... ({attempt + 1}/6)")
            time.sleep(15)
    raise last_err


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_langs():
    """POST_LANGS から投稿対象の言語を決める（未指定なら全言語）"""
    raw = os.environ.get("POST_LANGS", ",".join(LANGS))
    langs = tuple(l.strip() for l in raw.split(",") if l.strip())
    unknown = [l for l in langs if l not in LANGS]
    if unknown:
        raise RuntimeError(f"POST_LANGS に未知の言語があります: {unknown}")
    if not langs:
        raise RuntimeError("POST_LANGS が空です")
    return langs


def main():
    token = os.environ["META_ACCESS_TOKEN"]
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    ig_ids = {"ja": os.environ["IG_USER_ID_JA"], "en": os.environ["IG_USER_ID_EN"]}
    langs = resolve_langs()

    now = datetime.datetime.now(datetime.timezone.utc)
    # 複数言語を1回で流す場合は、最も遅い基準日（=オフセット最小）に合わせて先取りを防ぐ
    offset = min(LANG_UTC_OFFSET[l] for l in langs)
    today = (now + datetime.timedelta(hours=offset)).strftime("%Y-%m-%d")
    print(f"対象言語={','.join(langs)} today={today}（UTC{offset:+d}基準）")

    queue = load_json(QUEUE_PATH, [])
    posted = load_json(POSTED_PATH, {})

    # 旧フォーマット（言語共通の _last_post_at のみ）からの移行判定
    migrated = any(k.startswith("_last_post_at_") for k in posted)

    # 対象言語のうち未投稿が残っている、最古のエントリを選ぶ
    target = None
    for e in sorted(queue, key=lambda x: x["date"]):
        if e["date"] > today:
            break
        if any(l in e and f"{e['date']}_{l}" not in posted for l in langs):
            target = e
            break

    if target is None:
        print(f"投稿対象なし（today={today}）。queueが尽きた可能性があります。")
        return

    if target["date"] != today:
        print(f"※ {target['date']} の未投稿分を追いつき投稿します（today={today}）")

    failed = False
    for lang in langs:
        if lang not in target:
            continue
        key = f"{target['date']}_{lang}"
        if key in posted:
            print("already posted:", key)
            continue

        # 二重投稿ガードは言語ごと（JAとENで投稿時刻が違うため共通化できない）
        last = posted.get(f"_last_post_at_{lang}")
        if last is None and not migrated:
            last = posted.get("_last_post_at")  # 移行時の1回だけ旧キーを見る
        if last:
            elapsed = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 3600
            if elapsed < MIN_HOURS_BETWEEN_POSTS:
                print(f"skip {lang}: {elapsed:.1f}時間前に投稿済み（{MIN_HOURS_BETWEEN_POSTS}時間以内）")
                continue

        image_url = f"{base}/{target['date']}_{lang}.png"
        try:
            media_id = publish(ig_ids[lang], image_url, target[lang]["caption"], token)
            posted[key] = media_id
            posted[f"_last_post_at_{lang}"] = now.isoformat()
            posted["_last_post_at"] = now.isoformat()
            print("posted:", key, media_id)
        except Exception as ex:
            failed = True
            print(f"FAILED {key}: {ex}", file=sys.stderr)

    with open(POSTED_PATH, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
