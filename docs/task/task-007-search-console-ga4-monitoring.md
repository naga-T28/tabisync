# Task 007: Search Console・Bing Webmaster Tools登録とGA4計測を整備する

- 種別: SEO運用 / 計測 / Django（GA4関連の最小限のコード対応を含む）
- 優先度: Medium
- 状態: 調査済み / 実装待ち
- 対象: 外部サービス（Google Search Console、Bing Webmaster Tools、GA4）への登録・設定と、それに伴う最小限のコード対応
- 対象外: 有料SEOツールの導入、広告運用の変更
- 調査基準日: 2026-08-13

## 前提

Task 004で`PUBLIC_BASE_URL`・`robots.txt`・サイトマップ（`https://tabisync.com/sitemap.xml`相当）・canonical・`X-Robots-Tag`が整備済みであること。本タスクはその上で、外部サービス側の登録と計測設定を行う。

**本タスクの大部分は本番ドメインの管理者権限・Google/Microsoftアカウントへのアクセスが必要で、Claude単独では実行できない。実行者（人）が外部サービス側の操作を行い、コード変更が必要な箇所（GA4のUUIDパス除外等）のみ実装を依頼する想定。**

## 現状の課題（コード調査済み）

### GA4タグが一部ページにしか設置されていない

`templates/base.html`にのみGoogle tag（gtag.js、測定ID`G-RPQJMFHLNC`）が設置されており、`templates/base_home.html`（ホーム）、`templates/base-noindex.html`（パスワード・リセット画面）、`templates/tabisync/content/base.html`（しおりV2表示・編集画面）にはgtagスニペットがない。

→ 現状、**ホームページの閲覧はGA4で計測されていない**可能性が高い（`base.html`を継承する作成・FAQ・規約・プロフィール・更新情報・お問い合わせ・404ページのみ計測されている）。これが意図した設計（プライバシー配慮でしおり画面を計測対象外にしている）なのか、単なる設置漏れなのかを最初に確認・決定する必要がある。

### UUID付きURLのGA4送信を防ぐ仕組みがない

現在、`gtag('config', 'G-RPQJMFHLNC')`はオプションなしで呼ばれており、Google Analyticsの自動ページビュー計測は`page_location`/`page_path`をそのまま送信する。仮に今後しおり表示・編集画面（`/content/v2/<pk>/<uuid>/...`等）にもGA4を設置する場合、UUIDを含む秘密URLがそのままGA4のイベントデータへ記録されてしまう。Task 004の方針（「検索結果・分析ツールへUUID付き秘密URLを渡さない」）と矛盾しないよう、設置前に対策を組み込む必要がある。

## 実装タスク

### Search Console（人による操作が中心）

- [ ] Google Search ConsoleでDomain property（`tabisync.com`）の所有権を確認する（DNS TXTレコード等、Task 008のDNS変更と合わせて実施すると効率的）。
- [ ] `https://tabisync.com/sitemap.xml`を送信する。
- [ ] URL検査ツールで、ホーム・FAQ・作成ページ・Task 005で追加した説明ページのcanonical・インデックス可否を確認する。
- [ ] 「クロール済み - インデックス未登録」「重複」「robots.txtによるブロック」「ソフト404」を月次で確認する運用を開始する（確認日・件数・対応内容を記録する場所を決める）。
- [ ] 検索クエリ・表示回数・クリック率・掲載順位を月次で記録する。

### Bing Webmaster Tools（人による操作が中心）

- [ ] Bing Webmaster Toolsにサイトを登録し、同じサイトマップを送信する。
- [ ] IndexNowの導入要否を検討する（更新頻度・運用負荷を踏まえて判断し、導入しない場合もその判断根拠を記録する）。

### GA4（コード対応 + 設定）

- [ ] ホームページにGA4を計測対象として含めるかどうかを決定する。含める場合は`templates/base_home.html`へgtagスニペットを追加する（`base.html`と重複する設定を1箇所にまとめる共通partial化も検討する）。
- [ ] しおり表示・編集画面（`templates/tabisync/content/base.html`、`templates/base-noindex.html`）にGA4を設置するかどうかを決定する。設置する場合は、`gtag('config', ...)`の`page_path`をUUID部分がマスクされた値（例: `/content/v2/[itinerary]/...`のような固定文字列）に上書きするコードを追加し、実際のUUIDがGA4へ送信されないことを確認する。設置しない選択肢（プライバシー優先で現状維持）も有効な判断とする。
- [ ] GA4側で、既存のUUID付きページパスがすでに蓄積されている場合は、データ保持設定・フィルタの要否をGA4管理画面で確認する。
- [ ] 本番リリース後、主要SNS（X等）のカードデバッガーでOGP表示を確認する。

### 継続運用の文書化

- [ ] SEO変更履歴（対象URL、変更内容、計測日、結果）を記録する場所を`docs/`配下に決める（例: `docs/seo/` ディレクトリを新設し月次ログを残す）。順位変動だけを理由に即時ロールバックしない運用方針をあわせて記載する。

## 検証コマンド・確認方法

```bash
curl -I https://tabisync.com/
curl https://tabisync.com/robots.txt
curl https://tabisync.com/sitemap.xml
```

- Search Console「URL検査」でホーム・FAQ・作成ページ・新規説明ページを個別に検査する。
- GA4のリアルタイムレポートで、ホーム・（設置する場合は）しおり表示画面のイベントが正しい`page_path`（UUIDがマスクされているか、そもそも送信されていないか）で届いていることを確認する。

UUID付きURLを確認する際は、実データのURLをログ・ドキュメント・外部検証サービスへ貼らない。ローカルまたは専用テストデータで確認する。

## 完了条件

- Search Console・Bing Webmaster Toolsへの登録とサイトマップ送信が完了している。
- GA4の計測範囲（ホーム・しおり画面を含めるか否か）が明示的に決定され、含める場合はUUIDがGA4へ送信されない実装になっている。
- 月次でインデックス状況・検索クエリ・Core Web Vitalsを確認する運用と記録場所が文書化されている。
- SEO変更履歴を記録する仕組みが用意されている。

## 注意事項

- 本タスクのDNS所有権確認・アカウント登録・サイトマップ送信は、本番ドメインの管理者権限が必要な操作であり、実行者（人）の承認と操作が前提となる。
- GA4の設定変更は、既存のアクセス解析データの連続性に影響する可能性があるため、変更前に現状の計測構成を記録しておく。
- UUID付きしおりを分析ツールの識別子・ディメンションとして送信しない方針（Task 004）を、GA4設定変更後も維持する。
