# Task 005: 検索意図別の説明・活用ページを追加する

- 種別: SEO / コンテンツ制作 / Django / フロントエンド
- 優先度: Medium
- 状態: 調査済み / 実装待ち
- 対象: 検索流入獲得を目的とした新規公開ページの追加
- 前提: Task 004（クロール制御・canonical・サイトマップ・構造化データの基盤整備）が完了していること
- 対象外: UUID付き旅行しおりの検索公開、ブログ（blog.tabisync.com）本文の制作、有料広告・SEOツールの導入

## 目的

ホーム1ページに検索キーワードを詰め込むのではなく、利用者が実際に検索しそうな意図ごとに専用ページを用意し、それぞれで具体的な機能・手順・制限・FAQ・CTAを提示する。Task 004で整備したcanonical・OGP・構造化データ・サイトマップの仕組みにそのまま乗せられる状態にする。

## 前提として使える基盤（Task 004で整備済み）

- `PUBLIC_BASE_URL`とcontext processor `public_base_url`により、canonical・OGP・JSON-LDが単一の公開オリジンを参照する。
- `base.html`に`{% block robots_meta %}`（既定`index, follow`）があり、新規ページはそのまま`index, follow`になる。
- `base.html`/`base_home.html`に`title`、`meta_description`、`og_title`、`og_description`、`og_image`、`twitter_*`の各blockがあり、ページごとに上書きできる。
- `tabisync/seo.py`の`dumps_json_ld()`で、文字列連結せずに安全な構造化データを出力できる（`BreadcrumbList`等を追加する際に利用する）。
- `tabisync/sitemaps.py`の`SITEMAP_URL_NAMES`にURL名を追加すれば、そのままサイトマップへ載る。
- 見出し階層のルール（ページ本文に`h1`を1つ、以下`h2`/`h3`）が`docs/`配下の既存ページで確立済み。同じパターンに従う。

## 現状の課題

- ホームページに機能紹介が集約されており、検索意図（「登録不要」「共同編集」「AIコンシェルジュの使い方」等）ごとの着地点がない。
- `create`（しおり作成フォーム）はフォームのみで本文が薄く、Task 004時点でサイトマップからも除外している。内容を拡充すれば`index`のままサイトマップにも戻せる。
- デモ（`/demo/v2/...`）は`noindex, nofollow`のまま維持する方針（Task 004で確定済み）だが、そこへ誘導する公開ページがない。

## 追加するページ（優先順）

Task 004の調査で挙がった5テーマを、需要と実装コストを見ながら1ページずつ追加する。

1. 旅行しおりのサンプルと作成手順（デモへの入口を兼ねる。最優先）
2. 登録不要で旅行しおりを作成・共有する方法
3. 友達・家族と旅行計画を共同編集する方法
4. 旅程・行きたい場所・持ち物・メモを一つにまとめる使い方
5. AIコンシェルジュを使った旅行計画の例と注意点

各ページは独立URLとし、無理に1本へ統合しない。ただしテーマ間で内容が重複しすぎないよう、各ページの主眼を上記の見出しに絞る。

## ページ要件（共通）

- 本文は実機能の説明・実際の操作手順・スクリーンショット（または既存デモへのリンク）・制限事項・FAQ・作成導線（CTA）を含み、他サイトの一般論を並べただけの薄いページにしない。
- `h1`はそのページの検索意図と一致させ、`title`・`meta description`はホームや他の新規ページと重複しない固有の文言にする。
- OGP画像は既存の`tabisync-v2-ogp.webp`を流用するか、ページ内容に合わせた新規画像を用意する（`og:image:width`/`height`/`alt`は`base.html`の`og_image`系blockで上書きする）。
- 本文中でホーム・FAQ・しおり作成・デモ・関連する他の新規ページへ、内容が分かるアンカーテキストで内部リンクする（「こちら」のみのリンクにしない）。
- デモへ誘導する場合は、デモが`noindex`であることを変更せず、リンク元の公開ページ側で実際の見た目やサンプルを説明する。
- 公開が決まったページは`tabisync/sitemaps.py`の`SITEMAP_URL_NAMES`へURL名を追加する。

## しおり作成ページの扱い

- Task 004の方針表どおり、`create`は「内容を拡充した場合のみ」サイトマップに含める。本タスクで作成手順・機能説明などフォーム以外の本文を追加した場合は、`SITEMAP_URL_NAMES`へ`tabisync:create`を追加する。
- フォームより上または下に、手順・注意事項（パスワード設定の意味、日程上限日数、共有方法など）を追記する。既存の入力仕様と矛盾する説明を書かない。

## 実装タスク

- [ ] 各ページのURL・view・templateを追加する（例: `tabisync/views/static_pages.py`へ`TemplateView`を追加し、`tabisync/urls.py`へ`path()`を追加する）。
- [ ] `base.html`を継承し、`title`/`meta_description`/`og_*`/`twitter_*`をページごとに固有の文言で上書きする。
- [ ] 本文に`h1`を1つ設置し、以降`h2`/`h3`で構成する。
- [ ] 本文中にホーム・FAQ・しおり作成・デモ・関連ページへの内部リンクを設置する。
- [ ] 公開が決まったページを`tabisync/sitemaps.py`の`SITEMAP_URL_NAMES`へ追加する。
- [ ] 必要に応じてパンくずリストを表示し、`dumps_json_ld()`で`BreadcrumbList`を画面表示と同じデータから生成する。
- [ ] `templates/base.html`または各ページのnav/footerから新規ページへのリンクを追加し、孤立ページ（他ページからリンクされないページ）を作らない。
- [ ] `tabisync/tests/test_static_pages.py`の`PUBLIC_URL_NAMES`（および必要なら`SITEMAP_URL_NAMES`比較用のリスト）へ新規ページを追加する。

## テスト要件

- [ ] 各新規ページが200を返し、自己参照canonical・固有title・固有descriptionを持つ（`tabisync/tests/test_static_pages.py`の既存テストパターンに準拠）。
- [ ] `h1`が1つだけ存在する。
- [ ] サイトマップに追加したページが`tabisync/tests/test_static_pages.py`の`SitemapTests`で200・canonical一致であることを確認する。
- [ ] 内部リンク先URLが`{% url %}`で解決でき、404にならない。
- [ ] JSON-LDを追加した場合はJSONとしてparseできる。

```bash
cd project_tabisync
pipenv run python manage.py check
pipenv run python manage.py test tabisync.tests.test_static_pages
pipenv run python manage.py test tabisync
```

## 完了条件

- 優先度1位（しおりサンプル・作成手順ページ）が公開され、デモへの導線として機能している。
- 追加した各ページが、薄いページではなく実機能・手順・FAQ・CTAを備えている。
- Task 004で整備したcanonical・OGP・構造化データ・サイトマップの仕組みに矛盾なく統合されている。
- ホーム・FAQ・作成画面・デモとの相互リンクが構築されている。
- 自動テストが追加ページを含めて成功する。

## 注意事項

- ページ追加はキーワード数や本数を目標にしない。各ページが独自の検索意図に答えているかを基準に取捨選択する。
- 公開後はTask 007（Search Console運用）でインデックス状況・検索クエリを確認し、成果の薄いページは内容拡充または統合を検討する。
- UUID付きしおりを公開コンテンツ・サンプルとして流用しない。スクリーンショットや例示データは実データを使わず、ダミーデータまたはデモ画面を使用する。
