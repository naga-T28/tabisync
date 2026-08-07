# Task 003: 旅程表に選択日の訪問スポット地図を表示する

- 種別: フロントエンド / 地図 / 旅程表UI
- 優先度: High
- 状態: 実装待ち
- 対象: 現行V2旅程表ページ
- 前提: Task 002のMap Display Adapter（`createMapRenderer`）を利用できること
- 対象外: V1画面、旅程編集画面、ブログ埋め込み画面、場所検索・保存仕様の変更

## 目的

現行V2旅程表ページに、ユーザーが現在選択している日の予定で訪れるスポットを地図表示する。

- PCでは、右側カラムの「ブログ用iframeを出力」の直上に表示する。
- SPでは、旅程表の直下に表示する。
- 日タブを切り替えると、地図も選択日に合わせて即時に更新する。
- 地図の見た目と操作感は、Task 002で整備した現行V2地図UIと統一する。

## 用語と表示対象

本タスクにおける「訪れるスポット」は、選択日の`ScheduleV2`に`place`として紐づいている`WantToGo`とする。

- `WantToGo.planned_day`だけを基準にしない。旅程表に実際に登録された予定の日（`ScheduleV2.day_index`、既存互換データは`get_schedule_day_index()`で解決）を基準にする。
- 選択日に予定があっても`ScheduleV2.place`が未設定なら地図へ追加しない。
- `place`に有効な`latitude`と`longitude`がない場合はマーカーを表示しない。
- 同じ`WantToGo`が同じ日に複数回使われている場合、地図上では`WantToGo.id`単位で1スポットに重複排除する。
- 表示順が必要な場所一覧やアクセシブルな代替表示は、その日の予定順（`start_time`, `order`, `id`）を維持する。
- 別のしおりに属する場所を混入させない。既存の`Itinerary`スコープと閲覧認可を維持する。

## 現状の実装境界

### 主な変更対象

- `project_tabisync/tabisync/views/itinerary_v2.py`
  - `ItineraryDetailV2View`は既に`ScheduleV2.place`を`select_related()`で取得し、日別の`grouped_days`を生成している。
  - 各日について、地図表示に必要な最小限の構造化データを組み立てる。
- `project_tabisync/templates/tabisync/content/content.html`
  - 日タブと`setActivePanelByIndex()`に地図更新を連動させる。
  - PC/SPの指定位置に地図カードを配置する。
- `project_tabisync/static/js/map_renderer.js`
  - Task 002の共通Map Display Adapterを再利用する。
  - 本要件に不足する安全な更新APIが必要な場合のみ、既存呼び出し元と後方互換を維持して拡張する。
- `project_tabisync/static/scss/content_V2/_content.scss`
  - 地図カード、地図コンテナ、空状態、読み込み失敗時の表示、レスポンシブ配置を定義する。
- `project_tabisync/static/css/style_v2_1.css`およびsource map
  - SCSSから再生成する。
- `project_tabisync/tabisync/tests/test_itinerary_v2.py`
  - view context、認可、日別データ、重複排除、座標の扱いを回帰テストする。

### 変更しない領域

- `ScheduleV2`、`WantToGo`のモデルと保存形式。
- Google PlacesのAutocomplete、検索、Place Details取得。
- 「Google Mapsで開く」リンクの生成・挙動。
- Task 002のprovider設定、attribution、fallback、座標検証、セキュリティ境界。
- V1テンプレート・SCSS。
- `blog_schedule_embed.html`とブログ用iframeの出力内容。

## UI要件

### 共通

- カード見出しは、選択日が分かる文言にする。例: `1日目の訪問スポット`。
- 地図コンテナには、選択日を含む適切なaccessible nameを設定する。
- 初期表示日は旅程表の既存ロジックに従う。今日の日付を含む日があればその日、なければ1日目を表示し、地図も同じ日に同期する。
- 日タブ、日選択メニュー、既存の自動日選択のいずれから切り替わっても、見出し、マーカー、表示範囲、空状態を同時に更新する。
- 1地点では過度に拡大しない適切なzoom、複数地点では全マーカーが収まるboundsを使用する。
- マーカーを押すと既存の`openPlaceModal()`で正しい場所詳細を開く。
- マーカーの色・形、地図操作、attributionは既存V2地図UIと統一する。
- 高さを確保してレイアウトシフトを抑え、読み込み中も旅程表の操作を妨げない。
- 地図を操作できない利用者のため、少なくとも選択日のスポット名をDOM上で確認できる代替表示を残す。既存モーダルまたは「Google Mapsで開く」導線も利用できるようにする。

### PC（`min-width: 960px`）

- `.schedule-side-column`内に地図カードを置く。
- 地図カードは「ブログ用iframeを出力」カードの直上に表示する。
- 右カラム幅`340px`内で横スクロールやはみ出しを発生させない。
- 概要カードがある場合は、`概要 → 訪問スポット地図 → ブログ用iframeを出力 → しおりを共有`の順にする。
- 概要カードがない場合も、地図カードを「ブログ用iframeを出力」の直上に置く。

### SP（`max-width: 959px`）

- 地図カードは`.schedule-table-box`の直後、すなわち旅程表の下に配置する。
- 概要、ブログ用iframe、共有カードより前に表示する。
- 画面幅を超えず、タッチ操作時にページの縦スクロールを阻害しない。

同一の地図DOMをCSSの`order`だけで正しい位置へ配置できるならそれを優先し、PC用・SP用に同じ地図を二重生成しない。DOMの複製が不可避な場合も、同時に2つのMapインスタンスを初期化せず、表示中のコンテナだけを使用する。

## データ受け渡し

- DjangoからJavaScriptへは、Djangoの`json_script`など安全なJSON埋め込みを使用する。
- `innerHTML`へ場所名、住所、メモ、provider由来HTMLを直接渡さない。
- 各スポットに渡す値は原則として`id`、`name`、`address`、`lat`、`lng`、`planned_day`、地図モーダルに必要な既存項目に限定する。
- token、パスワード、セッション情報、不要なメモをtile/style providerへ送信しない。
- Python側で`None`を除外し、JavaScript側でも緯度`[-90, 90]`、経度`[-180, 180]`を再検証する。
- クエリ数を日数や予定数に比例させない。既存の`select_related("place")`を維持し、追加のN+1 queryを発生させない。

想定する日別データ形状:

```json
{
  "1": [
    {
      "id": 10,
      "name": "訪問スポット名",
      "address": "住所",
      "lat": 35.0,
      "lng": 139.0,
      "planned_day": 1
    }
  ],
  "2": []
}
```

キーは画面上の`day_num`と一致させ、日程未定のしおりでも既存の日番号ロジックで動作させる。

## 地図ライフサイクル

- 初回は、既存の日選択ロジックが確定した後に選択日の地図を初期化する。
- 日切替ごとにMapLibre本体やstyleを再ロードしない。
- 可能であれば1つのMapインスタンスを保持し、マーカー集合の差し替え、表示・非表示、bounds更新で対応する。
- 共通Adapterがマーカー集合の更新に対応していない場合は、`setPlaces(places)`等のprovider非依存APIを追加することを検討する。
- 再生成する場合は古いMapインスタンスを`destroy()`して、イベントリスナー、WebGL context、DOMをリークさせない。
- 非表示状態で初期化したMapを表示する場合は、必要に応じてresizeを行い、地図の欠けや中心ずれを防ぐ。
- 高速な日タブ連打や地図ロード中の日切替でも、古い非同期処理が新しい選択日の表示を上書きしない。

## 空状態と障害時fallback

### 選択日に座標付きスポットが0件の場合

- 空の世界地図を表示しない。
- 地図コンテナを隠し、`この日の予定には地図表示できるスポットがありません。`等の空状態を表示する。
- 予定自体、場所名、編集リンクは従来どおり表示する。
- 座標なしの場所が予定にある場合もJavaScript errorにしない。

### provider障害、timeout、WebGL非対応、CSP拒否の場合

- 地図canvasのみを非表示にし、選択日のスポット名と既存の場所詳細・Google Maps外部リンクを残す。
- ユーザー向けには内部例外、style URL、stack traceを表示しない。
- 日タブ切替、旅程表、ブログiframeコピー、共有機能は継続利用できるようにする。

## セキュリティ・プライバシー要件

- 表示対象は、閲覧認可済みの現在の`Itinerary`に属する`ScheduleV2.place`だけに限定する。
- 任意のscript、style、tile、iframe URLを場所データやURL parameterから注入できないようにする。
- provider/style設定はTask 002のサーバー設定だけを使用する。
- ユーザー入力値をHTML文字列として組み立てない。DOM APIの`textContent`またはDjango templateのescapeを使う。
- attributionをPC/SPともに常時読める状態にする。
- 新たなGoogle Maps JavaScript APIの地図インスタンスを作らない。場所検索用Google APIと表示用MapLibreの責務分離を維持する。

## 実装手順

1. `ItineraryDetailV2View`の日別group生成時に、予定へ紐づく場所から地図用データを作る。
2. 有効座標だけを地図対象とし、同じ`WantToGo.id`を日単位で重複排除する。
3. `content.html`へ地図カード、地図コンテナ、空状態、fallback、代替スポット一覧を追加する。
4. `json_script`等で日別データを安全に渡す。
5. 既存の`setActivePanelByIndex()`を単一の同期ポイントとして、旅程表と地図を同じ日へ更新する。
6. Task 002の`createMapRenderer()`を利用し、marker clickを`openPlaceModal()`へ接続する。
7. PC/SPの配置をSCSSで実装し、CSSとsource mapを再生成する。
8. viewとJavaScriptの回帰テストを追加し、主要画面を手動確認する。

## テスト

### Django / データ

- 選択日ごとに、その日の`ScheduleV2.place`だけが地図用データへ含まれる。
- `WantToGo.planned_day`と予定の`day_index`が異なる場合、予定の`day_index`側に表示される。
- 同じ場所を同じ日に複数予定で参照しても1件に重複排除される。
- 同じ場所を別日に参照した場合は、それぞれの日のデータへ含まれる。
- `place=None`、座標なし、NaN相当、不正範囲の座標を安全に除外する。
- 別Itineraryの場所を表示できない。
- 日程未定のしおりと既存互換の日付データでも正しい日番号へ分類される。
- 既存の閲覧・編集認可、パスワードゲート、token境界を維持する。
- query数が予定件数に比例して増えない。

### JavaScript / UI

- 初期表示日と地図の日が一致する。
- 今日の日付を含む旅程では、自動選択された今日の地図が表示される。
- 日タブと日選択メニューの切替で、見出し、マーカー、bounds、空状態が同期する。
- marker clickで正しい`openPlaceModal()`が開く。
- 0件、1件、複数件、重複座標、不正座標でJavaScript errorにならない。
- 高速な日切替中も古い日の非同期描画結果が残らない。
- provider失敗時も旅程表、場所名、Google Mapsリンク、編集・共有操作が残る。
- 地図の初期化と破棄を繰り返してもイベントやMapインスタンスが増殖しない。
- mock providerで外部通信なしに日切替を検証できる。

### レスポンシブ・アクセシビリティ

- PCでは右カラムの「ブログ用iframeを出力」直上に表示される。
- SPでは旅程表の直下かつ概要・iframe・共有カードより前に表示される。
- `959px`と`960px`の境界で順序崩れ、二重表示、横スクロールがない。
- keyboard操作で日を切り替えた場合も地図が更新される。
- map containerに選択日を含むaccessible nameがある。
- 地図が使えなくてもスポット名と外部導線へ到達できる。
- attributionがPC/SPで欠けずに読める。

## 検証コマンド

```bash
cd project_tabisync
pipenv run python manage.py check
pipenv run python manage.py test tabisync.tests.test_itinerary_v2
pipenv run python manage.py test tabisync
```

SCSS変更後はリポジトリルートで次を実行し、意図したCSSとsource mapだけが更新されていることを確認する。

```bash
npx sass project_tabisync/static/scss:project_tabisync/static/css
```

`npm test`は未設定のため使用しない。`staticfiles/`、`media/`、`logs/`は変更・commitしない。

## 完了条件

- 現在選択している日の予定に紐づく座標付きスポットだけが地図表示される。
- 日タブ切替と地図の見出し、マーカー、表示範囲、空状態が常に同期する。
- PCでは右側の「ブログ用iframeを出力」直上、SPでは旅程表直下に表示される。
- Task 002のMap Display Adapterとprovider設定を再利用し、新しい表示provider依存を追加していない。
- 0件、座標なし、provider障害時に安全なfallbackが機能する。
- 別Itineraryの情報漏えい、任意HTML/URL注入、認可回避がない。
- 地図が利用できない場合も、選択日のスポット情報と主要な旅程表操作を利用できる。
- Django自動テストとPC/SPの主要操作確認が完了し、SCSSに対応するCSSとsource mapが再生成されている。
