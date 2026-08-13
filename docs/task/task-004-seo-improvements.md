# Task 004: 現行構成に合わせたSEO基盤と検索流入コンテンツを整備する

- 種別: SEO / Django / フロントエンド / 運用
- 優先度: High
- 状態: 調査済み / 実装待ち
- 対象: 公開ページ、クロール制御、サイトマップ、構造化データ、表示性能、検索計測
- 対象外: UUID付き旅行しおりの検索公開、V1機能の刷新、有料SEOツールの導入、ブログ本文の制作
- 調査基準日: 2026-08-13

## 目的

TabiSyncを「登録不要の旅行しおり」「旅行計画の共有」「AIによる旅行計画支援」を探す利用者に正しく届けるため、検索エンジンが公開ページを安全かつ一貫してクロール・評価できる状態を作る。

SEOのためにUUID付きしおりを公開コンテンツ化してはならない。検索流入はホーム、FAQ、更新情報、運営者情報、今後追加する説明・活用ページで獲得し、利用者が作成した旅程、編集画面、パスワード画面、リセットURL、AIコンシェルジュ画面は検索対象外のまま維持する。

## 現状整理

### 対応済みの項目

- `html lang="ja"`と日本語表示を設定している。
- `base.html`と`base_home.html`にtitle、meta description、canonical、OGP、X（Twitter）カードがある。
- ホーム、作成、FAQ、規約、プライバシーポリシー、プロフィール、更新情報、お問い合わせには固有メタ情報がある。
- ホームに`SoftwareApplication`、FAQに`FAQPage`、プロフィールに`Person`のJSON-LDがある。
- Django Sitemap Frameworkによる`sitemap.xml`がある。
- `robots.txt`でUUID付きしおりとリセット系URLをクロール対象外にしている。
- 主要なしおり表示・認証レスポンスでは`X-Robots-Tag: noindex, nofollow`を付け、テンプレートでも`noindex`を使用している。
- 公開ページからホーム、デモ、FAQ、ブログ、作成、お問い合わせ、運営者情報への内部リンクがある。
- 画像は一部WebP化され、主要ページでレスポンシブ表示されている。

### 現状の主な課題

1. `robots.txt`が`/content/`を拒否する一方、同じURL群に`noindex`を返している。クロールを拒否すると検索エンジンが`noindex`を確認できず、外部からURLが発見された場合にURLだけ残る可能性がある。
2. `robots.txt`に`sitemap.xml`の絶対URLがなく、末尾改行やレスポンス内容のテストもない。
3. canonicalとJSON-LDのURLが`request.scheme`と`request.get_host`に依存する。許可された別Host、ステージング、プロキシ設定の差によってcanonicalが分散する余地がある。
4. サイトマップにフォーム中心の`create`・`contact`と規約ページが含まれる一方、インデックス方針が文書化されていない。`lastmod`もない。
5. 404ページが通常の`base.html`を継承し、タイトルが「ホーム」で、明示的な`noindex`がない。お問い合わせ完了、オフライン画面も検索結果に必要なページではない。
6. デモ一式は`noindex`である。意図としては安全だが、検索流入向けの製品説明・利用例ページが別途ないため、具体的な検索意図を受け止めるページが少ない。
7. FAQなど一部の公開ページで視覚上の主見出しが`h2`から始まり、ページ単位の`h1`がない。
8. JSON-LD内のURLもHost依存で、画面本文と構造化データを二重管理している。FAQ更新時に内容がずれる可能性がある。
9. 公開ページ共通で外部フォント、Font Awesome、広告スクリプトを読み込み、`base.html`ではページによって不要なFlatpickrも読み込む。LCP、INP、CLSへの影響を実測していない。
10. 画像に`width`・`height`、優先度、遅延読み込みを体系的に設定しておらず、未使用の大きな画像も残っている。
11. Search Consoleでの所有権確認、サイトマップ送信、インデックス状況、検索クエリ、Core Web Vitalsの継続確認手順がリポジトリにない。

## インデックス方針

実装前に次の方針をテスト可能な一覧として固定する。

| URL種別 | 方針 | サイトマップ | 理由 |
| --- | --- | --- | --- |
| ホーム | `index, follow` | 含める | サービスの主ランディングページ |
| FAQ | `index, follow` | 含める | 利用前の検索意図に直接回答できる |
| 更新情報 | `index, follow` | 含める | サービスの継続性と更新内容を示す |
| 運営者プロフィール | `index, follow` | 含める | 運営主体と信頼性を示す |
| 利用規約・プライバシーポリシー・AI規約 | `index, follow` | 含める | 信頼性とサービス情報を示す。検索流入は主目的にしない |
| しおり作成 | 原則`index, follow` | 内容を拡充した場合のみ含める | フォームだけの薄いページにせず、作成手順と機能説明を本文に持たせる |
| お問い合わせ入力 | `index, follow`または`noindex, follow`を実装時に決定 | `index`の場合のみ含める | 検索価値が低いため、サイト名検索で必要かを基準に決める |
| お問い合わせ完了・オフライン・404 | `noindex, follow` | 含めない | 検索結果として価値がない |
| デモ | 当面`noindex, nofollow`を維持 | 含めない | 実しおりと似たUIの重複ページ群。流入用の説明ページを別途作る |
| UUID付きV1/V2しおり、メモ、リスト、地図、AI、編集 | `noindex, nofollow` | 含めない | ユーザー情報と秘密URLを検索公開しない |
| パスワード、リセット、QR、表紙画像、ブログ埋め込み | HTTPヘッダーで`noindex, nofollow` | 含めない | 認証・共有用の補助URLである |
| 管理画面、CKEditorエンドポイント | クロール拒否 | 含めない | 管理・内部機能である |

`robots.txt`はアクセス制御として扱わない。秘密性はUUID、パスワード、セッション認可で守る。検索結果から確実に除外すべきHTML・画像・補助レスポンスには`X-Robots-Tag`を返し、検索エンジンがその指示を取得できる構成にする。

## 実装タスク

### P0: クロール・canonical・非公開URLを正す

- [ ] `PUBLIC_BASE_URL`（例: `https://tabisync.com`）を設定へ追加し、canonical、OGP URL、JSON-LD URL、サイトマップ、`robots.txt`で同じ公開オリジンを使う。
- [ ] `PUBLIC_BASE_URL`は任意の非秘密環境変数として`AGENTS.md`またはREADMEへ記載し、本番では必須相当としてsystem checkまたはテストで不正値を検出する。
- [ ] HTTP→HTTPS、`www`有無、末尾スラッシュの正規URLを一つに決め、NginxまたはDjangoで1回の恒久リダイレクトに統一する。
- [ ] `robots.txt`に`Sitemap: https://tabisync.com/sitemap.xml`を追加し、`Content-Type: text/plain`、UTF-8、末尾改行を保証する。
- [ ] `robots.txt`の`Disallow: /content/`と`noindex`の競合を解消する。UUID付きURLが検索エンジンから取得可能な場合はクロールを許して`X-Robots-Tag`を認識させる。クロール拒否を残すURLは、管理・内部エンドポイントなど検索結果除外を`robots.txt`だけに依存しないものへ限定する。
- [ ] UUID付きV1/V2の全GET/POSTレスポンス、リダイレクト、403/404、QR画像、表紙画像、ブログ埋め込み、認証・リセット系へ一貫して`X-Robots-Tag: noindex, nofollow`が付くことをURL一覧ベースで監査する。
- [ ] `add_noindex_header()`など共通処理へ集約し、新規ビューで付け忘れにくい設計にする。
- [ ] 404、お問い合わせ完了、オフラインを`noindex, follow`にし、404は正しいHTTP 404と固有タイトルを返す。
- [ ] canonicalはクエリ文字列を除外し、公開ページだけに出力する。`noindex`の秘密URLにはcanonicalを付けて公開URLへ統合しようとしない。

### P0: サイトマップをインデックス方針と一致させる

- [ ] `StaticViewSitemap.items()`を上の方針表と一致させ、検索対象外ページを含めない。
- [ ] 更新情報には実データまたは管理可能な更新日から`lastmod`を返す。根拠のない現在時刻を毎回返さない。
- [ ] `changefreq`と`priority`は検索順位を上げる施策として過信せず、ページ特性に合わせるか省略する。
- [ ] サイトマップ内の全URLが公開canonicalと完全一致し、200を返し、リダイレクト・`noindex`・重複URLを含まないことをテストする。
- [ ] ステージングでは全ページを`noindex`とし、本番URLのサイトマップを生成・送信しない。

### P1: ページ単位のメタ情報とHTML構造を整える

- [ ] 公開ページごとに検索意図が重ならないtitleとmeta descriptionを定義する。ブランド名だけ、共通文言だけのページを残さない。
- [ ] titleは主要語を前方に置き、画面内容と一致させる。文字数で機械的に切らず、検索結果で意味が伝わる長さにする。
- [ ] OGP・Xカードのtitle、description、URL、画像をcanonicalと同期し、`og:locale=ja_JP`を追加する。
- [ ] OGP画像は絶対HTTPS URL、適切な縦横比と容量に統一し、可能なら`og:image:width`、`og:image:height`、`og:image:alt`も出力する。
- [ ] 各公開ページの本文主見出しを一つの`h1`にし、その下を`h2`、`h3`の順にする。ロゴをページの主見出しとして数えない。
- [ ] パンくずが利用者に有効な階層ページでは画面上のパンくずと`BreadcrumbList`を同じデータから生成する。
- [ ] 404テンプレートのtitleを「ページが見つかりません | TabiSync」へ変更し、本文にホーム・FAQへの復帰導線を置く。
- [ ] `base.html`と`base_home.html`のSEOブロック重複を共通partialまたは共通baseへ寄せ、修正漏れを防ぐ。

### P1: 構造化データを保守可能にする

- [ ] ホームの`SoftwareApplication`に使用実態と一致する情報だけを残し、公開canonical、ロゴ、運営者情報を共通設定から生成する。
- [ ] サイト全体の運営主体を示す`Organization`または`WebSite`をホームへ追加し、公式サイト・ブログ・公式Xの`sameAs`を実在URLに限定して設定する。
- [ ] FAQのJSON-LDと表示本文を同じPythonデータまたはテンプレートデータから生成し、質問・回答の不一致を防ぐ。
- [ ] FAQリッチリザルトの表示は保証されない前提とし、構造化データのためだけに本文を増やさない。
- [ ] JSON-LDへユーザー入力や秘密URLを入れない。Djangoの安全なJSON出力を使い、文字列連結でスクリプトを生成しない。
- [ ] Schema.org ValidatorとGoogle Rich Results Testで構文エラーがないことを確認する。

### P1: 検索意図を受け止める公開コンテンツを追加する

- [ ] ホームだけにキーワードを詰め込まず、次のテーマから需要と機能に合う独立ページを段階的に作る。
  - 登録不要で旅行しおりを作成・共有する方法
  - 友達・家族と旅行計画を共同編集する方法
  - 旅程、行きたい場所、持ち物、メモを一つにまとめる使い方
  - AIコンシェルジュを使った旅行計画の例と注意点
  - 旅行しおりのサンプルと作成手順
- [ ] 各ページは実機能、スクリーンショット、手順、制限、FAQ、作成CTAを持ち、他サイトの一般論を寄せ集めた薄いページにしない。
- [ ] デモそのものは`noindex`のまま、公開の「旅行しおりサンプル」説明ページからデモへ誘導する。
- [ ] ホーム、FAQ、説明ページ、作成画面、ブログを利用者の文脈に合うアンカーテキストで相互リンクする。
- [ ] ブログ側でもTabiSyncのcanonicalを誤設定せず、公式サービスへの関連リンクを設ける。サブドメインを含むサイト構成をSearch Consoleで管理する。
- [ ] 更新情報は日付、変更内容、対象機能が分かる本文を持たせ、ホームには直近数件だけを表示する。

### P2: Core Web Vitalsとクロール効率を改善する

- [ ] PageSpeed Insights、Chrome UX Report、Search Consoleでモバイルを優先してLCP、INP、CLSを計測し、変更前の値を記録する。
- [ ] ファーストビュー画像へ実寸に合う`width`・`height`、`srcset`・`sizes`を設定し、LCP画像だけ`fetchpriority="high"`と適切なpreloadを検討する。
- [ ] ファーストビュー外の画像へ`loading="lazy"`と`decoding="async"`を付ける。表示されない画像を先読みしない。
- [ ] 既存WebPの実表示サイズと容量を確認し、過大な画像を再圧縮する。元JPG/PNGが参照されていない場合は参照調査後に整理する。
- [ ] ページごとに不要なFlatpickr、地図、Font Awesome、広告スクリプトを読み込まない。必要なJavaScriptは`defer`または遅延初期化する。
- [ ] Google Fontsの重複リクエストを統合し、必要ウェイトだけに絞る。自己ホストはライセンス、キャッシュ、更新負担を確認して判断する。
- [ ] 広告枠・画像・地図に事前の表示領域を確保し、CLSを抑える。
- [ ] WhiteNoise/Nginxでハッシュ付き静的ファイルの長期キャッシュとBrotli/Gzipを確認する。
- [ ] HTML内の主要本文とリンクはJavaScript実行なしでも取得できる状態を維持する。

### P2: 信頼性・アクセシビリティを補強する

- [ ] 運営者、問い合わせ方法、利用規約、プライバシーポリシー、AI利用上の注意を全公開ページから到達可能にする。
- [ ] 機能や無料範囲、登録不要という表現を実際の仕様と一致させ、変更時にホーム・FAQ・構造化データを同時更新する。
- [ ] 意味のある画像には内容を説明するalt、装飾画像には空altを設定する。ロゴやスクリーンショットへ同じ曖昧なaltを繰り返さない。
- [ ] リンク文言を「こちら」だけにせず、遷移先が分かる文言にする。
- [ ] モバイルで本文、見出し、CTAが広告や固定UIに隠れず、キーボード操作とフォーカス表示が機能することを確認する。

### P3: Search Consoleと継続運用を整備する

- [ ] Google Search ConsoleでDomain propertyを確認し、`https://tabisync.com/sitemap.xml`を送信する。
- [ ] Bing Webmaster Toolsにもサイトマップを送信する。必要性を確認したうえでIndexNowを検討する。
- [ ] URL検査でホーム、FAQ、作成ページ、説明ページのcanonical・インデックス可否を確認する。
- [ ] 「クロール済み - インデックス未登録」「重複」「robots.txtによるブロック」「ソフト404」を月次確認する。
- [ ] 検索クエリ、表示回数、クリック率、掲載順位、検索流入後の作成完了を月次で記録する。
- [ ] GA4には秘密URLやUUIDをページ名・イベント値として送らない。UUID付きパスは集約または除外する。
- [ ] 本番リリース後に主要SNSのカードデバッガーでOGP表示を確認する。
- [ ] SEO変更履歴、計測日、対象URL、結果を`docs/`配下へ残し、順位変動だけで即時ロールバックしない。

## 主な変更対象候補

- `project_tabisync/project_tabisync/settings.py`
- `project_tabisync/project_tabisync/context_processors.py`
- `project_tabisync/project_tabisync/urls.py`
- `project_tabisync/tabisync/sitemaps.py`
- `project_tabisync/tabisync/views/utils.py`
- `project_tabisync/tabisync/views/access_control.py`
- `project_tabisync/tabisync/urls.py`
- `project_tabisync/templates/base.html`
- `project_tabisync/templates/base_home.html`
- `project_tabisync/templates/base-noindex.html`
- `project_tabisync/templates/home.html`
- `project_tabisync/templates/404.html`
- `project_tabisync/templates/docs/`
- `project_tabisync/templates/contact/`
- `project_tabisync/templates/tabisync/create.html`
- `project_tabisync/templates/demo/`
- `project_tabisync/static/img/`
- `project_tabisync/tabisync/tests/test_static_pages.py`
- URL別のインデックス制御を検証する既存viewテスト

## テスト要件

- [ ] 公開対象URLは200、自己参照canonical、固有title、固有descriptionを持つ。
- [ ] 非公開・補助URLは正常系、認証要求、エラー、リダイレクトの各経路で`X-Robots-Tag`を持つ。
- [ ] 404は404を返し、`noindex`を持つ。
- [ ] `robots.txt`は200、`text/plain`で、公開サイトマップURLを1件だけ含む。
- [ ] サイトマップの各URLは公開オリジンを使い、200・index可能・canonical一致である。
- [ ] JSON-LDをJSONとしてparseでき、画面本文とFAQデータが一致する。
- [ ] Hostヘッダーやクエリ文字列を変えてもcanonicalが意図しないHost・URLへ変化しない。
- [ ] ステージング設定ではインデックス許可レスポンスを返さない。
- [ ] 既存のしおり閲覧・編集認可、UUIDトークン、パスワード、セッション制御に回帰がない。

最低限、次を実行する。

```bash
cd project_tabisync
pipenv run python manage.py check
pipenv run python manage.py test tabisync.tests.test_static_pages
pipenv run python manage.py test tabisync
```

本番相当環境では次も手動確認する。

```bash
curl -I https://tabisync.com/
curl -I https://tabisync.com/存在しないパス/
curl https://tabisync.com/robots.txt
curl https://tabisync.com/sitemap.xml
```

UUID付きURLを確認するときは実データのURLをログ、ドキュメント、外部検証サービスへ貼らない。ローカルまたは専用テストデータで確認する。

## 完了条件

- 公開対象、非公開対象、サイトマップ掲載対象が方針表とテストで一致している。
- canonical、OGP、JSON-LD、サイトマップが本番の単一HTTPSオリジンを参照する。
- UUID付きしおりと認証・編集・補助URLが検索結果に登録されない設計になっている。
- 404、完了画面、オフライン画面が検索対象外になっている。
- 公開ページに固有のtitle、description、h1、適切な内部リンクがある。
- 構造化データが表示本文と一致し、検証ツールで重大エラーがない。
- モバイルのCore Web Vitalsを計測し、少なくとも変更前後の値と残課題が記録されている。
- Search Consoleへサイトマップを送信し、月次確認手順と成果指標が文書化されている。
- SEO対応によって認可、秘密URL、ユーザーデータ保護を弱めていない。

## 推奨実施順

1. インデックス方針と`PUBLIC_BASE_URL`を確定する。
2. `X-Robots-Tag`、`robots.txt`、404、サイトマップ、canonicalを修正し、自動テストを追加する。
3. 公開ページのtitle、description、h1、OGP、JSON-LDを共通化・整合させる。
4. 検索意図別の説明ページを1ページずつ追加し、Search Consoleの実績で次のテーマを決める。
5. PageSpeed Insightsと実ユーザーデータを基に、LCP・INP・CLSへ影響の大きい順で改善する。
6. リリース後にインデックス状況、検索流入、作成完了率を継続計測する。

## 注意事項

- `robots.txt`、meta robots、`X-Robots-Tag`は認証・アクセス制御の代替ではない。
- UUID付きしおりをSEO用の公開UGCとして流用しない。将来公開しおり機能を作る場合は、本人の明示的な公開設定、別公開トークン、削除・非公開化、個人情報対策、スパム対策、モデレーションを別タスクで設計する。
- キーワード出現回数、サイトマップの`priority`、構造化データの追加だけを成果としない。検索意図に合う本文、クロール可能性、速度、安全性、利用後の作成完了を合わせて評価する。
- 外部サービス上の設定変更、Search Console登録、DNS変更、Nginxリダイレクト変更は、本番権限と明示的な承認を得て実施する。
