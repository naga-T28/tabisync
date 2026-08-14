# Design — TabiSync（改訂案 / DRAFT・未反映）

**この文書はまだ`design.md`に統合されていない提案です。** レビュー・承認後に本体の`design.md`へマージし、その後SCSS/テンプレートへ反映する2段階を想定しています。現時点でコード（SCSS/テンプレート）は一切変更していません。

ブランドカラーは引き続き `static/img/icon-tabisync.png`（メインロゴのグラデーション）と
`static/img/logo-ai-concierge.png`（AIコンシェルジュ副ロゴ）からの実ピクセル抽出値を正とします。今回のラウンドで色は一切変更していません。

---

## 変更差分サマリー

| 区分 | 内容 |
| --- | --- |
| **変更なし** | Color System（全トークン値）／書体そのもの（Kaisei Tokumin・Zen Kaku Gothic New・Space Mono）／CTAの形状（塗り/アウトラインpill）／ナビのロジック |
| **新規追加** | Surface/Border/Radius/Shadowの明文化（「しおりの折り角」モチーフ）／タイポグラフィのウェイト対比原則／ルートライン描画モーション（地図・旅程向け）／AIコンシェルジュ用プログレスリング／セクション非対称比率の原則 |
| **却下** | partners-re.co.jpの青系アクセント／グラデーションCTAボタン／メガドロップダウン型ナビ／写真主体のヒーロー方針への転換 |

---

## Provenance（DNA研究の記録）

- **研究対象**: `https://partners-re.co.jp/`（不動産・投資会社の公開コーポレートサイト。TabiSyncと資本・ブランド上の関係はない第三者サイトで、構造原則の参考としてのみ使用した公開参照）
- **抽出方法**: 公開HTML/CSSの技術的事実（フォント宣言、spacing/radius/color値、アニメーション定義、DOM構造）を直接取得して分析。ロゴ・写真・コピー・固有ブランドカラーは非採用。
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
  - グラデーションCTAボタン → 既存design.mdの禁止ルールを継続
  - 6〜8項目のメガドロップダウンナビ → TabiSyncのIAはこの複雑さを必要としないため不採用
  - 写真主体のヒーロー方針 → TabiSyncは実プロダクト画面（旅程表・地図）をヒーローに使う既存方針を継続。ストックフォト的な写真ヒーローには転換しない

---

## 適用範囲（現時点）

*（現行`design.md`と同じ。今回のラウンドで対象範囲の変更はなし）*

- **実装済み**: `templates/home.html`, `templates/base_home.html`, `templates/base.html`, `templates/docs/guide_sample.html`, `templates/docs/guide_no_signup.html`, `templates/docs/guide_collaboration.html`, `templates/docs/guide_all_in_one.html`, `templates/docs/guide_ai_concierge.html`
- **base.html継承による副次的な反映**: `templates/docs/qanda.html`, `templates/docs/update.html`, `templates/docs/profile.html`, `templates/docs/user_agreement.html`, `templates/docs/privacy_policy.html`, `templates/docs/concierge_terms.html`, `templates/contact/*.html`, `templates/tabisync/create.html`, `templates/404.html`
- **未着手（将来のラウンド）**: V2しおりアプリ本体（`templates/tabisync/content/*.html`, `templates/demo/v2_*.html`）、V1レガシー。本提案のSurface/Motionの新原則は、これらに着手する回で正式適用する（下記「Component方針」参照）。

## Genre

editorial（変更なし）

## Macrostructure family

*（既存の3ファミリー定義は維持。以下は今回の研究で得た補足原則）*

- **マーケティングページ**（home.html）: Workbench — 実プロダクト画面をヒーローに据える方針は継続。新規追加として、**セクションごとに異なる非対称比率を与える**原則を採用する（全セクションを同じ50/50分割の繰り返しにしない）。例: サービス紹介は均一カードグリッド、実績・特徴紹介は非対称2カラム、というように**内容の性質に応じて比率を変える**。
- **コンテンツ/ドキュメントページ**（docs/*.html）: Long Document — 変更なし。
- **アプリ本体**（未着手・「旅程キャンバス」）: 既存定義（旅程表=非対称2カラム、地図=空間型、AIコンシェルジュ=ドック型、リスト=単一カラム）を維持しつつ、非対称2カラムの比率は**旅程表とその日の地図プレビューの情報量に応じて可変**とする原則を明記する（常に同じ比率を強制しない）。

## Color System

**このラウンドでの変更なし。** 値・抽出手法は既存`design.md`の「カラー抽出ログ」を正とする。partners-re.co.jpの配色は一切参照していない。

### ニュートラル（白基調・微暖色バイアス）
```
--color-paper:    oklch(99% 0.004 75)
--color-paper-2:  oklch(97% 0.006 75)
--color-paper-3:  oklch(94% 0.008 75)
--color-ink:      oklch(23% 0.018 50)
--color-ink-2:    oklch(46% 0.022 50)
--color-ink-3:    oklch(66% 0.018 50)
--color-rule:     oklch(89% 0.010 75)
```

### ブランドアクセント（3アンカー）
```
--color-accent:         oklch(55% 0.230 324)  主要CTA・アクティブ状態（人間の操作）
--color-accent-strong:   oklch(48% 0.220 322)  hover/pressed
--color-accent-ink:      oklch(98% 0.012 324)

--color-accent-ai:       oklch(33% 0.150 271)  AIコンシェルジュ専用
--color-accent-ai-ink:   oklch(97% 0.010 271)

--color-accent-warm:     oklch(76% 0.140 56)   一瞬の強調専用
--color-accent-warm-ink: oklch(24% 0.040 56)

--color-focus:           oklch(62% 0.200 324)
```

**今回の研究による補強**: partners-re.co.jpは単一アクセント色を罫線・ボタン・リンクにのみ使い、背景を塗らないという規律で「未来的だが押しつけがましくない」印象を作っていた。これはTabiSyncが既に持つ「`--color-accent`の面積は各ビューポートの3〜5%以内」というルールと完全に一致する。**この既存ルールを変更する必要はなく、むしろ継続の妥当性が外部研究で裏付けられた**、という位置づけにする。

さらに、3アンカー体制（人間の操作=紫／AI=ネイビー／一瞬の強調=オレンジ）は、「友達との共同計画」と「AIによる旅行支援」を色相で切り分ける役割を既に果たしている。今回追加するのは運用ルールの明文化のみ：

- **紫（accent）**: ユーザー本人・友達の操作全般（旅程の追加・編集、招待、共有）
- **ネイビー（accent-ai）**: AIコンシェルジュが発話・提案・生成している状態全般
- **オレンジ（accent-warm）**: 「共有が完了した」「AIの提案が届いた」など、一瞬だけ祝福する通知的強調

### セマンティック
```
--color-success: oklch(58% 0.110 150)
--color-warning: oklch(78% 0.130 85)
--color-error:   oklch(55% 0.180 27)
```

## Typography System

書体そのものは変更なし。

- **Display**: Kaisei Tokumin, weight 500/700, style normal
- **Body**: Zen Kaku Gothic New, weight 400/500/700（フォールバック: Hiragino Kaku Gothic ProN → Yu Gothic → Noto Sans JP）
- **Mono（アウトライヤー）**: Space Mono, weight 400/700 — フッターワードマーク、パンくず区切り、日付・カウンター表示

```
--text-xs:  0.75rem;   --text-sm:  0.875rem;  --text-base: 1rem;
--text-md:  1.125rem;  --text-lg:  1.375rem;  --text-xl:  1.75rem;
--text-2xl: 2.25rem;   --text-3xl: 2.75rem;
--text-display:   clamp(2.15rem, 3.2vw + 1rem, 3.4rem);
--text-display-s: clamp(1.75rem, 2vw + 1rem, 2.35rem);
```

### 新規原則: ウェイト対比によるタイポグラフィ階層

partners-re.co.jpは「大きい要素ほど軽いウェイト、小さい要素ほど太いウェイト」という両極対比だけで階層を作っていた（中間ウェイトは本文にしか使わない）。この原則をKaisei Tokumin / Zen Kaku Gothic New の**既存フォントの範囲内で**採用する。

- **旅程・トリップのタイトル**（`--text-display`クラス）: Kaisei Tokumin **weight 500**（既存の700寄せをやめ、軽い方に統一）— 旅の名前は宣言的に太くするより、静かに大きく見せる方が「しおり」らしい
- **メタ情報チップ**（日付・人数・カテゴリラベル等、`--text-xs`〜`--text-sm`）: Zen Kaku Gothic New **weight 700** — 小さいが情報として確実に拾える強さを持たせる
- 本文（`--text-base`前後）は従来どおりweight 400/500の範囲に留め、対比の両極には寄せない

## Surface / Border / Radius / Shadow（新規セクション）

partners-re.co.jpはCSS全体で`box-shadow`を一度も使わず、面の分離をヘアラインボーダーと背景色の濃淡差だけで行っていた。これはTabiSyncが既に一部ページで進めている「重い影の廃止」と方向が一致するため、**正式なルールとして明文化する**。

### 基本ルール
- カード・パネルの既定表現は「1pxのヘアラインボーダー（`--color-rule`、強調時は`--color-accent`を低不透明度で）＋背景色一段分の濃淡差」とし、`box-shadow`は使わない
- 例外: モーダル・シート・ドラッグ中の要素など「画面上に浮いている」ことを積極的に示す必要がある場合のみ、ごく薄い影（既存`--radius-lg`と組になっているコンポーネント）を許容する。カード・リスト項目・チップには使わない
- 新規トークン:
  ```
  --shadow-float: 0 8px 24px oklch(23% 0.018 50 / 0.08);
  ```
  モーダル・シートなど「本当に浮いている」要素専用。カード全般には使用しない。

### 「しおりの折り角」モチーフ（新規・限定使用）

partners-re.co.jpのカード表現には、4隅を均等に丸めるのではなく**1つの角だけ大きく丸める**非対称な処理が繰り返し登場していた。これはTabiSyncの製品が自称する「**しおり**」（紙の旅行栞・折り目のある冊子）と自然に重なるモチーフだと考える。紙のしおりには折られた角がある——その質感を、装飾ではなく**「これは旅程シートである」という機能的なサインとして**取り入れる。

```
--radius-notch: 3.5rem;      /* デスクトップ */
--radius-notch-sp: 2rem;     /* モバイル */
```

**使用範囲を意図的に限定する**（partners同様、乱用しない）:
- 旅程の「Day」カード（1日分の予定をまとめるカードのみ）: 右上角に`--radius-notch`
- 旅程表全体を囲む外枠（しおり本体を表すコンテナ）: 右上角のみ
- それ以外（AIチャットバブル、ボタン、フォーム、通常のカード）には使わない — ここで乱用すると「しおり」の意味を持たない単なる飾りに落ちるため

### 既存のRadius/Pillルールは維持
```
--radius-sm: 4px;    入力欄・小チップ
--radius-md: 10px;   カード・パネル
--radius-lg: 18px;   モーダル・シート
--radius-pill: 100vh; タブ・フィルター・FAB・バッジ等
```

## Spacing System

変更なし。既存の単一基準値ベースの構成（`--space-3xs`〜`--space-3xl`）は、今回の研究で確認した「基準値の倍数展開でスペーシングを作る」という原則と既に一致しているため、そのまま踏襲する。

```
--space-3xs: 0.25rem;  --space-2xs: 0.5rem;  --space-xs: 0.75rem;
--space-sm:  1rem;     --space-md:  1.5rem;  --space-lg: 2.25rem;
--space-xl:  3.5rem;   --space-2xl: 5rem;    --space-3xl: 7.5rem;
```

既存ブレークポイント `$breakpoint-md: 960px` を維持。

## Motion

既存の「控えめなfadeとtranslateY(-1〜2px)程度」「bounceなし」「`prefers-reduced-motion: reduce`で全停止」という方針は維持した上で、以下2つを新規に追加する。いずれも装飾ではなく、**地図・旅程・AI支援という製品機能そのものを説明するモーション**として位置づける。

### 1. ルートライン・ドローイン（地図・旅程向け）

partners-re.co.jpの「罫線がスッと伸びるリビール」を、地図上のルート線・旅程表の日程間コネクターが**描画されていく**表現として再解釈する。装飾的な線ではなく、「経路が今まさに引かれている」という機能的な意味を持たせる。

```
--dur-medium: 480ms;
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);  /* 既存トークンを流用 */
```

- 地図でその日のルートを表示する際、線をstroke-dashoffsetで`--dur-medium`かけて描画する
- 旅程表で新しい予定カードが追加された際、前の予定との接続線を同様に描画する
- 色は文脈に応じて`--color-accent`（人間が確定した経路）または`--color-accent-ai`（AIが提案した経路）を使い分ける
- バウンドなし、`--ease-out`のみ使用

### 2. AIコンシェルジュ・プログレスリング

partners-re.co.jpのカルーセルインジケーターが5秒かけて線形に回転する表現を、**AIが処理中であることを示すリング**として再解釈する。

```
--dur-long: 900ms;
--ease-linear: linear;
```

- AIコンシェルジュが提案を生成している間、送信ボタンまたはチャットのAIアバター周囲に`--color-accent-ai`の円弧が`--ease-linear`・`--dur-long`のループで回転する
- 完了時はリングが止まり、フェードで消える（bounceなし）
- 人間の操作（紫）とは色相で明確に区別し、「今動いているのはAIである」ことを一目で示す

### 既存モーションとの関係
- ボタンhover（`translateY(-1px)`）、カードhover（枠線をaccentへ）は変更なし
- 上記2つの新規モーションは**機能説明のためだけに使い、それ以外の場所（例: ボタン、通常のカード出現）には流用しない**

## Microinteractions stance

既存方針を維持。追加ルール:
- 「しおりの折り角」（`--radius-notch`）は静的な構造上のサインであり、hoverやクリックで動かさない（partnersでも装飾トリックではなく常時表示の構造要素だった）
- ルートライン・ドローインとプログレスリングは、対応する処理（ルート表示・AI生成）が実際に走っているときにのみ再生する。ローディングを偽装する目的では使わない

## CTA voice

変更なし。
- Primary: 塗りpill、`--color-accent`背景、`--color-accent-ink`文字、hoverで`--color-accent-strong`
- Secondary: アウトラインpill、`--color-ink`枠線・文字、背景透明
- **グラデーションボタンは今回の研究後も不採用のまま**（partnersのCTAはグラデーション塗りだったが、既存design.mdの禁止ルールを継続する）

## Navigation方針

ロジック変更なし。以下は今回の研究で得た**裏付けの記録**として追記する。

- **base_home.html**の「ヒーロー上は透明→スクロールで半透明ダーク＋blurへ切り替え」という既存実装は、partners-re.co.jpの固定ヘッダーが同じ状態遷移（透明→白背景+ぼかし）を**可読性確保という機能目的のためだけに**使っているのと構造的に一致していた。これは新しく輸入した原則ではなく、**既存実装の妥当性が外部研究で確認できた**という位置づけにする。装飾目的でのぼかし多用（editorial genreのglassmorphism禁止ルール）とは別枠として扱う。

## Component方針

既存方針（フッター共通化、ガイドページコンポーネント等）を維持。以下を「アプリ本体（未着手）」ラウンドの適用候補として追記する:

- 旅程表の「Day」カード: `--radius-notch`を右上角のみに適用
- 地図のルート表示・旅程表の日程間コネクター: ルートライン・ドローインを適用
- AIコンシェルジュの送信ボタン/アバター: プログレスリングを適用
- 上記はすべて**V2アプリ本体に着手する回で正式に反映**する。現時点のSCSS/テンプレートは変更しない。

## Per-page allowances

変更なし。
- マーケティングページ: 実プロダクトscreenshotの使用可（新規モックアップ生成は不可）
- ドキュメントページ: enrichmentなし。タイポグラフィのみ

## What pages MUST share

既存項目に以下を追加:
- ロゴ画像そのもの（再デザインしない）
- `--color-accent`とその使用率（各ビューポート3〜5%以内）
- `--color-accent-ai` / `--color-accent-warm`の限定的用途
- Display / Body / Monoの3書体
- CTAの形状（塗り/アウトラインpill）
- フッター（共通パーシャル）
- **（新規）box-shadowを使わないSurfaceルール**
- **（新規）`--radius-notch`は旅程関連カードのみに限定使用**

## What pages MAY differ on

- ファミリー内でのレイアウト差分（ガイド記事ごとの見出し密度等）
- home.htmlのみ実プロダクトscreenshotを使用
- **（新規）ルートライン・ドローインとプログレスリングは、対応する機能（地図・AI）を持つページのみで使用可**

## カラー抽出ログ（実測）

*（既存`design.md`と同一。今回のラウンドで再サンプリングは行っていない）*

- メインロゴ左上付近（紫）実測 `rgb(197,118,185)` → `oklch(67% 0.131 333)`。既存ブランド紫 `#AF29BB`（`oklch(55% 0.230 324)`）の方が濃く純度が高く、既存UIでの継続性を優先しこちらを正式採用（変更なし）。
- メインロゴ右下付近（オレンジ）最頻値 `rgb(240,152,80)`〜`rgb(246,154,86)` → `oklch(76-77% 0.137-0.138 55-58)`。`--color-accent-warm`（変更なし）。
- AIコンシェルジュ副ロゴ最頻色（ネイビー）`rgb(24,24,120)` → `oklch(30% 0.155 272)` → 調整後 `oklch(33% 0.150 271)`（変更なし）。

## Exports

### tokens.css（案 — 現行`base/_tokens.scss`に対する差分は末尾3行のみ追加）
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

---

## 次のステップ（未実施）

1. この案の内容をレビューいただき、必要な修正を反映
2. 承認後、本体の`design.md`へマージ
3. `base/_tokens.scss`へ新規トークン（`--radius-notch`系・`--shadow-float`・`--dur-medium`・`--dur-long`・`--ease-linear`）を追加
4. 「しおりの折り角」「ルートライン・ドローイン」「AIプログレスリング」は、いずれもV2アプリ本体（旅程表・地図・AIコンシェルジュ）に着手する回で実装 — 現行の`home.html`等の実装済みページに今すぐ影響が出るものではありません
