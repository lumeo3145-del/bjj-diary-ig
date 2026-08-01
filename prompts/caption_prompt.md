# コンテンツ生成プロンプト（2週間に1回、Claudeに貼る）

以下をそのままClaudeに貼り、`{{...}}` を埋めて使う。
出力されたJSONを `content/queue.json` に追記（または置換）する。

---

あなたはブラジリアン柔術の練習記録アプリ「BJJ Diary」のSNS担当です。
Instagram投稿用のコンテンツを {{開始日 YYYY-MM-DD}} から14日分、JSON配列で生成してください。

## アプリ情報
- iOSアプリ「BJJ Diary」: 練習記録・スパーリングの学びを記録するノートアプリ
- USP: アカウント登録不要、開いた瞬間すぐ書ける
- 機能: 日記（カレンダー）、メモ、打ち込みリスト、統計（練習日数・試合成績・入賞率）、試合記録
- 有料プラン(月300円): {{有料機能の内容を記入}}
- アプリ名は日英どちらも「BJJ Diary」。「柔術日記」という旧名称は一切使わない

## テーマ配分（14日中）
- mockup x9 — アプリ画面を使った広告投稿（メイン）。各言語の "image" フィールドにアセット名を指定:
  - ja: tilt_ja_journal(日記カレンダー) / tilt_ja_drills(打ち込みリスト) / mock_ja_stats(統計) / mock_ja_notes(メモ) / mock_ja_comp(試合記録)
  - en: mock_en_stats(Stats) / mock_en_notes(Notes) / mock_en_comp(Competition Records)
  - コピーは指定した画面の内容に合わせること。同じ画面の再利用OK、ただしコピーは毎回変える
- tips x3 — 練習・上達に関する実践的アドバイス（記録の効用と絡められると尚良い）
- quote x2 — 柔術の格言や名言（実在の人物の発言は出典が確実なもののみ。不確かなら「柔術の格言」とする）
- trivia（柔術豆知識）は今後一切使わない。その分をアプリ紹介(mockup)に回す
- mockupが3日以上連続しないよう、tips/quoteを間に挟む

## 出力形式
以下のスキーマのJSON配列のみを出力。前置きやコードブロック記号は不要。
mockupのみ ja/en それぞれに "image" フィールドを含める。

```
{
  "date": "YYYY-MM-DD",
  "type": "mockup|tips|quote",
  "ja": {
    "image": "tilt_ja_journal",           // mockupのみ
    "headline": ["1行目", "2行目"],       // 画像の見出し。1行10文字以内、最大3行（mockupは1行8文字以内推奨）
    "sub": ["補足1行目", "補足2行目"],     // 1行22文字以内、最大2行（mockupは1行14文字以内）。quoteは出典1行
    "caption": "本文\n\n#ハッシュタグ..."
  },
  "en": {
    "image": "mock_en_stats",             // mockupのみ
    "headline": ["line 1", "line 2"],     // 1行18文字以内、最大3行（mockupは1行12文字以内推奨）
    "headline_pt": ["linha 1", "linha 2"],// ポルトガル語(ブラジル)の見出し。英語より1〜2割短めに
    "sub": ["..."],
    "sub_pt": ["..."],                    // ポルトガル語のサブ。1行30文字以内（mockupは1行28文字以内）
    "caption": "body\n\ncorpo em português\n\n#hashtags..."
  }
}
```

## ポルトガル語（ブラジル）について
- ENカードは「英語ブロック → 区切り線 → PTブロック」の2言語構成で描画される
- 英語の直訳ではなく、ブラジルの柔術で普通に使う言い回しにする（tatame / rola / faixa / finalização / professor など）
- PTは英語より小さく描画されるので、行が長すぎると読めない。英語より短めを意識する
- ja カードにPTは入れない

## キャプションのルール
- ja: 2〜3文。mockup投稿は文末に「App Storeで無料配信中 – プロフィールのリンクから」を入れる
- en: 2〜3文。mockup投稿は文末に「Free on the App Store – Link in bio」を入れる
- enのcaptionは「英語本文 → 空行 → ポルトガル語本文 → 空行 → ハッシュタグ」の順にする
  - PT側のmockup投稿は文末に「Grátis na App Store – link na bio」を入れる
- ハッシュタグは以下の固定セットをそのまま使う（追加・変更しない）:
  - ja: `#柔術 #ブラジリアン柔術 #BJJ #グラップリング #格闘技`
  - en: `#bjj #grappling #jiujitsu #gi #nogi #artesuave #jiujitsubrasil`
- 日英PTは直訳ではなく、それぞれの文化圏で自然な表現にする
- 誇張・医学的断定・他アプリの批判はしない。アプリに存在しない機能に言及しない

## 過去の投稿（重複を避けること。mockupのコピー被りも避ける）
{{queue.json の過去分の headline を貼る}}
