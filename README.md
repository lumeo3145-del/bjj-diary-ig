# BJJ Diary Instagram 自動投稿

日英2アカウントに毎日 JST 21:00 に自動投稿するパイプライン。

## 仕組み

```
[2週間に1回・手動15分]
Claude にプロンプト → 14日分のJSON → queue.json に追記
python3 generate_cards.py → output/ に画像28枚
目視チェック → git push

[毎日・全自動]
GitHub Actions (21:00 JST) → Graph API で日英に1枚ずつ投稿
GitHub Actions (月1) → アクセストークン自動更新
```

## 初回セットアップ

### 1. Meta 側（所要 約1時間）

1. 両Instagramアカウントを **プロアカウント（クリエイター）** に切替
2. Facebookページを2つ作成し、各IGアカウントと連携
3. [Meta for Developers](https://developers.facebook.com/) でアプリ作成（タイプ: Business）
4. Graph API Explorer で以下の権限を付与してユーザートークンを取得
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `business_management`
5. 短期トークンを長期トークン（60日）に交換:
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={APP_ID}
     &client_secret={APP_SECRET}
     &fb_exchange_token={短期トークン}
   ```
6. IGビジネスアカウントIDを取得:
   ```
   GET /me/accounts                     → ページID一覧
   GET /{page-id}?fields=instagram_business_account
   ```
   日英それぞれのIDを控える。

### 2. GitHub 側

1. このリポジトリを **パブリック** で作成して push
   （raw.githubusercontent.com の画像URLを投稿に使うため。
   　非公開にしたい場合は Cloudflare R2 等に置き `IMAGE_BASE_URL` を変える）
2. Settings → Secrets and variables → Actions に登録:

   | Secret | 内容 |
   |---|---|
   | `META_ACCESS_TOKEN` | 長期アクセストークン |
   | `META_APP_ID` | Metaアプリ ID |
   | `META_APP_SECRET` | Metaアプリ シークレット |
   | `IG_USER_ID_JA` | 日本語アカウントのIGユーザーID |
   | `IG_USER_ID_EN` | 英語アカウントのIGユーザーID |
   | `GH_PAT` | secrets 書込権限付き Fine-grained PAT（トークン自動更新用） |

3. `generate_cards.py` の `HANDLES` を実際のハンドル名に修正

### 3. ローカル環境

```bash
pip install pillow
# フォント (Ubuntu)
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra
# macOS
brew install --cask font-noto-sans-cjk-jp font-noto-serif-cjk-jp
```

## 2週間ごとの運用（唯一の手作業・15〜30分）

1. `prompts/caption_prompt.md` を Claude に貼って14日分のJSONを生成
2. `content/queue.json` に追記
3. 画像生成と確認:
   ```bash
   python3 generate_cards.py
   open output/   # 目視チェック。直したい日は queue.json を編集して
   python3 generate_cards.py --only 2026-08-05   # 再生成
   ```
4. `git add . && git commit -m "content: 8月前半" && git push`

以降は毎日21:00に自動投稿される。

## 動作確認

初回は手動でテスト実行するのが安心:
Actions タブ → daily-post → Run workflow

## トラブルシューティング

- **queue が切れた**: 投稿はスキップされログに出るだけ。気づいたら補充
- **トークン失効**: refresh-token ワークフローが月1で更新。失敗時は
  Graph API Explorer で再取得して Secret を手動更新
- **投稿失敗**: Actions のログを確認。画像URLが404の場合は push 忘れ
- **APIレート制限**: 1アカウント24時間で50投稿まで。この構成(1日1枚)では問題なし

## 構成

```
├── content/
│   ├── queue.json        # 投稿キュー（Claudeで生成）
│   └── posted.json       # 投稿済み記録（自動更新）
├── output/               # 生成画像（コミットして公開URL化）
├── prompts/
│   └── caption_prompt.md # コンテンツ生成プロンプト
├── generate_cards.py     # JSON → カード画像
├── post_to_instagram.py  # Graph API 投稿
├── refresh_token.py      # トークン更新
└── .github/workflows/
    ├── post.yml          # 毎日 21:00 JST
    └── refresh-token.yml # 毎月1日
```
# bjj-diary-ig
