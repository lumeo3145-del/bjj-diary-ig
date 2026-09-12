# -*- coding: utf-8 -*-
"""
投稿キューの残量を調べる。

queue が尽きても post_to_instagram.py は正常終了するため、
Actions は成功のまま静かにスキップし続ける。それに気づけるようにするのが目的。

残量 = queue のうち「今日以降の日付」かつ「まだ未投稿の言語が残っている」日数。
これが QUEUE_WARN_DAYS 以下なら low=true を出力する（通知はワークフロー側の責務）。

環境変数:
  QUEUE_WARN_DAYS  警告しきい値（既定: 3）
出力（GITHUB_OUTPUT があれば書き込む）:
  remaining / low / last_date
low のときは Issue本文を queue_alert.md に書き出す（ワークフローが --body-file で使う）。
"""
import datetime
import json
import os

QUEUE_PATH = "content/queue.json"
POSTED_PATH = "content/posted.json"
LANGS = ("ja", "en")
DEFAULT_WARN_DAYS = 3


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def warn_days():
    raw = os.environ.get("QUEUE_WARN_DAYS", "")
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_WARN_DAYS


def remaining_dates(queue, posted, today):
    """今日以降で、まだ投稿しきっていない日付を古い順に返す"""
    return [
        e["date"]
        for e in sorted(queue, key=lambda x: x["date"])
        if e["date"] >= today
        and any(l in e and f"{e['date']}_{l}" not in posted for l in LANGS)
    ]


ALERT_PATH = "queue_alert.md"

ALERT_TEMPLATE = """投稿キューの残りが **{remaining}日分** になりました。{tail}

補充しないと、この日以降の投稿は Actions 上では成功扱いのまま静かにスキップされます。

## 補充手順

1. `prompts/caption_prompt.md` を Claude に貼って14日分を生成
2. `content/queue.json` に追記
3. `./.venv/bin/python generate_cards.py` で画像生成 → `output/` を目視チェック
4. commit & push

補充して残量がしきい値（{threshold}日）を超えると、このIssueは自動でクローズされます。
"""


def write_alert(remaining, last_date, threshold):
    tail = f"最終日は `{last_date}` です。" if last_date else "キューは既に尽きています。"
    with open(ALERT_PATH, "w", encoding="utf-8") as f:
        f.write(ALERT_TEMPLATE.format(remaining=remaining, tail=tail, threshold=threshold))


def emit(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for k, v in values.items():
            f.write(f"{k}={v}\n")


def main():
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    queue = load_json(QUEUE_PATH, [])
    posted = load_json(POSTED_PATH, {})

    dates = remaining_dates(queue, posted, today)
    remaining = len(dates)
    threshold = warn_days()
    low = remaining <= threshold
    last_date = dates[-1] if dates else ""

    print(f"キュー残り: {remaining}日分（today={today} UTC基準、しきい値={threshold}日）")
    if dates:
        print(f"次に投稿: {dates[0]} / 最終日: {last_date}")
    else:
        print("キューが尽きています。補充しないと投稿は止まったままです。")

    if low:
        print("::warning::投稿キューの残りが少なくなっています。queue.json を補充してください")
        write_alert(remaining, last_date, threshold)

    emit(remaining=remaining, low=str(low).lower(), last_date=last_date)


if __name__ == "__main__":
    main()
