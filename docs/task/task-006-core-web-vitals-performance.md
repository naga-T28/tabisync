# Task 006: Core Web Vitalsとページ読み込み性能を改善する

- 種別: パフォーマンス / フロントエンド / Django
- 優先度: Medium
- 状態: 調査済み / 実装待ち
- 対象: 公開ページ（ホーム・作成・FAQ・規約・プロフィール・更新情報・お問い合わせ）およびしおり表示・編集画面の読み込み性能
- 対象外: サーバー・インフラ構成の変更（Task 008で扱う）、地図表示provider・AIコンシェルジュ機能自体の変更
- 調査基準日: 2026-08-13

## 目的

LCP・INP・CLSを実測したうえで、影響の大きい順に改善する。数値目標だけを掲げず、実際に不要な読み込みを減らし、画像・フォント・サードパーティスクリプトの扱いを見直す。

## 現状の具体的な課題（コード調査済み）

### 1. Flatpickrが全ページで読み込まれているが、どこにも実装がない

`base.html`・`base-noindex.html`・`tabisync/content/base.html`・`tabisync/list.html`・`tabisync/edit.html`・`tabisync/memo.html`・`tabisync/content.html`・`tabisync/content/concierge_v2.html`がFlatpickrのCSS（`cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css`）とJS本体（`cdn.jsdelivr.net/npm/flatpickr`）を読み込んでいる。一方、リポジトリ全体を検索しても`flatpickr(`という初期化呼び出しは1件も見つからない。日付入力は`tabisync/create.html`含め素の`<input type="date">`を使っている。

→ 現在Flatpickrは実質デッドコードとして、`base.html`を継承する全公開ページ（ホーム以外のほぼ全公開ページ）としおり表示・編集画面で読み込まれている疑いが強い。実際に未使用と確認できれば読み込みごと削除する。

### 2. ホームのヒーロー画像が実表示サイズよりはるかに大きい

`templates/home.html`の`<img src="{% static 'img/home-hero-product.webp' %}" ...>`（`class="home-hero-product-image"`）には`width`/`height`/`loading`/`fetchpriority`指定がなく、元ファイルは**4167×3125px、約153KB**。ホームのLCP候補である可能性が高いにもかかわらず、実際の表示幅（レイアウト上は数百px程度）に対して数倍の解像度で配信されている。

### 3. 未使用の可能性がある旧形式画像が残っている

`static/img/`配下に、WebP化されていないJPG/PNG/ICOが約12ファイル残っている（例: `create-body.jpg`（780KB）、`main-visu.jpg`（336KB）、`tabisync-ogp.png`（184KB）など、合計約2.2MB）。参照有無を個別に確認していない。

### 4. Google Fontsが2回に分けてリクエストされている

`base.html`・`base_home.html`・`base-noindex.html`のいずれも、`Source+Sans+Pro`と`Noto+Sans+JP`を別々の`<link>`（別々の`fonts.googleapis.com/css2?family=...`リクエスト）で読み込んでいる。1つのURLに`family`パラメータを2つ指定すれば、CSSリクエストは1回に減らせる。また`Noto+Sans+JP:wght@100..900`は可変フォントの全ウェイト範囲を指定しており、実際にCSSで使用しているフォントウェイトより広い可能性がある。

### 5. 画像の`width`/`height`・`loading`・`decoding`が体系的に設定されていない

ホーム以外のページ（プロフィール画像、404画像等）も含め、`<img>`タグに明示的な`width`/`height`が設定されておらず、CLSの要因になり得る。ファーストビュー外の画像に`loading="lazy"`も設定されていない。

### 6. 広告・GA4スクリプトは概ね`async`化済み

`base.html`のGoogle tag（gtag.js）とAdSense（adsbygoogle.js）はすでに`async`属性付きで読み込まれている。ここは大きな追加対応は不要だが、変更時に`async`/`defer`を外さないよう注意する。

## 実装タスク

### 計測（着手前に実施し、変更前の値を記録する）

- [ ] PageSpeed Insights（モバイル優先）でホーム・FAQ・作成画面・しおり表示画面（テスト用データ）のLCP・INP・CLSを計測し、日付・URL・数値を`docs/`配下に記録する。
- [ ] Chrome UX Report（CrUXが利用可能な場合）またはSearch Consoleの「ウェブに関する主な指標」で実ユーザーデータを確認する。

### Flatpickrの要否確認・削除

- [ ] `static/js/`および全テンプレートで`flatpickr(`呼び出しが本当に存在しないことを最終確認する。
- [ ] 未使用と確認できた場合、`base.html`・`base-noindex.html`・`tabisync/content/base.html`・`tabisync/list.html`・`tabisync/edit.html`・`tabisync/memo.html`・`tabisync/content.html`・`tabisync/content/concierge_v2.html`からFlatpickrのCSS/JSタグを削除する。
- [ ] 日付入力（`create.html`、しおり編集画面）が`<input type="date">`のみで問題なく動作することをモバイル・デスクトップ双方のブラウザで確認する。

### 画像最適化

- [ ] `home-hero-product.webp`を実表示サイズに合わせて再書き出しし（`srcset`/`sizes`も検討）、`width`・`height`を明示し、LCP画像として`fetchpriority="high"`を付与する。`<link rel="preload" as="image">`の追加も検討する。
- [ ] ファーストビュー外の`<img>`に`loading="lazy"`・`decoding="async"`を付与する。
- [ ] `static/img/`配下の未WebP画像（JPG/PNG/ICO）について、テンプレート・CSS・JSからの参照有無を`grep`で確認し、参照されているものはWebP化、参照されていないものは削除する。
- [ ] プロフィール画像・404画像など主要`<img>`に`width`/`height`を設定する。

### フォント・サードパーティ読み込みの整理

- [ ] `base.html`・`base_home.html`・`base-noindex.html`のGoogle Fonts読み込みを1つの`<link>`（`family=Source+Sans+Pro:...&family=Noto+Sans+JP:...&display=swap`）へ統合する。
- [ ] 実際にCSSで使用しているフォントウェイトを`static/scss/`から洗い出し、`Noto+Sans+JP`の指定ウェイト範囲を必要分に絞れないか検討する（自己ホストへの切替はライセンス・キャッシュ運用コストを踏まえて別途判断する）。
- [ ] Font Awesomeについて、実際に使用しているアイコンのサブセット化・自己ホスト化の要否を検討する（CDN継続の場合は現状維持で可）。

### レイアウトシフト対策

- [ ] 広告枠（AdSense）・地図コンテナに、読み込み前から確保される高さ・幅（CSSの`min-height`等）を設定し、CLSを抑える。
- [ ] `home.css`/`style.css`/`style_v2_1.css`をSCSSから再生成し、意図した差分のみになっていることを確認する。

### 静的配信の確認

- [ ] 本番相当環境でWhiteNoise（`CompressedManifestStaticFilesStorage`）が発行するレスポンスヘッダー（`Cache-Control`、`Content-Encoding: br`または`gzip`）を`curl -I`で確認する。Nginx側の設定変更が必要な場合はTask 008と合わせて扱う。

## 検証コマンド

```bash
cd project_tabisync
pipenv run python manage.py check
pipenv run python manage.py test tabisync
npx sass project_tabisync/static/scss:project_tabisync/static/css
```

```bash
# 本番相当環境でのキャッシュ・圧縮確認例
curl -I https://tabisync.com/static/css/style.css
```

手動確認:

- モバイル・デスクトップ双方の主要ページで、画像・フォント・広告読み込み後にレイアウトがガタつかないことを目視確認する。
- Flatpickr削除後、日付入力・既存の日程関連バリデーションに回帰がないことを手動確認する。

## 完了条件

- 変更前後のLCP・INP・CLSが記録され、少なくとも計測対象ページで数値悪化がない。
- 未使用と確認されたFlatpickrの読み込みが削除されている、または使用実態が確認され意図的に残す判断が記録されている。
- ホームのヒーロー画像を含む主要画像に適切な`width`/`height`・`loading`・`fetchpriority`が設定されている。
- Google Fontsのリクエストが重複なく統合されている。
- 参照されていない旧形式画像が整理されている、または参照調査の結果が記録されている。
- 既存機能（日付入力、地図表示、広告表示、しおり表示・編集）に回帰がない。

## 注意事項

- 画像・フォント・スクリプトの変更は、しおり表示・編集画面など実際の利用画面で必ず目視確認する。自動テストは表示崩れを検出できない。
- Flatpickr削除は「現時点で未使用」の確認が前提。将来的にカスタム日付ピッカーを導入する計画がある場合は、削除ではなく現状維持を選択する。
- 本タスクはTask 004で整備したcanonical・noindex制御・構造化データの挙動を変更しない。画像・スクリプトの変更がmeta情報やJSON-LDに影響しないことを確認する。
