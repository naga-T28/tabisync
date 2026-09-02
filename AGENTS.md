# AGENTS.md

## この文書の目的

このファイルは、TabiSync を変更する開発者および AI エージェント向けの作業ガイドです。記載内容は現在のリポジトリから確認できた事実に基づきます。リポジトリだけでは判断できない方針は推測せず、`未定` としています。

## プロジェクト概要

TabiSync は、旅程、行きたい場所、メモ、チェックリストなどを一つの旅行しおりとして共有・編集する Django 製 Web アプリケーションです。ログインを必須とせず、しおりごとの UUID トークンと閲覧・編集パスワードを使用します。

- 本番公開URL: <https://tabisync.com>
- 表示言語: 日本語
- タイムゾーン: `Asia/Tokyo`
- Django アプリ: `tabisync`
- Django プロジェクト: `project_tabisync`
- 本番WSGIサーバー: Gunicorn
- 開発用DB: SQLite
- 非DEBUG環境の標準DB: PostgreSQL
- 静的ファイル配信: WhiteNoise、およびREADME上はNginx
- 外部連携: OpenAI Responses API、Google Maps、Cloudflare Turnstile、SMTP

## 最初に確認するファイル

作業開始時は、依頼に関係する範囲で次の順に確認してください。

1. `README.md`: プロダクトの目的と技術選定
2. `AGENTS.md`: 作業規約と検証方法
3. `project_tabisync/project_tabisync/settings.py`: 環境、DB、セキュリティ、外部設定
4. `project_tabisync/tabisync/models.py`: データモデル
5. `project_tabisync/tabisync/urls.py`: 画面・エンドポイント一覧
6. `project_tabisync/tabisync/views/`: 役割別に分割されたアプリケーション処理（`utils.py`, `itinerary_helpers.py` に共通ヘルパー、機能ごとに `itinerary_v2.py`, `schedule_v2.py`, `want_to_go.py`, `memo_v2.py`, `checklist_v2.py`, `concierge.py`, `auth.py`, `legacy_v1.py` 等）
7. AIコンシェルジュに関する依頼のみ: `project_tabisync/tabisync/concierge_agent/`（registry・agent loop・usage・tracing、`skills/`・`tools/` Markdown定義）と `project_tabisync/tabisync/concierge_tools/`（Tool実装）
8. 対象の `templates/`、`static/js/`、`static/scss/`、テスト

## ディレクトリ構成

```text
TabiSync/
├── AGENTS.md
├── README.md
├── Pipfile
├── Pipfile.lock
├── package.json
├── docker-compose.yml
├── docker-compose-staging.yml
├── containers/
│   └── django/
│       ├── Dockerfile
│       └── entrypoint.sh
├── .github/workflows/
│   └── deploy.yml
└── project_tabisync/
    ├── manage.py
    ├── project_tabisync/       # Djangoプロジェクト設定
    │   ├── settings.py
    │   ├── urls.py
    │   ├── context_processors.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── tabisync/               # メインDjangoアプリ
    │   ├── models.py
    │   ├── views/               # 役割別に分割されたview（旧views.py）
    │   ├── urls.py
    │   ├── forms.py
    │   ├── admin.py
    │   ├── openai_concierge.py
    │   ├── concierge_agent/     # AIコンシェルジュAgent基盤（registry/agent loop/usage/tracing、skills/・tools/ Markdown定義）
    │   ├── concierge_tools/     # concierge_agentのTool実装（read/proposal/ui、edit_actions共通service）
    │   ├── sitemaps.py
    │   ├── tests/                # 役割別に分割されたテスト（旧tests.py）
    │   └── migrations/
    ├── templates/
    │   ├── tabisync/
    │   │   └── content/        # 現行V2しおり画面
    │   ├── demo/
    │   ├── docs/
    │   └── contact/
    ├── static/
    │   ├── scss/
    │   │   ├── content_V1/
    │   │   └── content_V2/
    │   ├── css/                # Sassの生成物を含む
    │   ├── js/
    │   └── img/
    ├── media/                  # ユーザー生成ファイル。原則編集対象外
    └── logs/                   # 実行時ログ。原則編集対象外
```

## 現行機能とモデル

`Itinerary` が旅行しおり全体の中心です。現行V2機能では主に以下を使用します。

- `Itinerary`: 基本情報、日程、共有トークン、パスワード、QRコード、表紙画像、各種上限
- `ScheduleV2`: 日ごとの予定
- `WantToGo`: 行きたい場所と位置情報
- `MemoV2`: CKEditor 5を利用したメモ
- `ChecklistV2`: JSON文字列として保存するチェックリスト
- `ConciergeChatLog`: AIコンシェルジュの入力、判定、コンテキスト、回答ログ（run単位。`engine`列でlegacy/agentを区別）
- `ConciergeToolCallLog`: Agent経路（`engine="agent"`）でのTool呼び出し単位のログ（`ConciergeChatLog`にFK）

`TravelDate`、`Schedule`、`Memo`、`Item` とV1用テンプレート・SCSSも残っています。依頼で明示されない限り、V2の変更をV1へ展開しないでください。既存V1コードの削除や移行も行わないでください。

## 実装上の重要事項

- `Itinerary` 配下の関連データは、削除時の挙動と `related_name` を確認して変更してください。
- 閲覧用と編集用の認可は、UUIDトークン、パスワードハッシュ、セッションキーに依存します。認可確認を省略しないでください。
- 公開URL、QRコード、表紙画像、ブログ埋め込みでは、用途ごとに異なるトークンを使用しています。相互に置き換えないでください。
- `ScheduleV2.place` は任意指定で、`WantToGo` 削除時には `SET_NULL` になります。
- `MemoV2` と `ChecklistV2` は `Itinerary` と1対1です。
- チェックリストの `content` はDB上では `TextField` です。読み書き時のJSON正規化と上限チェックを維持してください。
- AIコンシェルジュには2経路があります。既定は従来どおり「安全判定 → 必要データ選択 → 回答生成」の固定3段階（`views/concierge.py::_post_legacy_mode`）。`CONCIERGE_AGENT_ENABLED`（または`CONCIERGE_AGENT_ENABLED_ITINERARY_IDS`で対象しおりを限定）を有効にすると、安全判定のあと`concierge_agent`のSkill/Tool駆動Agent loop（`_post_agent_mode`）が使われます。どちらも日次利用枠の予約・確定・解放は`concierge_agent/usage.py::DailyRunUsageService`を共通で通します。
- Agent経路のSkill/Toolは `tabisync/concierge_agent/skills/*.md` と `tabisync/concierge_agent/tools/*.md`（1 Skill = 1 Markdown、1 Tool = 1 Markdown）で定義し、`concierge_agent/registry.py`が起動時（Django system check）に検証します。ToolのMarkdown `handler`欄が指せるPython関数は`registry.py`内の許可リストに登録されたものだけです。Markdown追加・変更時は対応するPython実装（`concierge_tools/`）とこの許可リストの両方を更新してください。
- AIによる編集は、確認用の回答生成と `concierge_v2_apply_changes` による適用を分離した設計を維持してください（legacy経路の`edit_actions`、Agent経路の`propose_changes`Toolのいずれも、この分離を壊さないこと）。Agent経路の`propose_changes`はDBセーブポイント内で検証するだけで、呼び出し自体はしおりを一切変更しません。
- ユーザー向けエラーでは、非DEBUG環境に内部例外や外部APIの詳細を露出しないでください。
- `views/utils.py` には日数、1日当たり予定数、メモ、チェックリスト、画像容量などの上限定数があります。保存経路を追加する場合も同じ制約を適用してください。

## フロントエンド

- HTMLはDjango Templatesです。
- スタイルのソースは `project_tabisync/static/scss/` です。
- コンパイル済みCSSは `project_tabisync/static/css/` にあります。
- 現行しおり画面は主に `templates/tabisync/content/` と `static/scss/content_V2/` を使用します。
- JavaScriptは `project_tabisync/static/js/` にあるVanilla JavaScriptです。
- SCSSを変更した場合は対応するCSSとソースマップを再生成し、意図した生成物だけをコミット対象にしてください。
- V2だけの変更を `content_V1/` に加えないでください。

## セットアップと開発コマンド

Python 3.8とPipenvがリポジトリ上の基準です。

```bash
pipenv install --dev
cd project_tabisync
pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

Sassの監視はリポジトリルートで実行します。

```bash
npm install
npm run sass:watch
```

単発コンパイル例:

```bash
npx sass project_tabisync/static/scss:project_tabisync/static/css
```

## 検証

変更範囲に応じて、最低限以下を実行してください。

```bash
cd project_tabisync
pipenv run python manage.py check
pipenv run python manage.py test tabisync
```

モデル変更時:

```bash
pipenv run python manage.py makemigrations --check --dry-run
```

注意事項:

- `package.json` の `npm test` は未設定で、常にエラー終了します。検証コマンドとして使用しないでください。
- テストは `project_tabisync/tabisync/tests/` 配下に、対象view/機能ごとにファイル分割されています。
- 外部APIを呼ぶテストでは実通信を避け、モックを使用してください。
- UI変更では自動テストに加え、対象ページのモバイル・デスクトップ表示と主要操作を手動確認してください。

## データベース変更

- モデル変更にはDjango migrationを追加してください。
- 既存migrationを後から書き換えず、新しいmigrationで変更してください。
- データ削除や後方互換性を失う変更は、明示的な依頼なしに実施しないでください。
- `db.sqlite3`、`media/`、`logs/` は実行時データであり、ソース変更として扱わないでください。
- コンテナのentrypointは起動時に `makemigrations` と `migrate` を実行しますが、migrationファイルは開発時に生成・確認してリポジトリへ含めてください。

## 環境変数と秘密情報

`.env` の内容を表示、コミット、ログ出力しないでください。確認できる主な設定項目は以下です。

- Django: `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `USE_HTTPS`
- SEO: `PUBLIC_BASE_URL`（任意の非秘密値。例: `https://tabisync.com`。canonical・OGP・構造化データ・サイトマップ・robots.txtが参照する単一の公開オリジン。本番環境では`https://`始まりの値が必須で、未設定または不正な値だと起動時に例外になる。開発環境では未設定時`http://localhost:8000`を既定値として使う）、`ENVIRONMENT`（任意だが公開本番では`production`を必ず明示する。未設定・`staging`・`development`など`production`以外では全レスポンスに`X-Robots-Tag: noindex, nofollow`を付与する）
- Database: `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Email: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `CONTACT_RECEIVER_EMAIL`
- Google Maps: `GOOGLE_MAPS_API_KEY`
- Turnstile: `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `CLOUDFLARE_TURNSTILE_SECRET_KEY`, `TURNSTILE_TIMEOUT_SECONDS`（任意。検証APIのHTTPタイムアウト秒数。既定`5`）
- OpenAI: `OPENAI_API_KEY`, `OPENAI_LIGHT_MODEL`, `OPENAI_ANSWER_MODEL`、各プロンプト・タイムアウト設定
- AIコンシェルジュAgent経路（`concierge_agent`。任意、未設定時は全て安全側の既定値でlegacy経路のまま動作）:
  - `CONCIERGE_AGENT_ENABLED`（既定`false`）: Agent経路のグローバル有効化フラグ
  - `CONCIERGE_AGENT_ENABLED_ITINERARY_IDS`（既定空、カンマ区切りpk一覧）: 設定時はこの一覧のしおりのみAgent経路になり、`CONCIERGE_AGENT_ENABLED`より優先される（内部QAや限定公開向け）
  - `OPENAI_AGENT_MODEL`（既定`gpt-5.6-luna`。`OPENAI_ANSWER_MODEL`とは独立）: Agent loopのtool-callingステップで使うモデル
  - `OPENAI_AGENT_STEP_TIMEOUT_SECONDS`（既定は`OPENAI_ANSWER_TIMEOUT_SECONDS`と同じ）: Agent loop1ステップあたりのタイムアウト
  - `CONCIERGE_AGENT_MAX_OPENAI_CALLS_PER_RUN`（既定`6`）: 1 run（1リクエスト）あたりのOpenAI呼び出し回数上限
  - `CONCIERGE_AGENT_MAX_TOOL_CALLS_PER_RUN`（既定`6`）: 1 runあたりのTool呼び出し回数上限（Skill Markdownの`max_tool_calls`との小さい方が実際に適用される）
  - `CONCIERGE_AGENT_MAX_RUN_SECONDS`（既定`25`）: 1 run全体の経過時間上限
  - `CONCIERGE_AGENT_WEB_SEARCH_ENABLED`（既定`true`）: OpenAI組み込み`web_search` toolをAgentへ付与するかどうか(task-012)
  - `CONCIERGE_AGENT_MAX_WEB_SEARCH_PER_RUN`（既定`2`）: 1 runあたりのweb_search呼び出し回数上限(課金対象tool、$10/1,000call相当)
- Upload/Input: `MAX_COVER_IMAGE_UPLOAD_BYTES`, `MAX_REQUEST_BODY_BYTES`, `MAX_JSON_BODY_BYTES`（いずれも任意。`MAX_JSON_BODY_BYTES`はJSON API本文の上限で、既定256KiB）
- Gunicorn: `GUNICORN_TIMEOUT`, `GUNICORN_GRACEFUL_TIMEOUT`
- Proxy: `TRUSTED_PROXY_CIDRS`（任意。カンマ区切りのCIDR一覧、例: `10.0.0.0/8,192.0.2.10/32`。レート制限等のクライアントIP判定で `CF-Connecting-IP`/`X-Forwarded-For` を信頼してよい直前ホップの範囲を指定する。未設定時は転送ヘッダーを一切信頼せず `REMOTE_ADDR` のみを使用する安全側の既定値になる。外側Nginx等のリバースプロキシが到達するアドレス範囲を設定すること）

新しい環境変数を追加した場合は、秘密値を記載せず変数名、用途、必須か任意かをこの文書またはREADMEへ追記してください。

## Dockerとデプロイ

- Djangoイメージは `containers/django/Dockerfile` で構築します。
- `docker-compose.yml` は本番向け、`docker-compose-staging.yml` はステージング向けの構成です。
- GitHub Actionsの `.github/workflows/deploy.yml` は、`main` を本番、`test` をステージングとしてVPSへデプロイします。
- デプロイはrsync、Docker Compose再ビルド、外側のNginx等を含む `~/web_app` の起動で構成されています。
- デプロイ、GitHub Secrets、VPS、外部サービスの状態変更は、明示的な依頼と権限なしに実施しないでください。
- Cloudflare経由でのアクセスを前提とする場合（`CF-Connecting-IP` を使ったクライアントIP判定・レート制限が機能するため）、オリジンサーバー（外側Nginx）への直接アクセスをCloudflareのIPレンジ以外から遮断するようファイアウォール/Nginx設定で構成すること。直接アクセスを許してしまうと、攻撃者が任意の `CF-Connecting-IP`/`X-Forwarded-For` を送信してレート制限を回避できる。あわせて `TRUSTED_PROXY_CIDRS` に、Django（Gunicorn）へ到達する直前ホップ（外側Nginx等）のアドレス範囲を設定すること。この項目は現在のリポジトリだけでは実際のVPS/Nginx設定を確認できないため、デプロイ担当者が実環境に合わせて設定・確認する。

## 変更時のルール

- 作業前に `git status --short` を確認し、ユーザーの既存変更を保持してください。
- 依頼と無関係なファイルを整形・修正しないでください。
- 生成済みCSSに既存差分がある場合、SCSSコンパイルによる広範な上書きに注意してください。
- `views/` を変更するときも、依頼と関係するビューとヘルパーに範囲を限定してください。
- URL名、テンプレート名、`related_name` は複数箇所から参照されるため、変更前にリポジトリ全体を検索してください。
- セキュリティ、パスワード、トークン、レート制限、入力上限を弱める変更は行わないでください。
- 実装変更には、可能な範囲で回帰テストを追加してください。

## 現在確認できるテスト対象

- プロキシヘッダーを考慮したクライアントIP取得
- 非DEBUG環境での公開エラーメッセージ
- AIコンシェルジュの安全判定プロンプト
- コンシェルジュ入力の文字数制限
- 会話履歴の正規化
- V2チェックリスト保存
- しおりの閲覧/編集アクセス制御（`views/access_control.py`。V1/V2共通のセッションキー生成、パスワード再設定後の旧セッション失効、閲覧・編集ゲートの権限表）
- AIコンシェルジュAgent経路（`tests/test_concierge_agent_registry.py`: Skill/Tool Markdown定義の検証・system check、`tests/test_concierge_tools.py`: 各Toolのitineraryスコープ・座標非公開・propose_changesの非DB変更、`tests/test_concierge_agent_loop.py`: Agent loopの停止条件・未許可Tool拒否・キャッシュ・ui_components/edit_actionsの再構成、`tests/test_concierge_usage_limits.py`: run内利用上限と日次予約サービス、`tests/test_concierge_view_flag.py`: feature flag分岐とlegacy/agent両経路のview統合）

## テスト実行時の注意

- `manage.py test` 実行時は `RATELIMIT_ENABLE = False`（`settings.py`で`sys.argv`から判定）となり、`django_ratelimit` によるレート制限は無効化される。レート制限用キャッシュ(LocMemCache)はテストプロセス全体で共有されるため、有効なままだとテスト実行順序によって無関係なテストが偶発的に403で失敗しうるための対応。レート制限そのものの挙動を検証するテストは現状存在しない。

## 未定事項

以下は現在のファイル構成だけでは確定できません。

- コードフォーマッターとLintの正式ルール: 未定
- PythonおよびJavaScriptのコーディング規約: 未定
- 型チェックツールと適用範囲: 未定
- テストカバレッジの目標値: 未定
- 対応ブラウザと最低バージョン: 未定
- アクセシビリティの達成基準: 未定
- ブランチ命名規則: 未定
- コミットメッセージ規約: 未定
- Pull Requestのレビュー・承認ルール: 未定
- `main`、`test` 以外のブランチ運用: 未定
- リリース番号と変更履歴の運用: 未定
- 本番・ステージング環境の責任者: 未定
- 障害時の連絡先とエスカレーション手順: 未定
- DBバックアップ、保存期間、リストア手順: 未定
- ログ監視、メトリクス、アラートの運用: 未定
- OpenAI APIの費用上限と障害時運用: 未定
- 個人情報・コンシェルジュログの保存期間と削除方針: 未定
- V1機能の廃止・移行予定: 未定
- ユーザーアカウント機能の導入時期と認証方式: 未定
- プロダクトロードマップと機能優先順位: 未定
