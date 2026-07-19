# -*- coding: utf-8 -*-
"""
今日の分を Instagram Graph API で日英2アカウントに投稿する。
GitHub Actions から毎日 JST 21:00 に実行される想定。

必要な環境変数:
  META_ACCESS_TOKEN  長期アクセストークン
  IG_USER_ID_JA      日本語アカウントのIGビジネスアカウントID
  IG_USER_ID_EN      英語アカウントのIGビジネスアカウントID
  IMAGE_BASE_URL     生成画像の公開URLベース
                     例: https://raw.githubusercontent.com/<user>/<repo>/main/output

投稿済み管理: content/posted.json に {"2026-08-01_ja": "media_id", ...}
"""
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
POSTED_PATH = "content/posted.json"


def api_post(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=data, method="POST")
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


def api_get(path, params):
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{GRAPH}/{path}?{qs}") as res:
        return json.loads(res.read())


def wait_ready(container_id, token, timeout=120):
    """コンテナの処理完了を待つ（画像は通常すぐ、動画対応も見据えて）"""
    for _ in range(timeout // 5):
        st = api_get(container_id, {"fields": "status_code", "access_token": token})
        if st.get("status_code") == "FINISHED":
            return True
        if st.get("status_code") == "ERROR":
            return False
        time.sleep(5)
    return False


def publish(ig_user_id, image_url, caption, token):
    c = api_post(f"{ig_user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    cid = c["id"]
    if not wait_ready(cid, token):
        raise RuntimeError(f"container not ready: {cid}")
    r = api_post(f"{ig_user_id}/media_publish", {
        "creation_id": cid,
        "access_token": token,
    })
    return r["id"]


def main():
    token = os.environ["META_ACCESS_TOKEN"]
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    ig_ids = {"ja": os.environ["IG_USER_ID_JA"], "en": os.environ["IG_USER_ID_EN"]}

    # JSTの今日
    today = (datetime.datetime.now(datetime.timezone.utc)
             + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")

    with open("content/queue.json", encoding="utf-8") as f:
        queue = json.load(f)
    posted = {}
    if os.path.exists(POSTED_PATH):
        with open(POSTED_PATH, encoding="utf-8") as f:
            posted = json.load(f)

    entry = next((e for e in queue if e["date"] == today), None)
    if entry is None:
        print(f"no entry for {today} — queue が切れています。補充してください。")
        return

    failed = False
    for lang in ("ja", "en"):
        key = f"{today}_{lang}"
        if key in posted:
            print("already posted:", key)
            continue
        if lang not in entry:
            continue
        image_url = f"{base}/{today}_{lang}.png"
        try:
            media_id = publish(ig_ids[lang], image_url, entry[lang]["caption"], token)
            posted[key] = media_id
            print("posted:", key, media_id)
        except Exception as e:
            failed = True
            print(f"FAILED {key}: {e}", file=sys.stderr)

    with open(POSTED_PATH, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
