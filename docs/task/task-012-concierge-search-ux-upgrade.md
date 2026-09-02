# Task 012: AIコンシェルジュのWeb検索対応とチャットUX刷新

- 種別: 機能追加 / AI / UI
- 優先度: High
- 対象: Skill/Tool駆動AIコンシェルジュ(`concierge_agent`, agent mode)
- 対象外: legacy(固定3段階)経路への遡及適用、画像生成機能、サーバー側の真のトークンストリーミング、ユーザーアカウント機能

## 目的

現行のAIコンシェルジュ(task-001で導入したSkill/Tool駆動Agent)に対し、以下4点を追加する。

1. 質問内容に応じて`gpt-5.6-luna`モデル+OpenAI組み込み`web_search` toolで最新情報を検索できるようにする。
2. 回答を表・引用・強調などで読みやすく整形する(画像生成は費用対効果の都合で今回は非対応)。
3. 回答文がブラウザ側で少しずつ表示される疑似タイプライター演出を追加する(サーバー側の真のストリーミングは行わない)。
4. 左サイドバーにChatGPT風の会話一覧(新規チャット・切替・削除)を追加する。しおりごとに`localStorage`で管理し、サーバー側の会話一覧APIは新設しない。

## 現状

- `tabisync/concierge_agent/agent.py`が独自function-calling loopを実装し、`OPENAI_AGENT_MODEL`(既定`gpt-5-mini`相当)を使う。組み込みtool(`web_search`等)は未使用。
- `templates/tabisync/content/concierge_v2.html`は単一会話のみを`localStorage`(`tabisync_concierge_history_<itineraryId>`)に保持し、サイドバーはない(`.concierge-side-panel`はCSS上`display:none`で未使用)。
- レスポンスは`fetch`で一括JSONを受け取り、即座に全文をDOMへ描画している(ストリーミングなし)。
- Markdown描画は独自の軽量パーサ(`renderMarkdown`)で見出し・リスト・強調・リンク・コードのみ対応。表・引用ブロックは未対応。

## 採用方針

### モデルとWeb検索

- `gpt-5.6-luna`(2026-07-09公開、web_search/tool calling/structured outputs対応、$0.20/$1.20 per 1M tokens)をAgentの既定モデルにする。`OPENAI_AGENT_MODEL`環境変数で上書き可能な既定値として設定し、legacy経路(`OPENAI_ANSWER_MODEL`)には影響させない。
- OpenAI組み込み`web_search` tool(Responses API, $10/1,000 call相当)をAgentのtool一覧へ常時追加し、`tool_choice: "auto"`のままモデル自身に要否を判断させる(「質問に応じて」の実現)。Skill Markdown側の変更は不要(全Skill共通のrun capabilityとして付与)。
- 1 run(=1ユーザーリクエスト)あたりのweb_search呼び出し上限を環境変数`CONCIERGE_AGENT_MAX_WEB_SEARCH_PER_RUN`(既定2)で制御する。上限到達後の反復では該当toolをpayloadから外す。既存の`RunUsageCounters`/`max_run_seconds`/`max_tool_calls`と同じ「run単位でサーバー側が強制」という設計方針を踏襲する。日次・月次の金額ベース上限(task-001が言及する`UsagePolicy`/`UsageEvent`基盤)は本タスクの対象外とし、将来別タスクで対応する。
- `web_search`はOpenAI側で実行される組み込みtoolのため、既存のfunction tool registry(`concierge_tools`のPython handler)には追加しない。`function_call`/`function_call_output`の往復は発生せず、1回のResponses API呼び出し内で完結する。
- レスポンスの`output_text`アノテーション(`url_citation`)から出典(title/url)を抽出し、`citations`として最大5件までクライアントへ返す。モデルが生成した任意HTML/URLをそのまま信用せず、Responses APIが構造化して返すannotationのみを使う。

### 回答の見やすさ

- 画像生成(`gpt-image-1-mini`等)は追加費用が発生するため、ユーザー判断により本タスクでは実装しない。
- 既存の安全なMarkdownサブセットレンダラーを拡張し、表(`| a | b |`形式)・引用ブロック(`>`)・水平線に対応する。モデル生成HTMLの直接描画(`innerHTML`への生HTML注入)は導入しない、という既存方針(task-001)を維持する。
- Web検索を使った回答では出典リンクを本文と分離した「参照」欄に表示する。

### 疑似タイプライター表示

- サーバー側は現行どおり完了済みJSONを一括で返す(Django Viewの同期構成・タイムアウト・利用上限予約ロジックを変更しない)。
- クライアント側で、描画済みDOMのテキストノードを単語単位の`span`へ分割し、`opacity`を順次切り替えることで表示アニメーションを行う。文字列の再パースは行わない(壊れたHTMLの一瞬表示を防ぐ)。
- 会話履歴の復元時(ページ再訪問時)はアニメーションなしで即時表示する。UIコンポーネント(地図)・変更適用ボックス・参照欄は本文アニメーション完了後に表示する。

### 会話サイドバー

- しおりごとに`localStorage`のキー`tabisync_concierge_conversations_<itineraryId>`へ、`{ [conversationId]: { title, updatedAt, messages: [...] } }`の形式で複数会話を保持する。
- 既存の単一会話キー(`tabisync_concierge_history_<itineraryId>`)からの移行処理を行い、既存データを最初の会話として取り込む。
- サイドバーに「新しいチャット」ボタン・会話一覧(タイトル=先頭のユーザー発言を要約、更新日時)・削除ボタンを表示する。PCでは常設パネル、スマホでは既存の`content-side-nav`と同様の開閉トグルにする。
- サーバー側の会話一覧・履歴取得APIは新設しない(既存`ConciergeChatLog`はrunログのままとし、UI用の会話一覧はクライアント側で完結させる)。将来サーバー同期が必要になった場合は別タスクとする。

## 実装ステップ

1. `tabisync/concierge_agent/agent.py`
   - `OPENAI_AGENT_MODEL`の既定値を`gpt-5.6-luna`にする(env上書き可)。
   - `web_search` built-in toolをtool一覧へ付与するヘルパーを追加し、`build_agent_step_payload`/`force_final_answer`で使う。
   - `output`から`web_search_call`アイテム数を数えて`RunTrace`へ記録し、run内上限に達したら以後の反復でtoolを外す。
   - `output`内の`url_citation`アノテーションを集約し、`AgentRunResult.citations`として返す。
   - `INSTRUCTIONS_PREFIX`にWeb検索の使用条件(しおり内データにない最新情報のときのみ、出典を明示)を追記する。
2. `tabisync/concierge_agent/tracing.py`
   - `RunTrace`に`web_search_call_count`を追加し、記録用メソッドを足す。
3. `tabisync/models.py` + migration
   - `ConciergeChatLog.web_search_call_count`(`PositiveIntegerField`, default 0)を追加する。
4. `tabisync/views/concierge.py`
   - `_post_agent_mode`で`web_search_call_count`をログへ渡し、JSONレスポンスへ`citations`を追加する。
5. `templates/tabisync/content/concierge_v2.html`
   - サイドバーDOMとトグルボタンを追加する。
   - `localStorage`を複数会話対応へ書き換え、移行処理を実装する。
   - Markdownレンダラーに表・引用ブロック対応を追加する。
   - `citations`のレンダリングを追加する。
   - 疑似タイプライター表示を実装する(新規メッセージのみ、履歴復元時は即時表示)。
6. `static/scss/content_V2/_concierge.scss`
   - サイドバーレイアウト(`.concierge-side-panel`を有効化)、会話一覧、表・引用ブロック、参照欄、タイプライター用スタイルを追加する。
   - `sass`でコンパイルし、対応する`static/css/style_v2_1.css`とsource mapのみを更新する。

## テスト

- `pipenv run python manage.py check`
- `pipenv run python manage.py makemigrations --check --dry-run`(models.py変更後は先にmigrationを作成)
- `pipenv run python manage.py test tabisync.tests.test_concierge_agent_loop tabisync.tests.test_concierge_view_flag tabisync.tests.test_concierge_usage_limits`
- Agent loopのunit testで、`web_search` toolがpayloadへ含まれること・run内上限で除外されること・`web_search_call`アイテムがcitationsへ正しく変換されることをモックで確認する。
- ブラウザ確認: 新規チャット作成、複数会話の切替・削除、タイプライター表示、表/引用の描画、地図UIコンポーネントとの共存、モバイルでのサイドバー開閉。

## 完了条件

- Agentがrun単位の上限内でWeb検索を自律的に使い分け、出典付きで回答できる。
- 回答が表・引用ブロックなどで読みやすく整形され、モデル生成の生HTMLは引き続き描画されない。
- 新規メッセージが疑似タイプライールで表示され、履歴復元時は即時表示される。
- 左サイドバーから複数会話の作成・切替・削除ができ、しおりを跨いだ会話混入がない。
- 既存の日次利用上限・run内Tool上限・エラー秘匿・ガードレールに回帰がない。
