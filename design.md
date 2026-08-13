# Design — TabiSync

ロックされたデザインシステム。テンプレート・SCSSを変更する前に必ずこのファイルを読むこと。
ブランドカラーは `static/img/icon-tabisync.png`（メインロゴのグラデーション）と
`static/img/logo-ai-concierge.png`（AIコンシェルジュ副ロゴ）から実ピクセルをサンプリングし、
OKLCHへ変換して抽出した（推測値ではない。手法は本ファイル末尾「カラー抽出ログ」参照）。
構造・タイポグラフィ・モーションの一部原則は、外部サイトのDNA研究（下記「Provenance」参照）を
参考にしている。色・ロゴ・写真・コピーはこの研究から一切採用していない。

## 適用範囲（現時点）

- **実装済み**: `templates/home.html`（`hallmark redesign` で再実装。旧実装は
  ローカルSCSS変数・box-shadow・グラスモーフィズムCTA・font-weight:950等
  design.mdトークン未使用のまま「実装済み」と記載されていた状態だったため、
  `home/_lp.scss` / `home/_header.scss` を全面的にトークンへ移行し、ヘアライン
  ボーダーのみのSurfaceルールとウェイト対比タイポグラフィを適用した）,
  `templates/base_home.html`, `templates/base.html`,
  `templates/docs/guide_sample.html`, `templates/docs/guide_no_signup.html`,
  `templates/docs/guide_collaboration.html`, `templates/docs/guide_all_in_one.html`,
  `templates/docs/guide_ai_concierge.html`。フッターは `templates/_site_footer.html`
  ＋ `layout/_site-footer.scss` を base.html / base_home.html の両方に実際に
  `{% include %}` して統合済み（旧実装はファイルだけ存在し、どちらのテンプレートも
  読み込んでいなかった）。
- **Phase 1（hallmark redesign ./templates/ で実施・実装済み）**: `templates/docs/qanda.html`,
  `templates/docs/update.html`, `templates/docs/profile.html`,
  `templates/docs/user_agreement.html`, `templates/docs/privacy_policy.html`,
  `templates/docs/concierge_terms.html`, `templates/contact/contact_form.html`,
  `templates/contact/thanks.html`, `templates/tabisync/create.html`, `templates/404.html`。
  見出し（`.user-agreement-title`/`.user-agreement-sub-title`）・FAQアコーディオン
  （`.qa-6`）・404・バージョン履歴・プロフィール・お問い合わせフォームをLong Document
  ファミリーのトークン（フォント・色・余白・pill CTA・ヘアラインボーダーのみのSurface
  ルール）へ移行した。フォーム入力欄（`.input-*`, `.enter-input-btn`,
  `.schedules-container`等）はV1レガシー/V2アプリ本体と共有のため今回は変更していない
  （Phase 2/4で対応）。あわせて `style.scss` / `home.scss` に `base/tokens` が、
  `style.scss` に `pages/docs` が未importだったビルド上の欠落を修正し、design.mdの
  トークンが実際にコンパイル・配信されるようにした。`::selection` のハードコード値
  （`#6B2AC0`）も `--color-accent` へ統合済み（本ファイルの「カラー抽出ログ」の記述と
  実装を一致させた）。
- **未着手（将来のラウンド）**: V2しおりアプリ本体（`templates/tabisync/content/*.html`,
  `templates/demo/v2_*.html`）、V1レガシー（`templates/tabisync/{content,list,memo,edit,password,...}.html`）。
  対象になった際は本ファイルへ「アプリ本体」ファミリーを追記してから着手する。本ラウンドで
  追加した「しおりの折り角」「ルートライン・ドローイン」「AIプログレスリング」（後述）は
  この未着手範囲への適用を前提にドキュメント化したものであり、現行の実装済みページには
  影響しない。

## Provenance（DNA研究の記録）

- **研究対象**: `https://partners-re.co.jp/`（不動産・投資会社の公開コーポレートサイト。
  TabiSyncと資本・ブランド上の関係はない第三者サイトで、構造原則の参考としてのみ使用した
  公開参照）
- **抽出方法**: 公開HTML/CSSの技術的事実（フォント宣言、spacing/radius/color値、
  アニメーション定義、DOM構造）を直接取得して分析した。ロゴ・写真・コピー・固有ブランド
  カラーは非採用。
- **採用したのは「原則」のみ**:
  - ヘアラインボーダーのみで面を分離するdepthモデル（box-shadowを使わない）
  - 単一基準値からの倍数展開によるスペーシング設計
  - 線描画リビール（罫線が伸びるアニメーション）
  - 線形・オーバーシュートなしのイージング
  - 「軽い極大 × 太い極小」のウェイト対比によるタイポグラフィ階層
  - 単一アクセント色を極小面積（罫線・ボタン・リンクのみ）に限定する運用規律
  - セクションごとに異なる非対称グリッド比率を与える構成原則
- **明示的に却下したもの**:
  - partners固有の青系アクセント色 → TabiSync既存の紫/オレンジ/ネイビーをそのまま使用
  - グラデーションCTAボタン → 本ファイルの既存禁止ルールを継続
  - 6〜8項目のメガドロップダウンナビ → TabiSyncのIAはこの複雑さを必要としないため不採用
  - 写真主体のヒーロー方針 → TabiSyncは実プロダクト画面（旅程表・地図）をヒーローに使う
    既存方針を継続。ストックフォト的な写真ヒーローには転換しない

## Genre
editorial

## Macrostructure family

- **マーケティングページ**（home.html）: Workbench — 実際の旅程表＋地図のプロダクト画面
  （`static/img/home-hero-product.webp`）をヒーローに据える。新規モックアップ画像は作らない。
  加えて、**セクションごとに異なる非対称比率を与える**原則を採用する（全セクションを同じ
  50/50分割の繰り返しにしない）。例: サービス紹介は均一カードグリッド、実績・特徴紹介は
  非対称2カラム、というように内容の性質に応じて比率を変える。
- **コンテンツ/ドキュメントページ**（docs/*.html）: Long Document — ガイド・FAQ・規約・
  プロフィール・更新履歴は読み物として組む。プロースの計測幅（measure）を守り、
  マーケティング的な装飾は最小限。
- **アプリ本体**（未着手）: 「旅程キャンバス」— LPマクロストラクチャーの型を使わず、
  既存のサイドレール/下部タブ構造を維持したまま機能画面ごとにレイアウト原則を適用する
  （旅程表=非対称2カラム、地図=空間型、AIコンシェルジュ=ドック型、リスト=単一カラム）。
  非対称2カラムの比率は旅程表とその日の地図プレビューの情報量に応じて可変とし、常に
  同じ比率を強制しない。着手時に本セクションへ詳細を追記する。

## Color System

3アクセント制。すべて実ロゴ画像からのサンプリング値に基づく（サンプリング手法は末尾参照）。

### ニュートラル（白基調・微暖色バイアス）
```
--color-paper:    oklch(99% 0.004 75)   背景（白基調、ごくわずかな暖色トーン）
--color-paper-2:  oklch(97% 0.006 75)   カード面
--color-paper-3:  oklch(94% 0.008 75)   ホバー/押下面
--color-ink:      oklch(23% 0.018 50)   本文・見出し
--color-ink-2:    oklch(46% 0.022 50)   補助テキスト
--color-ink-3:    oklch(66% 0.018 50)   プレースホルダー/最弱テキスト
--color-rule:     oklch(89% 0.010 75)   罫線
```

背景は白基調（`--color-paper`）を採用。純白 `#fff` ではなく、彩度をごくわずかに残すことで
「無機質なSaaSテンプレート」の白ではなく「選び取られたニュートラル」として機能させている
（彩度ゼロの純白/純黒を避けるeditorial genreの原則を、白基調の要望に合わせて低彩度側に
振り切って適用）。

### ブランドアクセント（3アンカー）
```
--color-accent:        oklch(55% 0.230 324)  主要CTA・アクティブ状態（人間の操作）
--color-accent-strong:  oklch(48% 0.220 322)  hover/pressed
--color-accent-ink:     oklch(98% 0.012 324)  アクセント上の文字

--color-accent-ai:      oklch(33% 0.150 271)  AIコンシェルジュ専用
--color-accent-ai-ink:  oklch(97% 0.010 271)  accent-ai上の文字

--color-accent-warm:    oklch(76% 0.140 56)   ワクワク感の一瞬の強調専用
--color-accent-warm-ink: oklch(24% 0.040 56)  accent-warm上の文字（濃色地に使う場合）

--color-focus:          oklch(62% 0.200 324)  フォーカスリング
```

**由来**: `--color-accent` はメインロゴ左上（紫）を実測した値そのもの（既存実装の
`#AF29BB` と一致 — 継続性を最優先し、既存の完全一致値を採用）。`--color-accent-warm` は
同じメインロゴの右下（オレンジ）の実測値。両者は色相324°→56°の暖色側の弧（紫→ピンク→
オレンジ、ロゴのグラデーションと同じ経路）でつながっており、単独で使っても「同じ
グラデーションの一部」と感じられる関係にある。`--color-accent-ai` はAIコンシェルジュ
副ロゴのネイビー実測値で、色相271°（寒色側）にあり、上記の暖色弧とは意図的に対極にある
— 「TabiSyncの温かさ」と「AIの技術感」を色相で切り分けるための、ロゴに基づく必然的な
選択。**グラデーションのCSS表現（linear-gradient等）としての多用はしない**。3色は
それぞれ単色のアクセントとして、用途ごとに独立して使う。

**運用ルールの明文化（DNA研究による補強）**: partners-re.co.jpは単一アクセント色を罫線・
ボタン・リンクにのみ使い、背景を塗らないという規律で「未来的だが押しつけがましくない」
印象を作っていた。これはTabiSyncが既に持つ「`--color-accent`の面積は各ビューポートの
3〜5%以内」というルールと完全に一致する。既存ルールを変更する必要はなく、継続の妥当性が
外部研究で裏付けられた、という位置づけである。3アンカー体制は「友達との共同計画」と
「AIによる旅行支援」を色相で切り分ける役割も果たす:

- **紫（accent）**: ユーザー本人・友達の操作全般（旅程の追加・編集、招待、共有）
- **ネイビー（accent-ai）**: AIコンシェルジュが発話・提案・生成している状態全般
- **オレンジ（accent-warm）**: 「共有が完了した」「AIの提案が届いた」など、一瞬だけ
  祝福する通知的強調

### セマンティック
```
--color-success:  oklch(58% 0.110 150)
--color-warning:  oklch(78% 0.130 85)
--color-error:    oklch(55% 0.180 27)   既存 rgb(208,0,0) を紙面のトーンに合わせて減彩
```

### 使用ルール
- `--color-accent` の面積は各ビューポートの3〜5%以内。塗りは主要CTA・アクティブ状態・
  フォーカスリングのみ。
- `--color-accent-warm` は装飾的な面塗りに使わない。優先度★、Today強調、共有完了直後の
  フィードバックなど「一瞬の強調」専用。1画面につき1〜2箇所まで。
- `--color-accent-ai` はAIコンシェルジュに関わるUI（アイコン・送信ボタン・チャット発言者
  ラベル等）専用。汎用リンク色としても使ってよい。
- Schedule カテゴリ色（食事・移動・宿泊・ショッピング・イベント・フラグ等）とDay別
  マーカー色（`want_list.html` の `getDayColor()`）は本システムの対象外。色相そのまま
  維持する（V2アプリ本体は本ラウンドの対象外のため）。
- グラデーション背景・グラデーションボタンは使用しない（ロゴ自体のグラデーションは
  画像としてそのまま維持する）。

## Typography System

- **Display**: Kaisei Tokumin, weight 500/700, style normal — 見出し・ヒーローコピー・
  ガイド大見出し。UIラベル・ボタン・フォーム項目・段落本文には使わない。
- **Body**: Zen Kaku Gothic New, weight 400/500/700 — 本文・UI文言。フォールバック:
  Hiragino Kaku Gothic ProN → Yu Gothic → Noto Sans JP。
- **Mono（アウトライヤー）**: Space Mono, weight 400/700 — フッターワードマーク、
  パンくずの区切り、日付・カウンター等の小さなデータ表示にのみ使用。
- Source Sans Proは削除（未使用の死荷重）。Noto Sans JP読み込みはV1/create.html互換の
  ため維持。

```
--text-xs:  0.75rem;   --text-sm:  0.875rem;  --text-base: 1rem;
--text-md:  1.125rem;  --text-lg:  1.375rem;  --text-xl:  1.75rem;
--text-2xl: 2.25rem;   --text-3xl: 2.75rem;
--text-display:   clamp(2.15rem, 3.2vw + 1rem, 3.4rem);
--text-display-s: clamp(1.75rem, 2vw + 1rem, 2.35rem);
```

### ウェイト対比によるタイポグラフィ階層（DNA研究による追加原則）

partners-re.co.jpは「大きい要素ほど軽いウェイト、小さい要素ほど太いウェイト」という
両極対比だけで階層を作っていた（中間ウェイトは本文にしか使わない）。この原則を
Kaisei Tokumin / Zen Kaku Gothic New の既存フォントの範囲内で採用する。

- **旅程・トリップのタイトル**（`--text-display`クラス）: Kaisei Tokumin **weight 500**
  （既存の700寄せをやめ、軽い方に統一）— 旅の名前は宣言的に太くするより、静かに大きく
  見せる方が「しおり」らしい
- **メタ情報チップ**（日付・人数・カテゴリラベル等、`--text-xs`〜`--text-sm`）:
  Zen Kaku Gothic New **weight 700** — 小さいが情報として確実に拾える強さを持たせる
- 本文（`--text-base`前後）は従来どおりweight 400/500の範囲に留め、対比の両極には
  寄せない

## Surface / Border / Radius / Shadow

partners-re.co.jpはCSS全体で`box-shadow`を一度も使わず、面の分離をヘアラインボーダーと
背景色の濃淡差だけで行っていた。これはTabiSyncが既に一部ページで進めている「重い影の
廃止」と方向が一致するため、正式なルールとして明文化する。

### 基本ルール
- カード・パネルの既定表現は「1pxのヘアラインボーダー（`--color-rule`、強調時は
  `--color-accent`を低不透明度で）＋背景色一段分の濃淡差」とし、`box-shadow`は使わない
- 例外: モーダル・シート・ドラッグ中の要素など「画面上に浮いている」ことを積極的に
  示す必要がある場合のみ、ごく薄い影（`--radius-lg`と組になっているコンポーネント）を
  許容する。カード・リスト項目・チップには使わない
- 新規トークン:
  ```
  --shadow-float: 0 8px 24px oklch(23% 0.018 50 / 0.08);
  ```
  モーダル・シートなど「本当に浮いている」要素専用。カード全般には使用しない。

### 「しおりの折り角」モチーフ（限定使用）

partners-re.co.jpのカード表現には、4隅を均等に丸めるのではなく1つの角だけ大きく丸める
非対称な処理が繰り返し登場していた。これはTabiSyncの製品が自称する「**しおり**」
（紙の旅行栞・折り目のある冊子）と自然に重なるモチーフである。紙のしおりには折られた
角がある——その質感を、装飾ではなく「これは旅程シートである」という機能的なサインとして
取り入れる。

```
--radius-notch: 3.5rem;      /* デスクトップ */
--radius-notch-sp: 2rem;     /* モバイル */
```

**使用範囲を意図的に限定する**（partners同様、乱用しない）:
- 旅程の「Day」カード（1日分の予定をまとめるカードのみ）: 右上角に`--radius-notch`
- 旅程表全体を囲む外枠（しおり本体を表すコンテナ）: 右上角のみ
- それ以外（AIチャットバブル、ボタン、フォーム、通常のカード）には使わない — ここで
  乱用すると「しおり」の意味を持たない単なる飾りに落ちるため

### 既存のRadius/Pillルール
```
--radius-sm: 4px;    入力欄・小チップ
--radius-md: 10px;   カード・パネル
--radius-lg: 18px;   モーダル・シート
--radius-pill: 100vh; タブ・フィルター・FAB・バッジ等、機能的affordanceがある要素のみ
```

既存ブレークポイント `$breakpoint-md: 960px`（`base/_variables.scss`）を維持。

## Spacing System

```
--space-3xs: 0.25rem;  --space-2xs: 0.5rem;  --space-xs: 0.75rem;
--space-sm:  1rem;     --space-md:  1.5rem;  --space-lg: 2.25rem;
--space-xl:  3.5rem;   --space-2xl: 5rem;    --space-3xl: 7.5rem;
```

単一基準値の倍数展開でスペーシングを構成する既存方針は、DNA研究で確認した「基準値の
倍数展開でスペーシングを作る」という原則と既に一致しているため、そのまま踏襲する。

## Motion

- Easing: `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)`
- 控えめなfadeとtranslateY(-1〜2px)程度の浮き上がりのみ。bounceなし。
- ヒーローCTAボタンのグラデーションシャイン・グラスブラー効果（backdrop-filter +
  shine sweep）は廃止（editorial genreはglassmorphism禁止、かつ「AIサービス風」の
  典型的な装飾のため）。
- `prefers-reduced-motion: reduce` で全アニメーション停止。

### ルートライン・ドローイン（地図・旅程向け／新規）

partners-re.co.jpの「罫線がスッと伸びるリビール」を、地図上のルート線・旅程表の
日程間コネクターが描画されていく表現として再解釈する。装飾的な線ではなく、「経路が
今まさに引かれている」という機能的な意味を持たせる。

```
--dur-medium: 480ms;
```

- 地図でその日のルートを表示する際、線を`stroke-dashoffset`で`--dur-medium`かけて
  描画する
- 旅程表で新しい予定カードが追加された際、前の予定との接続線を同様に描画する
- 色は文脈に応じて`--color-accent`（人間が確定した経路）または`--color-accent-ai`
  （AIが提案した経路）を使い分ける
- バウンドなし、`--ease-out`のみ使用

### AIコンシェルジュ・プログレスリング（新規）

partners-re.co.jpのカルーセルインジケーターが線形に回転する表現を、AIが処理中で
あることを示すリングとして再解釈する。

```
--dur-long: 900ms;
--ease-linear: linear;
```

- AIコンシェルジュが提案を生成している間、送信ボタンまたはチャットのAIアバター周囲に
  `--color-accent-ai`の円弧が`--ease-linear`・`--dur-long`のループで回転する
- 完了時はリングが止まり、フェードで消える（bounceなし）
- 人間の操作（紫）とは色相で明確に区別し、「今動いているのはAIである」ことを一目で
  示す

上記2つの新規モーションは機能説明のためだけに使い、それ以外の場所（例: ボタン、
通常のカード出現）には流用しない。

## Microinteractions stance

- ボタンhoverは `translateY(-1px)` 程度の軽い浮き上がりのみ。
- カードhoverは枠線をaccentへ、shadow-heavyな演出は避ける（既存の
  `box-shadow: 0 16px 38px rgba(...)` 級の重い影は廃止し、hairline border + ごく薄い
  shadowに置き換える）。
- 「しおりの折り角」（`--radius-notch`）は静的な構造上のサインであり、hoverやクリック
  で動かさない。
- ルートライン・ドローインとプログレスリングは、対応する処理（ルート表示・AI生成）が
  実際に走っているときにのみ再生する。ローディングを偽装する目的では使わない。

## CTA voice

- Primary: 塗りpill、`--color-accent` 背景、`--color-accent-ink` 文字、hoverで
  `--color-accent-strong`
- Secondary: アウトラインpill、`--color-ink` 枠線・文字、背景透明
- 既存クラス名（`.home-btn-primary` / `.guide-cta-btn-primary` 等）は維持し、中身の
  スタイルのみ変更
- グラデーションボタンは不採用のまま（partners-re.co.jpのCTAはグラデーション塗りで
  あったが、本ファイルの禁止ルールを継続する）

## Navigation方針

- ロジック（ハンバーガー開閉 `#btn08`/`#nav-menu`、スクロール時の`.is-scrolled`
  トグル）は一切変更しない。
- **base.html**（ドキュメント/フォーム系）: 常時白背景の固定ヘッダー。ロゴ＋インク
  リンク、hover時に`--color-accent`。
- **base_home.html**（マーケティング）: ヒーロー画像上は透明、スクロールで
  半透明ダーク＋blurへ切り替え（既存ロジック維持）。ロゴは白版のまま。
- PC/SPで別マークアップの部分（`.header-nav-pc-wrapper` / `.header-nav-wrapper`）は
  維持。
- **裏付け（DNA研究）**: base_home.htmlの「ヒーロー上は透明→スクロールで半透明ダーク＋
  blurへ切り替え」という既存実装は、partners-re.co.jpの固定ヘッダーが同じ状態遷移
  （透明→白背景+ぼかし）を可読性確保という機能目的のためだけに使っているのと構造的に
  一致していた。新しく輸入した原則ではなく、既存実装の妥当性が外部研究で確認できた、
  という位置づけである。装飾目的でのぼかし多用（editorial genreのglassmorphism禁止
  ルール）とは別枠として扱う。

## Component方針

- フッターは `templates/_site_footer.html` として共通化し、base.html /
  base_home.html の両方から `{% include %}` で読み込み済み（ワードマーク＋一行
  ステートメント＋規約リンク＋公式Xリンク）。`layout/_site-footer.scss` を
  `style.scss` / `home.scss` の双方にimportし、V1/V2アプリ本体専用の
  `layout/_footer.scss`（黒背景の別実装、`style_v2_1.scss`のみが参照）とは
  完全に分離した。
- ガイドページのコンポーネント（`.guide-lead`, `.guide-cta-btn`, `.guide-feature-list`,
  `.guide-steps`, `.guide-related-links`, `.guide-figure`）は `pages/_docs.scss` に
  既存実装済み。トークン接続のみで動作する。
- `.user-agreement-title` / `.user-agreement-sub-title`（H1/H2）、`.qa-6`（FAQ
  アコーディオン）はガイドページと規約・FAQページで共有される見出し/コンポーネント
  で、Phase 1で新トークンへ移行済み（結果としてガイドページ・規約・FAQページの
  見出しタイポグラフィが揃った。本文構造・コピーは変更していない）。
- **アプリ本体（未着手）ラウンドの適用候補**:
  - 旅程表の「Day」カード: `--radius-notch`を右上角のみに適用
  - 地図のルート表示・旅程表の日程間コネクター: ルートライン・ドローインを適用
  - AIコンシェルジュの送信ボタン/アバター: プログレスリングを適用
  - 上記はすべてV2アプリ本体に着手する回で正式に反映する。現時点のSCSS/テンプレートは
    変更しない。

## Per-page allowances

- マーケティングページ: 実プロダクトscreenshotの使用可（新規モックアップ生成は不可）
- ドキュメントページ: enrichmentなし。タイポグラフィのみ

## What pages MUST share

- ロゴ画像そのもの（再デザインしない）
- `--color-accent` とその使用率（各ビューポート3〜5%以内）
- `--color-accent-ai` / `--color-accent-warm` の限定的用途（面塗り禁止）
- Display / Body / Monoの3書体
- CTAの形状（塗り/アウトラインpill）
- フッター（共通パーシャル）
- box-shadowを使わないSurfaceルール
- `--radius-notch`は旅程関連カードのみに限定使用

## What pages MAY differ on

- ファミリー内でのレイアウト差分（ガイド記事ごとの見出し密度等）
- home.htmlのみ実プロダクトscreenshotを使用
- ルートライン・ドローインとプログレスリングは、対応する機能（地図・AI）を持つ
  ページのみで使用可

## カラー抽出ログ（実測）

`static/img/icon-tabisync.png`（180×180、メインロゴのグラデーションアイコン）と
`static/img/logo-ai-concierge.png`（AIコンシェルジュ副ロゴ）から、Pillowで実ピクセルを
sRGB取得し、OKLabを経由してOKLCHへ変換した（アルファ<200の透明ピクセルは除外、
グレー/白/黒に近い低彩度ピクセルも除外して最頻色を集計）。

- メインロゴ 左上付近（紫）: 実測 `rgb(197,118,185)` → `oklch(67% 0.131 333)`
  ※既存実装のブランド紫 `#AF29BB` (`rgb(175,41,187)`) → `oklch(55% 0.230 324)`
  の方がより濃く純度が高い。既存UIで既に使われ続けている値のため、`--color-accent`
  は`#AF29BB`の実測値をそのまま正式採用した（ロゴのハイライト部分より、既存の
  ブランドカラーとしての継続性を優先）。
- メインロゴ 右下付近（オレンジ）: 最頻値 `rgb(240,152,80)` 〜 `rgb(246,154,86)` →
  `oklch(76-77% 0.137-0.138 55-58)`。`--color-accent-warm` に採用。
- AIコンシェルジュ副ロゴ 最頻色（ネイビー）: `rgb(24,24,120)` → `oklch(30% 0.155 272)`。
  UIでの汎用性を考慮し `oklch(33% 0.150 271)` に軽く調整して `--color-accent-ai` に
  採用。
- 参考: 既存 `::selection` ハードコード値 `#6B2AC0` → `oklch(47% 0.214 297)`
  （紫とネイビーの中間的な色相）。本ラウンドで `::selection` は `--color-accent` に
  統合し、独立した値としては廃止した。

## Exports

### tokens.css（`base/_tokens.scss` に実装 — `--radius-notch`系・`--shadow-float`・
`--dur-medium`・`--dur-long`・`--ease-linear`は本ラウンドで追加した新規トークンで
あり、`_tokens.scss`への反映はまだ行っていない）
```css
:root {
  --color-paper: oklch(99% 0.004 75);
  --color-paper-2: oklch(97% 0.006 75);
  --color-paper-3: oklch(94% 0.008 75);
  --color-ink: oklch(23% 0.018 50);
  --color-ink-2: oklch(46% 0.022 50);
  --color-ink-3: oklch(66% 0.018 50);
  --color-rule: oklch(89% 0.010 75);

  --color-accent: oklch(55% 0.230 324);
  --color-accent-strong: oklch(48% 0.220 322);
  --color-accent-ink: oklch(98% 0.012 324);
  --color-accent-ai: oklch(33% 0.150 271);
  --color-accent-ai-ink: oklch(97% 0.010 271);
  --color-accent-warm: oklch(76% 0.140 56);
  --color-accent-warm-ink: oklch(24% 0.040 56);
  --color-focus: oklch(62% 0.200 324);

  --color-success: oklch(58% 0.110 150);
  --color-warning: oklch(78% 0.130 85);
  --color-error: oklch(55% 0.180 27);

  --font-display: "Kaisei Tokumin", "Hiragino Mincho ProN", "Yu Mincho", serif;
  --font-body: "Zen Kaku Gothic New", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP", sans-serif;
  --font-mono: "Space Mono", ui-monospace, "SF Mono", Menlo, monospace;

  --space-3xs: 0.25rem; --space-2xs: 0.5rem; --space-xs: 0.75rem; --space-sm: 1rem;
  --space-md: 1.5rem;  --space-lg: 2.25rem; --space-xl: 3.5rem;
  --space-2xl: 5rem;   --space-3xl: 7.5rem;

  --text-xs: 0.75rem;  --text-sm: 0.875rem; --text-base: 1rem;
  --text-md: 1.125rem; --text-lg: 1.375rem; --text-xl: 1.75rem;
  --text-2xl: 2.25rem; --text-3xl: 2.75rem;
  --text-display: clamp(2.15rem, 3.2vw + 1rem, 3.4rem);
  --text-display-s: clamp(1.75rem, 2vw + 1rem, 2.35rem);

  --radius-sm: 4px; --radius-md: 10px; --radius-lg: 18px; --radius-pill: 100vh;
  --radius-notch: 3.5rem;
  --radius-notch-sp: 2rem;

  --shadow-float: 0 8px 24px oklch(23% 0.018 50 / 0.08);

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-linear: linear;
  --dur-short: 200ms;
  --dur-medium: 480ms;
  --dur-long: 900ms;
}
```
