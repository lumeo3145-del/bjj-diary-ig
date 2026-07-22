# -*- coding: utf-8 -*-
"""
未投稿のうち最も古いエントリを1件、Instagramに投稿する。

v2の変更点:
  - Graph APIのエラー本文をログに出す（原因特定のため）
  - 「今日の日付」ではなく「未投稿で最古のもの」を投稿する
    → GitHub Actions の cron 遅延で日付をまたいでも取りこぼさない
  - 直近12時間以内に投稿済みなら何もしない（cron重複実行の二重投稿防止）
  - 投稿前に画像URLの到達性をチェックする

必要な環境変数:
  META_ACCESS_TOKEN / IG_USER_ID_JA / IG_USER_ID_EN / IMAGE_BASE_URL
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


def main():
    token = os.environ["META_ACCESS_TOKEN"]
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    ig_ids = {"ja": os.environ["IG_USER_ID_JA"], "en": os.environ["IG_USER_ID_EN"]}

    now = datetime.datetime.now(datetime.timezone.utc)
    today = (now + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")  # JST

    queue = load_json(QUEUE_PATH, [])
    posted = load_json(POSTED_PATH, {})

    # 未投稿（または片方だけ投稿済み）で最古のエントリを選ぶ
    target = None
    for e in sorted(queue, key=lambda x: x["date"]):
        if e["date"] > today:
            break
        if not all(f"{e['date']}_{l}" in posted for l in ("ja", "en") if l in e):
            target = e
            break

    if target is None:
        print(f"投稿対象なし（today={today}）。queueが尽きた可能性があります。")
        return

    # 二重投稿ガード（ただし片方だけ投稿済みのエントリは、残りを完了させる）
    partial = any(f"{target['date']}_{l}" in posted for l in ("ja", "en") if l in target)
    last = posted.get("_last_post_at")
    if last and not partial:
        elapsed = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 3600
        if elapsed < MIN_HOURS_BETWEEN_POSTS:
            print(f"skip: {elapsed:.1f}時間前に投稿済み（{MIN_HOURS_BETWEEN_POSTS}時間以内）")
            return
    if partial:
        print(f"※ {target['date']} は片方のみ投稿済み。残りを投稿します")

    if target["date"] != today:
        print(f"※ {target['date']} の未投稿分を追いつき投稿します（today={today}）")

    failed = False
    for lang in ("ja", "en"):
        if lang not in target:
            continue
        key = f"{target['date']}_{lang}"
        if key in posted:
            print("already posted:", key)
            continue
        image_url = f"{base}/{target['date']}_{lang}.png"
        try:
            media_id = publish(ig_ids[lang], image_url, target[lang]["caption"], token)
            posted[key] = media_id
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
