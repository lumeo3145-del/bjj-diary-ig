# -*- coding: utf-8 -*-
"""
長期アクセストークン（60日有効）を月1回リフレッシュする。
新トークンを標準出力に出し、GitHub Actions 側で gh secret set に渡す。

必要な環境変数:
  META_APP_ID
  META_APP_SECRET
  META_ACCESS_TOKEN  (現在の長期トークン)
"""
import json
import os
import sys
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


def main():
    params = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": os.environ["META_APP_ID"],
        "client_secret": os.environ["META_APP_SECRET"],
        "fb_exchange_token": os.environ["META_ACCESS_TOKEN"],
    })
    with urllib.request.urlopen(f"{GRAPH}/oauth/access_token?{params}") as res:
        data = json.loads(res.read())
    token = data.get("access_token")
    if not token:
        print("refresh failed:", data, file=sys.stderr)
        sys.exit(1)
    # トークンのみを出力（Actionsでマスクして受け取る）
    print(token)


if __name__ == "__main__":
    main()
