# Task 010: 管理画面からお知らせバナーを配信する機能を追加する

- 種別: バックエンド / 管理画面 / フロントエンド
- 優先度: Medium
- 状態: 実装済み
- 対象: ホームページ（`home.html`）、しおり詳細ページ（V2、`tabisync/content/content.html`）
- 前提: なし
- 対象外: V1レガシーしおり画面（`content`, `content_memo`, `content_list`等）、パスワード入力画面、ブログ埋め込み（`blog_schedule_embed.html`）、ドキュメント/FAQ/お問い合わせ等`base.html`系ページ、デモ/サンプルページ

## 目的

Django管理画面から、メンテナンス告知などのメッセージを配信できるようにする。管理者は表示先を「ホームページ」「すべてのしおりページ」「個別に指定したしおりページ」から選択できる。表示場所はページファミリーごとに異なる（下記「表示レイアウト・スタイル」参照）。

## 実装後の訂正（重要）

初版ではホームページも「`base_home.html`の`</header>`直後」に、しおりページと同じ帯状バナーで表示する設計だった。実装後に次の2点が判明し、設計を変更した。

1. **CSSバンドルの取り違え**: `base_home.html`が実際に読み込むCSSは`static/css/style.css`（`style.scss`由来）ではなく`static/css/home.css`（`static/scss/home.scss`由来）だった。初版では`style.scss`側に`@use`していたため、ホームページにCSSが一切反映されない不具合になっていた。
2. **デザイン変更の依頼**: ホームページでは帯状バナーではなく、MV（`.home-hero`）直下に専用エリアを設け、カード型で表示する形に変更した。あわせて「メンテナンスなどの情報は公式Xを参照してください」という導線（`https://x.com/tabisync_com`へのリンク）を常時表示するようにした。

この結果、**ホームページ用とV2しおりページ用で、テンプレート・CSSパーシャル・トークンの使い方が完全に分かれている**（後述の「現状の実装境界」参照）。

## 現状の実装境界

### 主な変更対象

- `project_tabisync/tabisync/models.py` — 新規モデル`SiteAnnouncement`を追加する。
- `project_tabisync/tabisync/admin.py` — `SiteAnnouncementAdmin`として管理画面へ登録する（既存登録は`admin.site.register(Model)`のみで`ModelAdmin`のカスタマイズ例がないため、本タスクが最初の`ModelAdmin`実装になる）。
- 新規マイグレーション（`tabisync/migrations/`）。
- `project_tabisync/project_tabisync/context_processors.py` — 新規`announcement(request)`を追加する（既存の`google_maps`/`map_display`/`seo`と同じ関数ベースの規約に合わせる）。
- `project_tabisync/project_tabisync/settings.py` — `TEMPLATES[0]["OPTIONS"]["context_processors"]`へ追加する。
- **しおりページ（V2）側**
  - `project_tabisync/templates/_announcement_banner.html` — 帯状バナーの共通パーシャル（`_site_footer.html`と同じ位置付け）。
  - `project_tabisync/templates/tabisync/content/base.html` — PC用サイドナブ型ヘッダー（47〜107行目）とSP用ヘッダー（108〜127行目）の両方が閉じたあと、`{% block contents %}`の直前に1箇所だけ`{% include %}`する。CSSのメディアクエリでPC/SPヘッダーの表示が切り替わるため、バナーをヘッダーごとに二重配置する必要はない。
  - `project_tabisync/static/scss/layout/_announcement-banner.scss` — 新規。`style_v2_1.scss`にのみ`@use`する（`style.scss`には不要、下記参照）。
  - `project_tabisync/static/scss/content_V2/_base.scss` — 固定ヘッダー分のクリアランス（モバイル`margin-top: 60px`、PCは左サイドナブ幅ぶんの`margin-left`をサイドナブ開閉状態と連動させて付与）を追加する。
- **ホームページ側**
  - `project_tabisync/templates/_announcement_banner_home.html` — MV直下専用の新規パーシャル。カード型UIと公式Xへの導線を持つ。
  - `project_tabisync/templates/home.html` — `.home-hero`の`</section>`直後に`{% include "_announcement_banner_home.html" %}`を追加する。`base_home.html`のヘッダー直下には何も追加しない。
  - `project_tabisync/static/scss/home/_announcement.scss` — 新規。design.mdのトークン（`--color-*`, `--space-*`, `--radius-*`）を直接使う（`home.scss`は`base/tokens`を読み込んでいるため）。
  - `project_tabisync/static/scss/home.scss` — 上記partialを`@use`する。
- **共通**
  - `project_tabisync/tabisync/models.py` / `admin.py` / マイグレーション / `context_processors.py` / `settings.py` — ページファミリーに依らず共通（後述）。
  - `project_tabisync/static/js/announcement_banner.js` — 新規。`.announcement-banner`/`.announcement-banner-close`/`data-announcement-id`をフックにした閉じるボタン制御。しおりページの帯状バナー・ホームのカードUIの両方から共通で読み込む（ホーム側もクラス名の一部を流用しているため、JSの変更なしで両対応している）。
  - `project_tabisync/static/css/style_v2_1.css`, `home.css`とsource map — SCSSから再生成する。
  - `project_tabisync/tabisync/tests/test_announcement.py` — 新規。

### 変更しない領域

- `templates/base.html`（ドキュメント/お問い合わせ/FAQ/規約等）— 今回はホームページとしおりページのみが対象で、それ以外のページには表示しない。
- V1レガシーのしおり画面、`templates/demo/v2_*.html`等のデモ/サンプルページ。
- `_site_footer.html`、`components/_messages.scss`（Djangoの`django.contrib.messages`用フラッシュメッセージとは別物として扱う。1回限りの操作結果通知と、管理者が能動的に配信する持続的なバナーは目的が異なるため統合しない）。
- `Itinerary`モデル本体、パスワード認可ロジック（`ViewPasswordRequiredMixin`）。

## データモデル

```python
class SiteAnnouncement(models.Model):
    LEVEL_CHOICES = [
        ("info", "情報"),
        ("warning", "注意"),
        ("critical", "重要（メンテナンス等）"),
    ]

    title = models.CharField("管理用タイトル", max_length=100, help_text="管理画面の一覧にのみ表示。サイトには表示されない。")
    message = models.TextField("表示メッセージ", max_length=500)
    level = models.CharField("重要度", max_length=10, choices=LEVEL_CHOICES, default="info")

    is_active = models.BooleanField("有効にする", default=False)
    show_on_home = models.BooleanField("ホームページに表示", default=False)
    show_on_all_itineraries = models.BooleanField("すべてのしおりページに表示", default=False)
    itineraries = models.ManyToManyField(
        "Itinerary",
        verbose_name="対象のしおり（個別指定）",
        blank=True,
        help_text="「すべてのしおりページに表示」がオフのとき、ここで指定したしおりにのみ表示します。",
    )

    starts_at = models.DateTimeField("表示開始日時", null=True, blank=True)
    ends_at = models.DateTimeField("表示終了日時", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_within_schedule(self, now=None) -> bool:
        now = now or timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def __str__(self):
        return self.title
```

- `title`は管理画面の一覧・検索用のみで、サイト上には出さない（`message`と分離することで、後から見返したときに何のための告知か分かりやすくする）。
- `show_on_home`と`show_on_all_itineraries`は独立したフラグにする。両方オフでも`itineraries`が指定されていれば、その個別しおりにだけ表示できる。
- 複数の`SiteAnnouncement`が同時に同じページの表示条件を満たした場合、バナーを重ねて複数表示はしない。`updated_at`が最も新しい1件だけを表示する（重複表示によるレイアウト崩れ・視認性低下を避けるため）。この挙動は本タスクの完了条件に含める。

## 管理画面（admin.py）

```python
class SiteAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "is_active", "show_on_home", "show_on_all_itineraries", "starts_at", "ends_at", "updated_at")
    list_filter = ("level", "is_active", "show_on_home", "show_on_all_itineraries")
    search_fields = ("title", "message")
    filter_horizontal = ("itineraries",)
    readonly_fields = ("created_at", "updated_at")
```

- `filter_horizontal`にすることで、しおり件数が多くなっても個別指定がしやすい2ペインUIになる。
- `ChecklistV2`が既存コードで未登録のまま残っている点は本タスクと無関係なため触らない。

## 表示対象の判定ロジック（context_processors.py）

```python
def announcement(request):
    match = request.resolver_match
    url_name = getattr(match, "url_name", None) if match else None

    qs = SiteAnnouncement.objects.filter(is_active=True)
    now = timezone.now()
    qs = qs.filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now))
    qs = qs.filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))

    if url_name == "home":
        qs = qs.filter(show_on_home=True)
    elif url_name == "content_v2":
        pk = match.kwargs.get("pk")
        qs = qs.filter(models.Q(show_on_all_itineraries=True) | models.Q(itineraries__id=pk))
    else:
        return {"active_announcement": None}

    active = qs.order_by("-updated_at").distinct().first()
    return {"active_announcement": active}
```

- `request.resolver_match.url_name`でホーム（`tabisync:home`）としおり詳細（`tabisync:content_v2`）だけを対象にし、それ以外のURLでは常に`None`を返す。これによりドキュメント系ページやV1画面は`_announcement_banner.html`をincludeしていない上に、そもそもクエリの絞り込み結果も空になる二重の安全策になる。
- `ItineraryDetailV2View.get()`は`get_context_data()`を経由せず`render(request, ...)`を直接呼んでいるが、`render()`は内部で`RequestContext`を使いcontext processorを自動的にマージするため、ビュー側の追加対応は不要。
- しおりのパスワード保護（`view_password`）はテンプレートレンダリング前の`ViewPasswordRequiredMixin`で処理されるため、パスワード未突破の状態ではそもそも`content.html`が描画されず、バナーも表示されない。パスワード入力画面（`password.html`）自体は対象外のまま。

## 表示レイアウト・スタイル

しおりページとホームページで、見た目・挿入位置・使用するCSSトークンが異なる。

### しおりページ（V2）— ヘッダー直下の帯状バナー

- 挿入位置は`content/base.html`の`{% block contents %}`直前（PC/SPどちらのヘッダーが閉じたあとの1箇所のみ）。
- `style_v2_1.scss`は`base/variables`のみで`base/tokens`（design.mdのOKLCHトークン）を読み込んでいない（design.mdの適用範囲がまだV2アプリ本体に及んでいないため）。そのため`_announcement-banner.scss`は`base/tokens`のCSS変数に依存せず、`base/variables`（`$accent-purple`, `$danger`, `$white`, `$gray-bg`, `$radius-*`等）だけを使って実装している。
- `level`ごとの配色は`base/variables`の既存値を流用する: `info`は`$gray-bg`背景+`$text-main`文字、`warning`は`$accent-purple`系、`critical`は`$danger`系。
- 横幅いっぱいの1行〜数行のバー。長文の場合に折り返しても崩れないようにする。
- `.page-header`が`position: fixed`のため、バナー自体に固定ヘッダー分のクリアランス（モバイル`margin-top: 60px`、PC幅は左サイドナブ幅ぶんの`margin-left`をサイドナブ開閉状態と連動させて付与）を持たせている。

### ホームページ — MV直下の専用エリア（カード型）

- 挿入位置は`.home-hero`（MV）の`</section>`直後、`.home-recent-section`より前。ヘッダーには何も追加しない（ヘッダーが`.home-hero`に透過で重なる既存デザインのため、ヘッダー直下だと隠れてしまう）。
- `home.scss`は`base/tokens`を読み込んでいるため、`home/_announcement.scss`はdesign.mdのCSSカスタムプロパティ（`--color-paper-2`, `--color-rule`, `--color-ink`, `--color-ink-2`, `--color-accent`, `--space-*`, `--radius-md`等）をそのまま使う。`base/variables`は使わない。
- ヘアラインボーダー＋`--color-paper-2`背景のカードUI（design.mdの「box-shadowを使わないSurfaceルール」に準拠。グラデーション背景も使わない）。
- `level`ごとの配色は`--color-warning`/`--color-error`と同じ色相のOKLCH値を薄いトーンにして使う（`color-mix()`は使わず、リテラルなoklch値で直接指定）。
- メッセージ本文に加えて、常に次の導線を表示する: 「メンテナンスなどの最新情報は公式X（@tabisync_com）でご確認ください。」（`https://x.com/tabisync_com`へのリンク、`target="_blank" rel="noopener noreferrer"`）。

### 共通

- `message`はDjangoのオートエスケープに任せ、`|safe`は使わない。改行は`linebreaksbr`で`<br>`化する（ユーザー入力ではなく管理者入力だが、admin権限が奪われた場合の被害を抑えるため、保存型XSSを許容しない方針を維持する）。
- モバイル幅でもヘッダー・ハンバーガーメニューの操作を妨げない高さに収める。

## 閉じる（dismiss）ボタン

- バナーには閉じるボタンを付け、クリックすると`localStorage`に`tabisync_announcement_dismissed=<announcement.id>`を保存して非表示にする。
- 別の`SiteAnnouncement`が新しく表示対象になった場合（idが変われば）、dismiss状態はリセットされ再度表示される。
- JavaScript無効環境やlocalStorage利用不可の環境でも、バナー自体は常にサーバーサイドで描画される（非表示はJS側の追加処理であり、表示自体をJSに依存させない）。読み込み直後に一瞬表示されてから消える体験は許容する。

## パフォーマンス

- `announcement`context processorは全ページ（ホーム・しおり詳細に限らず）で呼ばれるが、対象外URLでは早期`return`しDBクエリを発行しない。
- 対象URLでのクエリは主キー/インデックス対象のフィルタのみで、`.only()`または必要フィールドに絞ったQuerySetにする。
- しおりの`itineraries__id=pk`によるJOINは1件のpkに対する等値検索であり、しおり件数に比例して遅くならない。
- 将来的にトラフィックが増えた場合はDjangoキャッシュ（数十秒程度のTTL）を検討できるが、本タスクの完了条件には含めない。

## 実装手順

1. `SiteAnnouncement`モデルを追加し、マイグレーションを作成する。
2. `admin.py`に`SiteAnnouncementAdmin`を登録する。
3. `context_processors.py`に`announcement`を追加し、`settings.py`の`TEMPLATES`へ登録する。
4. `templates/_announcement_banner.html`（しおりページ用の帯状バナー）を作成し、`tabisync/content/base.html`にincludeを追加する。`static/scss/layout/_announcement-banner.scss`を作成し`style_v2_1.scss`へ`@use`、`content_V2/_base.scss`へ固定ヘッダー分のクリアランスを追加する。
5. `templates/_announcement_banner_home.html`（ホーム用のMV下カードUI、公式Xへの導線つき）を作成し、`home.html`の`.home-hero`直後にincludeを追加する。`static/scss/home/_announcement.scss`を作成し`home.scss`へ`@use`する。
6. `static/js/announcement_banner.js`でdismiss処理を実装し、しおりページ・ホームの両方から読み込む。
7. SCSSをコンパイルし、`style_v2_1.css`・`home.css`とsource mapを再生成する。
8. 自動テストを追加し、手動でホーム・しおり詳細ページの両方をPC/SP幅で確認する。

## テスト

### Django / モデル・admin

- `is_active=False`のとき、表示条件を満たしていてもどのページにも表示されない。
- `starts_at`が未来、または`ends_at`が過去のとき表示されない。
- `show_on_home=True`のときホームページのcontextに現れ、しおり詳細ページのcontextには現れない。
- `show_on_all_itineraries=True`のとき、`itineraries`に含まれていない任意のしおりでも表示される。
- `show_on_all_itineraries=False`かつ`itineraries`に特定のしおりのみ指定したとき、そのしおりでのみ表示され、別のしおりでは表示されない。
- 条件を満たす`SiteAnnouncement`が複数存在する場合、`updated_at`が最も新しい1件だけがcontextに入る。
- ドキュメント系ページ（例: `qa`, `contact`）、V1しおり画面、パスワード入力画面のcontextには常に`active_announcement=None`が入る。
- `message`にHTMLタグを含む文字列を保存しても、レンダリング結果でエスケープされ実行可能なHTMLにならない。

### フロントエンド / UI

- ホームページでは`.home-hero`（MV）の直後、`.home-recent-section`より前にカードUIが表示され、公式X（`https://x.com/tabisync_com`）への導線を含む。
- しおり詳細ページでPC/SPどちらのヘッダー配下でも帯状バナーが1回だけ表示される（二重表示にならない）。
- 閉じるボタンを押すとバナーが消え、リロードしても同じ`SiteAnnouncement`である間は再表示されない。
- 別の`SiteAnnouncement`（idが異なるもの）に切り替わった場合は、以前dismissしていても再表示される。
- JavaScriptを無効化してもバナー自体は表示される。

## 検証コマンド

```bash
cd project_tabisync
pipenv run python manage.py makemigrations tabisync
pipenv run python manage.py migrate
pipenv run python manage.py check
pipenv run python manage.py test tabisync.tests.test_announcement
pipenv run python manage.py test tabisync
```

SCSS変更後はリポジトリルートで次を実行し、意図したCSSとsource mapだけが更新されていることを確認する。

```bash
npx sass project_tabisync/static/scss:project_tabisync/static/css
```

新規/変更した静的ファイル（`static/js/announcement_banner.js`等）を`{% static %}`で参照するテンプレートをDjangoテストクライアントでレンダリングする場合、`ManifestStaticFilesStorage`を使っているため事前に`collectstatic`が必要になる。

```bash
pipenv run python manage.py collectstatic --noinput
```

`staticfiles/`、`media/`、`logs/`は変更・commitしない。

## 完了条件

- Django管理画面から新規`SiteAnnouncement`を作成・編集・無効化でき、`title`/`message`/`level`/表示先（ホーム・全しおり・個別しおり）/表示期間を設定できる。
- ホームページでは`.home-hero`直後のカードUIに、しおり詳細ページ（V2）ではヘッダー直下の帯状バナーに、条件を満たすメッセージが表示される。
- ホームページのカードUIには、常に公式X（`https://x.com/tabisync_com`）への導線が表示される。
- ドキュメント系ページ、V1レガシー画面、デモ/サンプルページ、パスワード入力画面には表示されない。
- 表示期間外・`is_active=False`のときは表示されない。
- 複数の`SiteAnnouncement`が同時に条件を満たしても、バナーが重複表示されない。
- ユーザーが閉じたバナーは、同じ告知が続く間は再表示されず、新しい告知に切り替わると再表示される。
- `message`はエスケープされ、保存型XSSが発生しない。
- `home.css`（ホーム）と`style_v2_1.css`（しおりページ）の両方で、それぞれのページに合ったコンポーネントが正しく表示され、design.mdの適用範囲（`base/tokens`はホームページのみでV2アプリ本体には未適用）と矛盾しない実装になっている。
- Django自動テストが通り、SCSSに対応するCSSとsource mapが再生成されている。
