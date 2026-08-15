# TabiSync プロダクト戦略

> 状態: 調査・意思決定用の提案書。実装仕様ではない。
>
> 基準日: 2026-08-14
>
> 対象リビジョン: ブランチ dev-free-map / commit 3b6e25e

## 1. 文書の目的

本書は、TabiSyncを「AI付き旅行しおり」から、次の価値に集中するプロダクトへ転換できるかを、現行コード、公開競合情報、LINE公式仕様に基づいて判断するための文書である。

> LINEに散らかった「行きたい」を、参加者ごとの希望と未決定事項が見える旅程に変え、幹事だけに偏った整理・調整を前へ進める。

結論だけでなく、維持する資産、足りないドメイン、MVP、段階的な検証、セキュリティ・プライバシー、Go/No-Go条件まで定義する。今回は調査と方針策定のみを対象とし、コード、モデル、マイグレーション、既存機能、Issue、外部環境には変更を加えない。

本書では事実と提案を混同しないため、次のラベルを使う。

| ラベル | 意味 |
|---|---|
| **実装済み** | 対象リビジョンのコードと呼び出し経路を確認した |
| **一部実装** | 構成要素はあるが、想定体験または運用要件を満たさない |
| **未実装** | リポジトリ内に対応するモデル、URL、View、UI、設定を確認できない |
| **未確認** | リポジトリ外の本番設定、利用実績、契約状態など、コードだけでは判定できない |
| **追加調査が必要** | 公式仕様、規約、実環境、ユーザー行動の確認が意思決定に必要 |
| **提案** | 本書で新たに推奨する設計またはプロダクト判断 |

## 2. 調査日

- リポジトリ調査日: 2026-08-14
- 競合公開情報の確認日: 2026-08-14
- LINE Developers公式情報の確認日: 2026-08-14
- 注意: 競合機能、料金、LINEの仕様・規約は変更される。実装着手時と公開前に再確認する。

## 3. 調査対象

### 3.1 リポジトリ

以下を読み取り調査した。

- AGENTS.md、README.md、design.md
- docs/task/、docs/fix/、.github/workflows/deploy.yml
- project_tabisync/project_tabisync/settings.py、urls.py と project_tabisync/tabisync/middleware.py
- project_tabisync/tabisync/models.py、urls.py、forms.py
- project_tabisync/tabisync/views/ 以下の作成、認可、V2旅程、予定、行きたい場所、メモ、チェックリスト、AIコンシェルジュ
- project_tabisync/tabisync/concierge_agent/ と concierge_tools/
- project_tabisync/templates/、static/js/、static/scss/ の関連箇所
- project_tabisync/tabisync/tests/ の関連テスト
- Pipfile、package.json、Dockerfile、docker-compose*.yml、entrypoint.sh

CLAUDE.md はリポジトリ内に存在しなかった。調査開始時点で作業ツリーには既存の未コミット変更があったため、それらを利用者の変更として保持し、本書の新規追加以外は触れていない。docs/product-strategy.md は存在しなかったため、指定名で新規作成した。

調査開始時点のGit状態は branch dev-free-map、HEAD 3b6e25e。既存変更は design.md、static/css/home.css(.map)、static/css/style.css(.map)、static/scss/layout/_site-footer.scss、tests/test_static_pages.py、views/static_pages.py、templates/_site_footer.html、base-noindex.html、base.html、base_home.html である。本書作成中にこれらを変更していない。

### 3.2 外部情報

- tabiori、Wanderlog、NAVITIME Travel、AVA Travel、Funliday
- Google Maps共有リスト、Googleスプレッドシートを使う代替運用
- タビノワ、tabitte、TabinoTe
- 公開検索で確認できるLINE上の旅行関連Bot
- LINE DevelopersのMessaging API、LINE Login、LIFF、料金、規約・ユーザーデータポリシー

### 3.3 調査上の限界

- 本番・ステージングのNginx、Cloudflare、VPS、監視、環境変数、LINE公式アカウント契約は確認していない。
- データベースの実利用データ、GA4、Search Console、問い合わせ、継続率は確認していない。
- テストコードと対象範囲は読んだが、今回は文書作成のみのためtest suiteは実行しておらず、現HEADでのpass結果は確認していない。
- 競合の非公開仕様、有料機能の実機挙動、最新の審査条件は公開情報以上に断定しない。
- LINEのグループ識別子を24時間以上保存できるかは、公式文書間でプロダクト設計上の解釈余地がある。第17・18・29節のGo/No-Go条件を参照すること。

## 4. エグゼクティブサマリー

### 4.1 判断

**新しいポジショニングは、条件付きで妥当である。** TabiSyncには、登録なしで開ける共有URL、旅行単位のデータ構造、候補・地図・予定・メモ・持ち物、モバイル向けWeb画面、提案と適用を分離したAI基盤がある。このため、LINEを入口、Webを共同意思決定と詳細編集の場にする構成は、既存資産を活かせる。

ただし、差別化の中心は「LINE Bot」でも「AIで旅程を自動生成」でもない。中心に置くべきなのは、次の一連の仕事である。

1. 会話に散らかった候補を構造化する。
2. 誰が何を望むかを、登録負担を抑えて集める。
3. 決定・見送り・確認待ちと未決定事項を可視化する。
4. 複数案とトレードオフを示し、人が選ぶ。
5. 採用案を既存の旅程へ安全に反映する。

### 4.2 最大の再設計点

現行の「行きたい度」は候補ごとに1つの1〜5値であり、参加者ごとの投票ではない。参加者、提案者、投票、候補ステータス、制約、合意、複数の旅程案、プロダクトイベント、LINE連携は未実装である。つまり最大のギャップはBotの受信処理ではなく、**複数人の意思決定を表現するドメインモデルと権限・識別**である。

### 4.3 推奨する順序

- Phase 0で、5〜10組のユーザー検証、イベント計測設計、LINE技術検証、規約照会を行う。
- Phase 1のWeb意思決定基盤と、Phase 2のLINE薄型Botの技術スパイクを一部並行する。
- 製品MVPは、**日付未定draft**、ゲスト参加、提案者、参加者別投票、候補ステータス、未決定事項、権限分離、安全なManager取得・復旧と、Botの参加・メンション・作成・リンク返信だけを垂直に接続する。draftはPhase 0で既存V2への影響を監査し、成立しない場合は実装前にMVPそのものを再承認する。
- Google Maps短縮URL解析はPhase 3、AI幹事と複数案はPhase 4へ送る。構造化された希望がない段階でAIを先行させない。
- 全参加者へのLINE Login、LIFF、LINEミニアプリはMVP必須ではない。通常のWebと署名付きゲスト参加で仮説を検証する。ただしgroup command senderのManager claimを他方式で安全に成立させられない場合、Managerだけの最小本人連携は公開条件として再評価する。

### 4.4 重大なGo/No-Go条件

LINE User Data Policy 3.2.3は、LINEユーザ情報のうち「友だち情報、グループ情報」を明示の有無にかかわらず24時間以上保存してはならないと定める。一方、Messaging APIはWebhookで groupId を返し、pushの宛先にも使う。公式FAQは groupId をLINE Platformが生成するグループ識別子と説明するが、groupIdが同ポリシー上の「グループ情報」なのか、保存可能な内部識別子なのかは、確認した公式文面だけでは解決しない。

したがって、**groupIdを永続保存して「1グループ＝進行中のしおり1件」を実装できると断定しない。** Phase 0でLINEヤフーの公式窓口から書面回答を得ることを、LINE中心戦略のGo/No-Go条件とする。ハッシュ化・暗号化は漏えい対策であり、保存禁止の適法化手段とはみなさない。許可されない場合は、24時間未満の一時コンテキストと、都度ユーザーがしおりコードを指定する縮退案に切り替えるが、体験価値は下がる。

同様に、LINE由来メッセージをOpenAI等へ送る場合、LINE User Data Policy 3.4の第三者開示制限と、必要な業務委託先への開示を条件付きで認める3.4.2の適用条件、委託先への義務flow-down、LINE公式アカウントAPI利用規約上の同意・利用目的との整合を確認する必要がある。OA API利用規約がLINE利用者messageの外部AI委託を一律禁止すると本書では解釈しないが、**一般公開版でLINE文面を外部AI処理することは、LINE・法務の確認まで保守的にNo-Go**とする。Web上で本人が改めて入力・同意したTabiSyncデータをAIへ送る経路とは分けて評価する。

さらに現行コードは、Google Maps JavaScript APIのPlacesService/AutocompleteServiceで取得した名称・住所・緯度経度等を保存し、MapLibre/OpenFreeMap上へ表示する。GoogleのCore Services Summaryは「Places API via Places Library, Maps JavaScript API」をCore Serviceとして列挙する。2026-08-14時点のGoogle Maps Platform固有規約は、Places API contentをnon-Google mapと併用しないこと、Places由来の緯度経度cacheを30日までとすることを記載する。これはlat/lngだけの一時的な例外で、name/address/rating等の包括的な永続保存許可ではない。Maps JavaScript API policyはcontentのcache/storageを原則制限し、place_idを例外とし、user session外でPlace Nameを持続化すると禁止されたscrapingになり得ると説明する。Places UI Kitにはnon-Google map併用の明示例外があるが、現コードは同Kitではない。**現行構成が契約に適合するかは断定せず、既存運用を含むGoogle/法務・attribution・保存field/provenance監査をPhase 0のGo条件へ加える。** 違反と断定して既存dataを削除せず、許容されるprovider構成を確認する。

### 4.5 北極星指標

提案された「作成されたしおりのうち、2人以上が候補追加、投票、編集のいずれかを行った割合」は戦略に合う。ただし、同一人物の複数セッションや閲覧だけを成果にしないため、次のように定義する。

> **7日以内の意味ある共同参加率** = 有効なしおりのうち、作成から7日以内に、識別可能な2人以上が候補追加・参加者別投票・候補ステータス提案・予定編集のいずれかを行ったしおりの割合

テスト、スパム、即時削除を除外し、同一ゲストの重複を抑える。LINE導入率やAI実行率は補助指標であり、北極星そのものにしない。

## 5. TabiSyncの現状

### 5.1 機能・技術の実装判定

| 対象 | 状態 | コードから確認した事実・根拠 | 新戦略への含意 |
|---|---|---|---|
| ブラウザ利用 | **実装済み** | Django TemplatesとV2画面。project_tabisync/templates/tabisync/content/ | Webを詳細操作面として再利用できる |
| Bootstrap | **未実装 / 既存想定の誤り** | Pipfile/package.jsonおよびTemplateにBootstrap依存・読込を確認できない。独自SCSS、Vanilla JS、Font Awesome、Driver.jsを使用 | 「Bootstrapを維持」という前提ではなく、既存HTML/SCSS/JSを壊さない |
| しおり作成 | **実装済み** | views/itinerary_v2.py の CreateView、forms.py。タイトル・開始日・終了日を要求し、最大30日 | Botの「旅行名だけで仮作成」と不一致。日付未定ドラフトが必要 |
| URL共有・QR | **実装済み** | Itinerary.token、build_itinerary_share_url、content.html の Web Share API・コピー、QR生成 | LINE返信に使えるが、トークン設計の強化が必要 |
| 閲覧・編集権限 | **一部実装** | views/access_control.py の ViewPasswordRequiredMixin、EditPasswordRequiredMixin、パスワードハッシュ指紋付きセッション | 閲覧/編集ゲートは再利用可能。参加URL、個人識別、権限ロール、失効・再発行はない |
| アカウント登録なし | **実装済み** | ItineraryにユーザーFKはなく、UUID URLと任意パスワードで利用 | 初期ターゲットと合う。一方、投票者の一意性と復帰識別が弱い |
| ユーザー認証 | **未実装** | Django authは依存にあるが、利用者向けlogin/register URL、Itinerary owner FKを確認できない | Guestを基本にし、強い本人連携は後から選択可能にする |
| 行きたい場所CRUD | **実装済み** | views/want_to_go.py の WantToGoV2View、モデル WantToGo、入力上限としおりスコープ検証 | 候補エンティティとして活用可能 |
| 場所検索 | **実装済み / 規約適合は追加調査** | want_list.html のGoogle Maps JS PlacesService/AutocompleteService/Details。名称・住所・座標等をWantToGoへ保存 | Google Places固有規約のnon-Google map併用、cache、attribution、料金を現行運用も含め即時監査 |
| 表示地図 | **実装済み / provider組合せは追加調査** | static/js/map_renderer.js、MapLibre GL JS、settings.py のOpenFreeMap style設定。Places由来座標をmarkerへ使用 | 「Google Maps表示」という既存想定は不正確。UXは維持対象だが、現provider組合せを無条件に維持とはしない |
| カードとピン連携 | **実装済み（限定的）** | want_list.html の openModalFromCard、marker click、setVisible。同じ詳細modalを開くが、選択ハイライトや相互スクロールはない | 候補比較UIの土台になる |
| Dayフィルタ・予定日未定 | **実装済み** | WantToGo.planned_day、0を未定として扱うUI、カードとマーカーを同時フィルタ | 「未決定」を日付以外へ広げる必要がある |
| 候補の行きたい度 | **一部実装** | WantToGo.priority は候補ごとに単一の1〜5 | 参加者別の4段階希望投票とは別物。移行時も意味を上書きしない |
| スケジュール | **実装済み** | ScheduleV2、ScheduleV2EditView、1日15件上限、WantToGoへの任意FK、日別表示 | 決まった案の反映先として使える |
| 日別地図・経路リンク | **実装済み** | content.html の updateScheduleMap、Google Maps route URL生成 | 旅行中の閲覧価値を維持 |
| メモ | **実装済み** | MemoV2、MemoV2View/EditView、JSON正規化と上限 | 自由記述の逃げ場として維持。意思決定データの代用にはしない |
| 持ち物 | **実装済み** | ChecklistV2、ChecklistV2View/EditView、JSON文字列と上限 | 旅行実行面の既存価値 |
| AIコンシェルジュ | **実装済み** | ConciergeV2View。legacy 3段階とfeature flag下のSkill/Tool Agent経路 | 既存データ読取と変更提案基盤を再利用可能 |
| AIの確認後適用 | **実装済み** | concierge_tools/proposal_tools.py の propose_changes はsavepoint内検証のみ、concierge_v2_apply_changes で編集権限を再確認して適用 | AI幹事の「勝手に確定しない」原則と一致 |
| 外部の営業時間・天気・経路調査 | **未実装** | Agent toolsは保存済み旅程・予定・候補・メモ・持ち物の読取と提案が中心 | 雨天案や現実的最適化には信頼できるデータ源が別途必要 |
| モバイル表示 | **実装済み** | V2 SCSS、960px以下のモバイルナビ、レスポンシブTemplate | LINE内ブラウザの実機検証は別途必要 |
| V2オフライン | **未実装** | Service Worker登録と対象URLは主にV1経路。V2を包含しない | 旅行中機能の弱点だがMVPの差別化対象ではない |
| Django/PostgreSQL/SQLite | **実装済み** | settings.py、Pipfile、docker-compose*.yml | 通常のドメイン追加は可能 |
| Docker/Gunicorn/WhiteNoise | **実装済み** | containers/django、entrypoint.sh、settings.py | Webhook用の本番構成に拡張余地あり |
| Nginx | **未確認** | READMEとdeploy workflowは外側Nginxを前提とするが設定本体はリポジトリ外 | Webhook body、timeout、IP、HTTPS設定を実環境確認 |
| Cloudflare | **一部実装 / 未確認** | Turnstile、TRUSTED_PROXY_CIDRS、CF-Connecting-IP処理は存在。オリジン制限はリポジトリ外 | LINE WebhookをWAFで誤遮断しない検証が必要 |
| Rate Limit | **実装済み（一部機能）** | django-ratelimit、作成・AI等のIPレート制限、テスト時無効化 | group/user/channel単位、費用上限、Webhook用制御は新規 |
| 自動テスト | **テストコードあり（実行結果は未確認）** | access control、WantToGo/Scheduleのscope・競合、Memo/Checklist、AI agent/tools/usage、proxy、Turnstile、SEO等のtestsを確認。今回は実行していない | LINE、Participant/Vote/Status、token lifecycle、product event、rate-limit発火、browser E2Eのtestは未実装 |
| CI test gate | **未実装 / 未確認** | deploy workflowは確認できるが、test/checkを必須にするworkflowを確認できない。npm testは失敗するplaceholder | security-sensitive Bot公開前に別Issueで整備 |
| ログ | **一部実装** | 本番WARNINGログ、ConciergeChatLog、ConciergeToolCallLog | LINEイベント、監査、プロダクトファネルはない。生メッセージをログへ流さない設計が必要 |
| アクセス解析 | **一部実装** | base.htmlにGA4 ID。base_home.htmlとV2系baseには同等の計測を確認できない | 現在のファネルを測れず、UUID URL漏えいにも注意 |
| 秘密URL画面の第三者script | **実装済み / リスク監査が必要** | V2 base.htmlでGoogle AdSense、AMP広告、CDN scriptを読み込む。ページURL/DOMへ同一ページ上の第三者JavaScriptがアクセスし得る | 新しいjoin/manage画面は広告・第三者analyticsなしを既定にし、既存V2もCSP、Referrer、送信先、同意を監査 |
| プロダクトイベント | **未実装** | 汎用イベントモデル/送信層を確認できない | Phase 0の先行課題 |
| LINE連携 | **未実装** | LINE設定、SDK、Webhook URL、モデル、テストを確認できない | 技術・規約スパイクから開始 |
| 非同期処理基盤 | **未実装** | Celery/RQ/Redis等のqueue/workerを確認できず、外部API処理は同期 | Webhook受付とAI/外部URL処理の分離が必要 |
| リアルタイム共同編集 | **未実装** | WebSocket/SSE/polling/version制御なし。メモ・リストはJSON全体のlast-write-wins | まず投票等を行単位にし、全画面リアルタイム化は避ける |
| 外部API | **一部実装** | OpenAI Responses API、Google Places/Maps deep link、OpenFreeMap/MapLibre、Turnstile、SMTP、GA/Ads/CDN等を確認。qrcode import失敗時はapi.qrserver.com fallback。LINEはなし | API key制限、請求alert、保持/利用規約、本番可用性は未確認。QR fallbackは秘密URLを外部送信し得る |
| 参加者・投票・候補状態 | **未実装** | 該当モデル/URL/UIなし | 新戦略の中核ギャップ |

### 5.2 現行データの関係

- Itinerary がしおり全体の中心で、UUID token、任意の閲覧/編集パスワード、日程、上限、QR、表紙、blog tokenを持つ。
- ScheduleV2 は Itinerary に多対1で、任意に WantToGo を参照する。WantToGo削除時はSET_NULL。
- WantToGo は Itinerary に多対1で、Place ID、名称、住所、緯度経度、評価、メモ、予定日、滞在時間、単一priority、tagを持つ。
- MemoV2 と ChecklistV2 は Itinerary と1対1。
- ConciergeChatLog と ConciergeToolCallLog はAI実行とTool呼び出しを記録する。
- TravelDate、Schedule、Memo、ItemなどV1モデルも残る。V2戦略のためにV1を削除・移行しない。
- WantToGo.planned_day と ScheduleV2.day_index は別の正本であり、前者を変えても予定は自動生成されない。旅程表地図はSchedule側の日を優先するテストがあるため、候補採用時の責務を新たに定義する。

### 5.3 セキュリティ上の現状

- UUID tokenとpkの組合せで対象しおりを取得し、閲覧・編集パスワードのセッションを分離している。
- パスワードハッシュの指紋をセッションキーに含めるため、パスワード変更後は旧セッションが失効する。
- JSON本文サイズ、各機能の件数・文字数、しおりスコープ、CSRFを検証する経路がある。
- 公開URLを再発行・失効する機能、参加専用権限、個人単位の監査、投票者識別はない。
- 編集パスワード未設定時はURLを知る人が編集できる。新戦略でLINE外へ転送される前提では危険度が上がる。
- V2 baseのOG URLはUUIDを含む完全URLであり、共有先Platform、crawler、同じpage上のscriptへ能力URLが渡り得る。既存仕様を即時破壊せず監査し、新しい参加tokenは失効可能・用途限定にする。
- V2の秘密UUID付き画面でもGoogle AdSense/AMP広告や複数の第三者CDN scriptを読み込む。第三者JavaScriptはURLとDOMに触れ得るため、新しいjoin/manage/claim画面では広告・第三者analyticsを読み込まず、CSPとReferrer-Policyを設計する。
- 「最近のしおり」は秘密URL全体を `localStorage` に保存し、AI conciergeの履歴にもlocalStorageを使う。共有端末とXSSの影響を含めて見直し、**manage tokenはlocalStorageへ保存しない**。
- qrcode libraryがimportできない場合の外部QR service fallbackは、share URLを第三者へ送信し得る。本番依存が入る通常経路とfallbackを区別して監査する。

### 5.4 ドキュメントとの不一致

- docs/task/task-002-free-map-display-provider.md と task-003 は実装待ちの記述を含むが、現コードにはMapLibre/OpenFreeMap表示と日別地図がある。タスク文書がコードより古い。
- docs/task/task-001-agentic-ai-concierge.md は現行を固定3段階中心として記す箇所があるが、feature flag既定OFFながらAgent基盤は実装済み。
- docs/task/task-004〜006にも実装待ち表記が残る一方、PUBLIC_BASE_URL/noindex/sitemap、検索意図guide、Flatpickr削除等の対応コードが存在する。外部運用や実測が未確認であることと、コード未実装を分ける必要がある。
- docs/task/task-007-search-console-ga4-monitoring.md は計測が未完であることとUUID付きURLの漏えいリスクを指摘する。現コードでも全ファネル計測は確認できない。
- docs/task/task-009-post-review-deployment-validation.md はコード側完了と実環境検証待ちを分けている。本番設定を「実装済み」と読み替えない。
- create.html はTurnstile widgetを表示する一方、CreateView内の検証呼び出しはコメントアウトされている。防御が有効とは断定できない。
- design.md はV2アプリ本体を今後のラウンドとして扱う箇所があるが、現コードにはV2の実機能が存在する。戦略実装前にドキュメント基準を再同期する。
- README.md の「他ユーザーの公開しおりも閲覧できる総合プラットフォーム」という将来像は、意思決定特化を優先する本提案と競合する。削除はせず、戦略承認後に優先順位を明記する。
- 現プライバシーポリシーは「個人を特定しない範囲の情報」「個人情報の収集は原則行わない」と説明するが、実際には再設定メール、しおり入力、AI送信・ログがあり、LINE userId、groupId、表示名等を扱う将来像とは整合しない。実装前の改定と法務確認が必要。

## 6. 現在のユーザーフロー

| 段階 | 現在できること | 操作・離脱リスク | 新戦略との一致 / 矛盾 | 改善候補 |
|---|---|---|---|---|
| 1. 知る | ホーム、デモ、説明、SEOページ | 主要価値が一般的なしおり・AIに見え、共同意思決定の痛みが伝わりにくい。ホームの行動計測も不十分 | 登録不要は一致。LINE起点の価値は未提示 | Phase 0のヒアリング後にメッセージテスト。LINE招待は技術・規約確認後に訴求 |
| 2. 作成 | Webでタイトル、開始日、終了日、任意パスワードを入力し即作成 | 相談初期は日付未定が多く、必須日付で離脱しうる。Botでは同じフォームを再現できない | 低登録負担は一致。会話起点・旅行名だけの仮作成とは矛盾 | 日付未定ドラフト、最少入力、Bot/Web共通の作成サービス |
| 3. 候補追加 | Places検索、手入力、カード、地図、Day未定、優先度、CRUD | 編集パスワード設定時は共有・入力の摩擦があり、未設定時はURL所持者へ編集権限を広く渡す。LINEの既存URLを再入力し、誰の提案か不明 | 候補の構造化は強く一致 | 参加URL、提案者、URL受付、重複確認 |
| 4. 共有 | URLコピー、Web Share、QR、ブログ埋め込み | 同一URLが転送されうる。閲覧/参加/編集の意図が伝わりにくい。失効・再発行なし | URL共有は中核資産 | 役割別トークン、短い説明付きLINE返信、失効・再発行 |
| 5. 同行者が閲覧 | 登録なしでモバイル表示、日別予定・地図を閲覧 | 閲覧パスワードがある場合は入力負担。誰が開いたか、参加したか不明 | インストール不要と一致 | ワンタップ参加、参加者名だけ設定、閲覧と参加を明示 |
| 6. 編集・参加 | 編集パスワードまたはパスワードなしURLで共通編集 | 個人帰属がなく、なりすまし・上書き・重複投票を防げない。編集権限が強すぎる | 共同作業の土台はあるが、参加という概念がない | ゲストParticipant、限定アクション権限、監査 |
| 7. 比較 | priority順、日別フィルタ、地図上の位置を比較 | priorityは全体で1値。希望の分布、対立、決定状態、未回答者が見えない | 新戦略の最大ギャップ | 4段階個人投票、集計、候補状態、未決定一覧 |
| 8. 日程へ割当 | WantToGoのDay指定、ScheduleV2との関連、AI変更提案 | 複数案を保持・比較できず、AI案は既存旅程への変更集合。営業時間・移動・制約の外部検証なし | 人が確定する設計は一致 | PlanVariantを確定Scheduleと分離し、採用時だけ反映 |
| 9. 旅行中 | 日別タブ、当日選択、次予定強調、日別地図、Google Maps経路リンク、持ち物 | V2オフラインなし。リアルタイム変更・通知は限定的 | Webを実行面として使える | まず安定性とLINE内ブラウザ実機確認。オフラインは利用データで判断 |
| 10. 旅行後 | ブラウザlocalStorageの最近のしおり、ブログ埋め込み | 参加者単位の履歴、再利用、写真、費用、アーカイブなし | 初期意思決定戦略の外側 | Phase 5まで保留し、再旅行率を見てテンプレート/再利用を判断 |

最も大きな離脱候補は、日程未定時の作成、同行者が編集権限を得る場面、個人の希望を表現できない比較段階である。Botだけを追加しても、この3点のうち最初の入口しか改善しない。

## 7. 現在の強み

1. **登録・インストール不要の共有Web**
   初期ターゲットが嫌う全員登録を既に回避できる。

2. **候補から実行旅程までの連続性**
   WantToGo、ScheduleV2、日別地図、持ち物、メモが同じItinerary配下にある。

3. **候補の地理的理解ができるUI**
   Places検索、構造化座標、カードとピン、Dayフィルタ、予定日未定が実装済みで、単なる表計算より旅行向けである。
   ただし検索dataと表示mapのprovider組合せは、Google固有規約の監査を通過することが再利用条件である。

4. **AI変更の確認分離**
   Agentの提案は即時DB変更せず、適用時に編集権限を再確認する。AI幹事の人間最終決定原則に適合する。

5. **既存の安全側実装**
   しおりスコープ、入力上限、パスワードセッション失効、非DEBUG時のエラー隠蔽、日次AI利用枠などを流用できる。

6. **薄いBotと相性のよいサーバーレンダリング**
   Botが複雑なUIを持たずWebへ誘導する構成なら、Django Templatesを置き換える必要がない。

## 8. 現在の課題

### 8.1 プロダクト

- 「誰が」「どの程度」望むかを保存できない。
- 候補の検討中、確認待ち、決定、見送りと、その変更履歴がない。
- 参加者、幹事、ゲスト、閲覧者の概念と権限がない。
- 複数案を並べて合意を取る場所がない。
- 作成時に日付が必要で、旅行相談の早い段階へ入れない。
- 共同利用の実態を測るイベントがない。

### 8.2 UX

- 共有URLを開いた人が、閲覧・投票・編集のどれをすべきか分かれない。
- 編集パスワードの共有は、2〜6人の軽い参加に対して重い。
- priorityが「全員の総意」に見えうるが、実際は最後に編集した一値である。
- LINE内ブラウザ、戻る動線、Cookie、Web Share、地図の実機互換性は未確認。

### 8.3 技術・運用

- LINE Webhook、非同期ワーカー、outbox、idempotency receiptがない。
- Python 3.8基準はライブラリ選定と保守期間のリスクになる。
- 本番のNginx/Cloudflare/監視/バックアップはリポジトリだけでは保証できない。
- GA4だけでなく、現行V2のAdSense/AMP広告・第三者CDN scriptも、秘密URL・DOMの外部露出面になる。新しい権限token画面へそのまま載せない。
- 秘密URL全体を「最近のしおり」としてlocalStorageへ置く現仕様は、共有端末・XSS・端末紛失時の影響が大きい。
- 現行規約・プライバシー文言が、LINE識別子・グループ投稿・外部AI送信を伴う将来像に対応していない。

### 8.4 戦略

- 旅行計画の機能総数、予約、経路最適化、オフライン、費用で成熟競合と正面衝突すると不利である。
- 「LINE対応」だけでは模倣可能であり、意思決定データと参加率の改善がなければ持続的な差にならない。
- 中核のグループ永続紐付けにはLINEポリシー解釈という未解決の外部依存がある。

## 9. 競合比較

### 9.1 読み方

下表は2026-08-14に公式サイト、運営者/開発者の製品ページ、公式ヘルプ、公式ストア掲載で確認できた範囲である。記載内容は各運営者の説明であり、特記しない限り実機・hands-on、現行稼働、利用者規模、品質を検証したものではない。「未確認」は機能が存在しないという意味ではなく、公開文面で裏付けられない事項を推測で補っていない。

LINE上の類似品探索は、公開Webの日本語・英語を対象に、一般検索、公式/開発者製品ページ、App Store/Google Play、LINE公式アカウント公開ページを確認した。主なqueryは「LINE グループ 旅行 Bot 旅程 候補 投票」「LINE Google Maps URL 保存 Bot」「group trip planner LINE bot voting itinerary」「travel organizer chatbot LINE」である。非公開・招待制・検索index外のBot、終了済みページ、地域限定appを網羅しないため、「同等品を確認できない」は**この範囲でend-to-end構成を裏付けられなかった**という非網羅的な調査結果に限る。

### 9.2 参加と共同意思決定

| サービス / 代替手段 | 主な入口・対象 | 登録 / インストール | URL・ゲスト | 共同編集 | 個人別希望投票 | 候補状態・合意形成 | LINEグループBot |
|---|---|---|---|---|---|---|---|
| **TabiSync現行** | 国内向け共有しおりWeb | 登録・インストール不要 | UUID URL、任意パスワード | 共通の編集権限で可能 | **未実装**。候補に単一priorityのみ | **未実装** | **未実装** |
| **tabiori** | 家族・友人・カップル等の旅行 | メール/Apple/Google登録、アプリとPC Web。無登録参加は**未確認** | URL/QR招待 | 参加メンバーによる共同編集 | **未確認** | **未確認** | **未確認** |
| **Wanderlog** | 高機能な旅行計画・実行 | Web/アプリ。共同編集者は招待 | 閲覧/編集権限を分けた招待を確認 | リアルタイム共同編集 | **未確認** | **未確認** | **未確認** |
| **NAVITIME Travel** | 国内移動を含む計画 | iOS/Android中心、Web同期 | 共有を確認。無登録ゲスト編集は**未確認** | プレミアムの共同編集を公式ストア掲載で確認 | **未確認** | **未確認** | **未確認** |
| **AVA Travel** | 主に海外旅行、好みからAI提案 | iPhoneアプリ。登録条件は**未確認** | 共有を確認。URL/ゲスト条件は**未確認** | リアルタイム共有・編集を公式掲載で確認 | 各自のLIKE候補は確認。票数等は**未確認** | LIKEによる絞込は確認、状態体系は**未確認** | 公式OAでAI旅行相談を確認。1対1限定か、旅行グループへ招待できるかは**未確認** |
| **Funliday** | AI作成から旅行実行 | Web/iOS/Android。編集者は第三者ログイン | リンク閲覧は無登録、編集はログイン | リアルタイム共同編集、閲覧/編集権限 | **未確認** | **未確認** | 共有URLをLINEへ送れるがBotではない |
| **Google Maps共有リスト** | 行きたい場所の地図共有 | Google Maps。編集はGoogleアカウント前提 | リンク共有、共同リスト | リストの共同編集 | 各場所への絵文字投票を公式情報で確認 | 候補→確定→旅程の状態は**未確認** | なし。LINEにはリンクを送る運用 |
| **LINE + Google Sheets** | 自作の共同表 | LINEは既存、Sheets編集者は共有設定に依存 | URL共有 | 表の共同編集・コメント | 列を作れば手動で可能 | 列を作れば手動で可能 | 自動Botではなく運用の組合せ |
| **TravelCanvas** | 家族・友人・社員旅行 | 作成・閲覧・編集とも登録/インストール不要。保存紐付けのみGoogle login | 固有URL | リアルタイム共同編集 | 候補への「いいね」 | 状態体系は**未確認** | URLをLINEへ共有、Botではない |
| **タビノワ** | グループ旅行の共同計画 | PWA。LINE/Googleログインを案内 | URL/QR招待、インストール不要を訴求 | リアルタイム共同編集 | 候補ごとの❤️ / 🤔 / 🙅投票を確認 | コメント・リアクションを確認。厳密な状態機械は**未確認** | **未確認** |
| **Limbo** | 英語圏のグループ旅行・決定停滞 | 作成者はiPhone app/account、投票者はWebリンクから無登録 | リンク/6文字code、無登録投票 | 編集者/投票者の権限分離 | 期限付き非公開投票→結果公開 | open ballot、deadline、reveal、approved result、Decisions inbox | **未確認** |
| **旅のしおり** | シンプルな無料グループ旅行 | 作成・共有・編集とも登録/インストール不要 | 固有URL | 共同利用 | **未確認** | **未確認** | URL共有のみ |
| **MapMemo** | LINEグループの場所URL保存 | Bot招待。別app/登録条件は**未確認** | Group投稿→list/mapへの導線。guest条件は**未確認** | Google Maps URLを自動でlist/tag/search/map化。共同権限は**未確認** | **未確認** | **未確認** | **開発者製品ページで機能を訴求**。現行稼働・規模は**未確認** |
| **Lightsplit** | LINEグループの割勘 | 全員の別app導入不要。詳細はMini App | Group card→Mini App | @Lightsplitだけ処理、通常会話を無視。共同編集範囲は割勘向け | 旅行投票は対象外 | カード→Mini Appで詳細編集 | **運営者製品記事で機能を訴求**。現行稼働・規模は**未確認** |
| **tabitte** | アプリ不要の共同しおり | 招待参加者はapp/login不要と公式説明 | URLから閲覧・編集 | 共同編集、section別権限 | 候補spotへのmember投票を確認 | 決定候補をScheduleへ1tap copy。正式な状態機械は**未確認** | **未確認** |
| **TabinoTe** | URLで共有するしおり | Web | 編集用URLを確認 | 編集用URLによる共同作業 | **未確認** | **未確認** | **未確認** |
| **公開検索で確認した旅行Bot** | LINE上の旅行支援 | 個別Botごと | 個別Botごと | 普通の友人グループでメンションし、共有旅程と参加者別合意を結ぶ現行サービスは確認できず | **未確認** | **未確認** | 同等品を確認できなかったが、「存在しない」ことの証明ではない |

### 9.3 旅行計画・実行機能

| サービス | 地図 / 日程 | AI旅行提案 | AI合意形成 | ルート最適化 | 外部URL取込 | 予約情報 | 費用 | オフライン |
|---|---|---|---|---|---|---|---|---|
| **TabiSync現行** | MapLibre地図、Places検索、日別Schedule | 保存データに対するAI回答・変更提案 | **未実装** | Google Maps経路リンクのみ | **未実装** | **未実装** | **未実装** | V2は**未実装** |
| **tabiori** | 予定、場所、地図 | **未確認** | **未確認** | **未確認** | **未確認** | **未確認** | スケジュール旅費の自動合計と各国通貨対応をFAQで確認 | 公式ストア掲載で対応を確認 |
| **Wanderlog** | 地図、旅程、移動 | AI旅程作成 | 参加者の対立説明は**未確認** | Proで確認 | 予約メール取込等を確認 | 予約整理 | 予算・費用 | Proで確認 |
| **NAVITIME Travel** | 交通を含む時間・費用付き行程 | 2024年のAI提供開始を確認。2026年の画面/制限は再確認できず | **未確認** | 独自経路検索、行きたい場所からの1日route生成を確認 | **未確認** | 予約導線 | 移動費表示 | **未確認** |
| **AVA Travel** | LIKE地点の地図・AI旅程 | 好み、日数、LIKEからAI提案 | LIKEの反映は確認、対立/重み付けは**未確認** | 移動時間を踏まえた自動最適化を公式掲載で確認 | 任意外部URL解析は**未確認** | 航空券・hotel比較/予約導線 | 割勘を確認 | **未確認** |
| **Funliday** | 地図、旅程、移動時間 | 短時間のAI旅程作成 | **未確認** | 経路支援 | Google Maps等からの取込を現行ガイドで確認 | 予約書類取込 | 費用管理を確認 | 公式ストア掲載で確認 |
| **Google Maps共有リスト** | 地図・場所list。日別しおりは**未確認** | Ask Mapsによる場所・行動案の会話探索を公式発表で確認。ただし2026-03発表時は米国/IndiaのAndroid/iOSからrolloutで、日本・全platformの現行提供は**未確認** | 絵文字Voteによる人の判断。AI合意形成は**未確認** | navigation/経路候補は強い。候補群の旅程順最適化は**未確認** | Maps内保存 | 一部partner予約 | group予算/割勘は**未確認** | 地図/navigationは一部対応。共同Voteのofflineは**未確認** |
| **LINE + Google Sheets** | 手作業で自由に作成 | なし | なし | なし | コピー&ペースト | 手入力 | 数式で可能 | Sheets側機能に依存 |
| **TravelCanvas** | 日程。地図は**未確認** | **未確認** | いいねを見て人が判断 | **未確認** | **未確認** | **未確認** | 割勘・精算 | PDF保存/印刷。Webオフラインは**未確認** |
| **タビノワ** | 日程。地図は**未確認** | **未確認** | 自動合意形成は**未確認** | **未確認** | **未確認** | **未確認** | 予算・割勘を確認 | PWA。オフライン範囲は**未確認** |
| **Limbo** | 日別map、route、timeline | 旅行生成AIは**未確認** | 期限、非公開投票、未投票reminder | 日別route表示、自動並替は**未確認** | 予約mail/PDF取込 | 予約確認、flight追跡 | 予算、割合、精算 | 作成・編集・投票・checkと再同期 |
| **旅のしおり** | Google Maps、日程、登録順route | **未確認** | **未確認** | route表示、自動並替は**未確認** | **未確認** | hotel/flight情報・書類 | 予算・費用 | **未確認** |
| **MapMemo** | URLから場所list/map | なしを前提にできないが公開情報では**未確認** | **未確認** | **未確認** | Google Maps URL | **未確認** | **未確認** | **未確認** |
| **Lightsplit** | 旅行地図/日程は対象外 | 旅行AIは対象外 | 旅行合意形成は対象外 | なし | なし | なし | 割勘が中核 | **未確認** |
| **tabitte** | 候補map、日程、決定候補のSchedule copy、晴雨/別行動の分岐plan | **未確認** | member投票と人の決定flow。AI集約は**未確認** | **未確認** | **未確認** | **未確認** | **未確認** | **未確認** |

### 9.4 競合から得られる判断

**正面から競うべきでない領域**

- WanderlogやFunlidayの機能網羅、予約取込、費用、オフライン、長期旅行管理
- NAVITIME Travelの交通データ、時刻・料金、経路最適化
- Google Mapsの地図・場所データそのもの
- tabioriの成熟したしおり装飾、写真、旅行中の総合体験
- 汎用表計算の自由度

**差別化できる可能性がある領域**

- 全員に新しいアプリ登録を求めず、既存のLINEグループから始める入口
- 候補収集ではなく「誰が何を望み、何が未決定か」まで構造化する意思決定レイヤー
- 複数案の希望充足・移動負担・不採用理由を説明し、人が採用するAI幹事
- LINEでは短い指示と進捗、Webでは比較・地図・編集という明確な役割分担

ただし空白市場ではない。TravelCanvasは登録不要・URL・共同編集・いいねを、タビノワは日本語で共同編集・3段階絵文字投票・コメントを、Limboは提案→期限付き非公開投票→結果公開を既に訴求する。tabitteも、**招待参加者はlogin不要**のURL共同編集、候補投票、決定候補のSchedule copy、分岐planを公式に説明する。したがって「投票→決定→旅程」だけでも独自性にならない。さらにMapMemoはLINEグループ内のGoogle Maps URL自動収集を開発者製品ページで、Lightsplitは明示メンションだけを処理してカードからMini Appへ渡す役割分担を運営者記事で訴求する。後二者の現行稼働と利用規模は未確認である。

2025年にLINE上の24時間旅行相談として開始した「るるぶ＋AIチャット」は、公式お知らせ一覧で2026-06-29の終了告知を確認したため、現行競合には数えない。会話型AIの開始だけでなく、共同編集可能な構造化データへ価値を残すことの重要性を示す隣接事例として扱う。

したがってTabiSyncは「登録不要」「投票」「LINE Bot」「AI旅程」のいずれか一語で差別化できない。**明示的なLINE入力→構造化候補→参加者別希望と条件→未決定の整理→説明可能な複数AI案→人の確認後に既存旅程へ反映**という一連の完了率で差別化を検証する。

### 9.5 サービス別の主な強みと示唆

| サービス / 代替 | 公式・運営者情報から確認できる主な強み | TabiSyncへの示唆 |
|---|---|---|
| tabiori | 旅程、写真、位置共有、チャット、持ち物、offlineを旅行前後へ広く提供 | 写真・装飾・旅行中の総合体験ではなく、決まる前の整理へ集中 |
| Wanderlog | 地図、予約取込、AI、経路最適化、予算、offlineの統合 | 海外旅行の機能数で競わず、日本語LINE groupの意思決定へ絞る |
| NAVITIME Travel | 日本の交通・経路・料金・予約導線 | 交通engineを再実装せず、決定済み候補の受け渡し先と捉える |
| AVA Travel | 好み/LIKEからAI旅程、地図、共有、route最適化 | AI推薦だけでは弱い。誰の希望・反対をどう扱ったかで差を作る |
| Funliday | AI旅程、共同編集、Maps取込、予約・費用・offline | POI量や総合機能ではなく、LINE入力から合意までの摩擦を減らす |
| Google Maps共有リスト | POI、地図、navigation、共同list、絵文字reaction | 地図を再発明せず、希望・状態・日程への上位decision layerを作る |
| LINE + Google Sheets | 柔軟な表、同時編集、comment、自由な運用 | 自由度で競わず、転記・集計・状態更新を旅行domainで自動化する |
| TravelCanvas | 登録不要Web、固有URL、共同編集、いいね、割勘 | 「登録不要URL共有＋投票」は差別化に使えない |
| タビノワ | 日本語PWA、3段階投票、comment、共同編集、費用 | 日本市場の直接競合。条件・未回答・履歴・説明可能な案まで必要 |
| Limbo | 期限付き秘密投票、結果公開、無登録投票、権限分離、offline | 合意形成自体も空白でない。LINE入口と日本向け制約で検証する |
| 旅のしおり | 無登録作成・編集、URL、地図、日程、予算 | 現行TabiSyncの低摩擦なしおりだけでは防御力が弱い |
| MapMemo | LINE groupのMaps URLをlist/tag/search/mapへ構造化 | URL保存の先に、意見・状態・Schedule採用をつなぐ |
| Lightsplit | 明示mentionだけを処理し、cardからMini Appへ詳細を渡す | privacy境界とBot/Web役割分担の参考にする |
| tabitte | 招待参加者はlogin不要の共同編集、候補投票、Schedule copy、分岐plan、section権限 | 投票→決定→旅程を越え、4段階の個人希望・厳密な履歴・AI説明で差を検証 |
| TabinoTe | 編集URL、旅程、checklist、予約memo、割勘 | 編集URLだけでは権限・本人性が弱い。用途別grantを設計する |
| るるぶ＋AIチャット（終了） | LINE上の旅行AI相談という低摩擦な入口 | 会話だけで終わらず、旅行ごとの共同資産を残す |

### 9.6 競合参照情報

すべて確認日は2026-08-14。

| 対象 | 確認できた主な事実 | 参照URL |
|---|---|---|
| tabiori | URL/QR招待、共同編集、予定・場所・位置共有・チャット・チェックリスト等 | [公式FAQ](https://tabiori.com/faq/)、[参加案内](https://tabiori.com/join/static/)、[使い方](https://tabiori.com/howto/)、[Google Play](https://play.google.com/store/apps/details?id=com.eyeputti.travellerbook&hl=ja) |
| Wanderlog | 共同編集と権限、AI、Proの経路最適化・オフライン、予約・費用等 | [共同編集ヘルプ](https://help.wanderlog.com/hc/en-us/articles/4625495771163-Add-friends-to-plan-together)、[AI](https://app.wanderlog.com/trip-planner-ai)、[経路最適化](https://help.wanderlog.com/hc/en-us/articles/13545624787867-Optimize-route)、[オフライン](https://help.wanderlog.com/hc/en-us/articles/13545182856859-Download-trip-plan-for-offline-access) |
| NAVITIME Travel | 行程、移動時間・料金、共同編集等のストア説明 | [App Store公式掲載](https://apps.apple.com/jp/app/%E6%97%85%E3%81%AE%E3%81%97%E3%81%8A%E3%82%8A%E4%BD%9C%E6%88%90-%E6%97%85%E8%A1%8C%E8%A8%88%E7%94%BB-navitime-travel/id1279724919) |
| AVA Travel | 好みを用いたAI旅行提案 | [公式サービス](https://travel.ava-intel.com/)、[法人向けAI旅行プランシステム](https://www.ava-intel.com/ai-travel-planner-systemes/) |
| Funliday | AI旅程、共同編集、Web/アプリ、取込、費用、オフライン | [公式FAQ](https://www.funliday.com/en/faq)、[公式機能ガイド](https://www.funliday.com/posts/funliday-app-function-guide/)、[Google Play](https://play.google.com/store/apps/details?id=com.funliday.app&hl=en_US) |
| Google Maps | リストの作成、共有、共同編集、region/platform限定rolloutのAsk Maps | [Google Mapsヘルプ](https://support.google.com/maps/answer/7280933)、[Ask Maps発表](https://blog.google/products-and-platforms/products/maps/ask-maps-immersive-navigation/) |
| Google Sheets | リンク共有、閲覧/コメント/編集権限、共同作業 | [Google Docs Editorsヘルプ](https://support.google.com/docs/answer/9331169?hl=ja)、[共同作業者数](https://support.google.com/a/users/answer/13309904?hl=ja) |
| TravelCanvas | 無登録Web、固有URL、共同編集、いいね、割勘 | [公式サイト](https://travelcanvas.app/ja) |
| タビノワ | URL/QR、PWA、共同編集、絵文字投票、コメント、費用 | [公式サイト](https://travelers-circle.com/) |
| Limbo | 無登録Web投票、期限付き非公開投票、結果公開、権限分離、予約・予算・offline | [App Store公式掲載](https://apps.apple.com/us/app/limbo-group-trip-planner/id6450775556) |
| 旅のしおり | 無登録作成・編集、固有URL、日程、地図、予算 | [公式サイト](https://tabinoshiori.jp/) |
| MapMemo | LINEグループ内Google Maps URLの自動保存、list/tag/search/map | [開発者製品ページ](https://www.kinjo.me/products/6vmlzh5uc) |
| Lightsplit | LINEグループ招待、明示mentionのみ処理、カードからMini Appへ | [運営者製品記事](https://lightsplit.com/ja/blog/lightsplit-line-bot-%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%97-%E5%89%B2%E3%82%8A%E5%8B%98) |
| tabitte | 招待参加者はlogin不要のURL共同編集、候補投票、決定候補のSchedule copy、候補map、section権限、分岐plan | [公式サイト](https://tabitte.com/) |
| TabinoTe | 編集用URL、旅程、チェックリスト、予約メモ、割勘 | [公式サイト](https://tabinote-app.com/)、[公式FAQ](https://tabinote-app.com/faq) |
| るるぶ＋AIチャット | 2025年のLINE旅行相談開始、2026-06-29終了告知 | [開始発表](https://jtbpublishing.co.jp/topics/CL000730)、[公式お知らせ一覧](https://plus.rurubu.jp/news) |

## 10. 新しいポジショニング

### 10.1 推奨ポジション

カテゴリを「AI旅行プランナー」ではなく、**友人旅行の意思決定を進めるAI幹事**と定義する。

推奨する一文は次のとおり。

> LINEグループから始めて、みんなの「行きたい」と迷っていることを一つにまとめ、選べる旅程案まで進めるAI幹事。

短い認知訴求には次を使える。

> LINEに散らかった「行きたい」を、ひとつの旅程に。

後者だけでは「リンク保存ツール」に見えるため、LPでは「みんなの希望」「未決定」「選べる案」「登録不要」を続けて説明する。

### 10.2 戦略の境界

- TabiSyncは旅行先を無限に発見させるサービスではなく、グループが出した候補を決めるサービスである。
- AIは幹事の代わりに勝手に決定せず、整理、比較、質問、複数案、理由説明を行う。
- LINEは会話・起動・短い確認の入口、Webは正確な状態と詳細操作の正本とする。
- 旅程が確定した後は、既存のSchedule、日別地図、持ち物、メモを実行面として使う。
- LINEの一般会話全文はプロダクトの入力資産にしない。明示操作で得た構造化データを正本にする。

### 10.3 防御力

Botの接続自体は模倣しやすい。防御力は、次の組合せから作る。

1. 参加者別の希望と制約を、低い入力負担で集めるUX。
2. 候補の状態と未回答・未決定を明示する共同意思決定モデル。
3. 希望充足と制約の説明可能な複数案。
4. 採用案を日別地図・予定へ崩さず反映する既存資産。
5. 実際に2人目・3人目が参加したかを計測し、参加摩擦を継続改善するデータ。

## 11. 対象ユーザー

### 11.1 初期セグメント

- 2〜6人の友人グループ
- 大学生・若年社会人を中心とする
- 国内の日帰り〜2泊
- 旅行相談が既にLINEグループで始まっている
- Google Maps、施設、SNS等のURLを送り合う
- 幹事はいるが、整理・催促・調整が一人に偏る
- 全員に旅行専用アプリを入れたり会員登録させたりしにくい

### 11.2 利点

- グループ人数が小さく、投票分布と未回答を理解しやすい。
- 短期国内旅行は候補数・日程・制約が比較的限定され、MVPのモデルで扱いやすい。
- LINE内で問題が発生しているため、入口の価値を行動で検証しやすい。
- 高度な予約・為替・長期経路より、合意形成の痛みが前面に出やすい。

### 11.3 弱点

- 若年層は無料期待が強く、LINE/AI/Places費用を回収しにくい。
- 「旅行ごとにBotを招待する」心理的抵抗、通知ノイズ、グループメンバー全員への説明責任がある。
- 2人旅行では会話だけで決まり、投票機能が過剰になりうる。
- 旅行頻度が低く、年単位の継続率は上がりにくい。
- LINEを使わない層や、Discord/Instagram DM等で相談する層を初期から捨てる。

### 11.4 最初に分けて測るコホート

- 2人 / 3〜4人 / 5〜6人
- 日帰り / 1泊 / 2泊
- 日付確定済み / 未定
- 幹事が明確 / 不明
- 候補URLが既に3件以上 / まだない
- Bot経由 / Web直作成

最初から「大学生」に限定せず、問題の強さで採用する。年齢よりも「LINEグループに候補URLが3件以上散らかり、誰も決め切れていない」を主要な参加条件にする。

## 12. 解決する課題

### 12.1 Job to be Done

> 友人との旅行相談で候補が増えて決められなくなったとき、全員に別アプリの学習を求めず、各自の希望と制約を集め、未決定を減らし、納得できる旅程にしたい。

### 12.2 問題の分解

| 問題 | 現在の代替 | 代替の弱点 | TabiSyncが担う範囲 |
|---|---|---|---|
| 候補が会話に流れる | LINE検索、ピン留め、ノート | 場所として構造化されず、重複・見落とし | 明示共有された候補だけを場所候補へ |
| 希望が曖昧 | スタンプ、口頭、幹事の記憶 | 誰の希望か、強さ、未回答が不明 | 参加者別4段階希望と集計 |
| 決定状態が不明 | 幹事がメッセージで宣言 | 後から流れ、変更理由が残らない | 候補状態と履歴、未決定一覧 |
| 制約が後出し | 会話、個別DM | 計画のやり直し | 必要最小限の構造化条件 |
| 一人で日程化 | 地図と表を往復 | 幹事負担、説明不足 | 比較可能な複数案と理由 |
| 旅行中の確認 | LINE履歴、Maps、スクショ | 情報が分散 | 既存の旅程、日別地図、持ち物、メモ |

### 12.3 解かない問題

航空券・宿泊予約の最安比較、完全な公共交通ルーティング、旅行商品販売、写真共有、精算、全世界の長期旅行管理は初期のJobではない。

## 13. 価値提案

### 13.1 参加者

- 新しいアプリを入れず、リンクから名前だけで参加できる。
- 「絶対」「できれば」「どちらでも」「今回は見送り」を短時間で表せる。
- 自分の希望がどう反映されたか、採用されなかった理由も分かる。

### 13.2 幹事

- 候補の転記、誰が何を望むかの記憶、未回答者の確認を減らせる。
- 未決定事項と次に聞くべき質問が分かる。
- AIから複数案とトレードオフを受け取り、決定権は保持できる。

### 13.3 グループ

- LINEの会話を置き換えず、決定すべき情報だけを共有の正本へ移せる。
- 決定後の予定、地図、持ち物、メモまで同じしおりで使える。
- 「一番人気」だけでなく、強い反対、制約、移動負担を含めて比較できる。

### 13.4 価値を証明する行動

「Botへ話しかけた」「AI案を生成した」ではなく、2人目以降の参加、投票、状態更新、予定採用、未決定の減少を価値の証拠とする。

## 14. LINE Botを中心とした体験

### 14.1 推奨する通常フロー

1. 管理者がMessaging APIチャネルでグループ参加を許可する。
2. ユーザーが公式アカウントを旅行グループへ招待する。友だち追加が必要な実際のクライアント導線はPhase 0で検証する。
3. join webhookを受け、Botは「処理する投稿の範囲」「保存」「退出/削除」「Webへのリンク」を含む短い案内を一度だけ返信する。
4. ユーザーがBotを明示メンションして「しおりを作成」と送る。
5. Botは mentionees の isSelf 等で自Botへのメンションを判定し、旅行名だけを質問する。プロフィール同意がない利用者ではmention object自体が欠落し得るため、その場合はBotが発行した**postback action（quick-reply buttonに設定する場合もmessage actionではなくpostback）**へ誘導し、表示名文字列の一致だけで命令扱いしない。postbackはgroup commandの起動には使えても、tapping actorのManager本人性を証明するとは限らない。会話状態には短いTTLを設ける。
6. 応答者が旅行名を送る。Botの質問への応答であることを、reply/quote、送信者、状態、期限で限定する。
7. Djangoの共通ドメインサービスで「日付未定ドラフト」を作る。
8. Botはグループへ、**管理/edit権限を含まない、用途限定・失効可能なbearer join grant URL**と「候補追加」「希望投票」「予定確認」の短い説明を返信する。
9. 作成commandの送信者は、グループへ管理tokenを出さない別のclaim導線でManager権限を取得する。方式は第14.5節のPhase 0 gateで決める。
10. メンバーはWebでゲスト名を設定し、候補・投票・状態を操作する。
11. Botは明示メンションされた「しおりを確認」に現在の用途限定join linkと概要だけを返す。

### 14.2 処理対象

初期は次だけを処理する。

- 自Botが構造化mentionで明示されたテキスト。mention object欠落時は文字列名で代替せず、Botが発行したpostback actionへ誘導する
- Botが開始した短期状態内の回答
- Botが提示したpostback
- ユーザーが「候補として追加」と明示したURL
- 明示開始された候補収集モード中の投稿

受信できることと、保存・AI送信してよいことを分ける。通常の雑談、他人宛てメンション、無関係なURL、Bot参加前の会話は処理・保存・AI送信しない。

### 14.3 状態と例外

| 状況 | 推奨動作 |
|---|---|
| 進行中のしおりが既にある | 新規作成せず、現在のしおりを提示。将来は明示的な「終了/切替」 |
| 旅行名の応答がない | 数分〜数十分で状態を期限切れ。自動催促はMVPで行わない |
| 複数人が同時に作成 | 原子的な一意制約と状態versionで一件だけ成功、他方へ既存リンク |
| Botが退出/削除 | leave webhookで送信停止と一時状態破棄。旅程Webは残すがLINE連携状態を表示 |
| しおり削除/非公開 | Botはmanage/edit URLを返さず、再作成または管理者操作を案内 |
| join URLが別グループへ転送 | URL所持者は参加できるbearer capabilityであり、MVPではLINE group membershipを証明できない。join以外を許可せず、期限・失効・再発行・転送注意を用意 |
| Manager未取得/端末喪失 | groupへmanage URLを投稿しない。第14.5節のprivate claim/recoveryを必須化し、未解決なら公開しない |
| 同一ユーザーが複数グループ | ParticipantはItinerary単位。LINE userIdをグローバル人格として無条件統合しない |
| Bot参加前の候補 | ユーザーが候補として再投稿、転送、またはWebで追加 |
| 送信取消 | 対応する保存済み入力を削除/匿名化し、派生候補はポリシーに基づき取消または要確認へ |
| ポリシー上groupId永続保存不可 | 24時間未満の一時状態だけにし、ユーザーが都度しおりコード/リンクを指定。1グループ1進行中は提供しない |

### 14.4 「1グループにつき進行中1件」の評価

MVPの会話曖昧性と同時作成を抑える制約としては適切である。過去の旅行はアーカイブとして保持し、currentだけに一意制約を置く。将来は「一覧」「切替」「終了」を明示コマンドにする。

ただし、この制約はgroupIdの安定した永続紐付けに依存する。LINEポリシー上許可されるという確認が取れるまで、製品要件として確定しない。

### 14.5 Managerの取得と復旧

Botがgroupへmanage URLを返すと全memberと転送先へ高権限を漏らす。一方、通常のguest Web sessionはgroup commandの `source.userId` と結び付かず、LINE Loginも参加者MVPでは保留している。このため「作成commandを送った人が自動でManagerになる」とは現仕様から言えない。

Phase 0では次を順に検証し、**Bot作成を維持できる方式を公開MVP前に一つ選び、脅威model・復旧手順まで固定する**。

1. 推奨候補: 作成者が公式アカウントを友だち追加し、1対1 chatで短期challengeを送る。groupのmessage eventと1対1で同じprovider上のuserIdを照合できる場合だけ、短寿命・一回限りのmanage claim URLを**その1対1 eventへのreply**で返す。groupで得たuserIdだけへprivate pushできるとは仮定せず、友だち/7日条件、userId欠落、delivery、規約を実機確認する。
2. Bot作成を維持する代替候補: group command senderのuserIdが得られる場合に、Manager限定LINE Login等で同一providerの本人性を照合してclaimする。全参加者へLoginを広げず、postbackだけを本人確認に使わない。
3. Web-first pivot: email/password等でManager identityをWeb上で先に確立し、そのしおりのjoin grantをgroupへ共有する。これは `@TabiSync しおりを作成` のfallbackではなく**Bot作成をMVPから外す別案**であり、採用時はH1とMVPを再承認する。誰でも先着claimできる方式にはしない。
4. 1または2が成立しない場合: Managerを必要とするBot作成をNo-Goにし、既存Webで管理権限を確立したしおりだけをgroupへ接続する。

Manager tokenはgroup message、OGP、analytics、広告、Referer、application log、localStorageへ出さない。端末喪失時の再claim、全token revoke、Manager不在、複数Manager、作成者userId欠落をE2E対象にする。参加者全員へのLINE Login強制はしないが、Managerだけの最小本人連携が必要と判明した場合は「LINE LoginはMVP外」という判断をその範囲に限って見直す。

## 15. BotとWebの役割分担

この分担は適切である。LINEで複雑な表・地図・権限を再現すると、メッセージ通数、状態同期、アクセシビリティ、誤操作が増える。

| 操作 | LINE Bot | TabiSync Web | 正本 |
|---|---|---|---|
| 参加案内・プライバシー告知 | 短い概要とリンク | 完全な説明・設定 | Web文書 |
| しおり仮作成 | 旅行名だけを対話取得 | 日付・説明・権限の詳細 | Django DB |
| 現在リンク・進捗 | 概要を返信 | 詳細表示 | Django DB |
| 候補URL受付 | Phase 3で明示命令のみ | 検索・手入力・修正 | WantToGo系 |
| 候補一覧 | 件数と上位数件まで | カード、地図、フィルタ | Web |
| 希望投票 | postbackの小さな補助は将来 | 参加者別投票と集計 | Web |
| 候補状態 | 概要/通知 | 変更・履歴・未決定 | Web |
| 日程編集 | 原則Webへ誘導 | Schedule編集 | Web |
| AI幹事起動 | 明示命令、受付通知 | 条件確認、複数案比較 | 構造化データ |
| AI結果 | 要約とWebリンク | 根拠、差分、採用/却下 | PlanVariant |
| Manager取得・権限・token・削除 | 1対1 private claim候補と案内。groupへmanage tokenは出さない | claim、復旧、管理画面 | Web/identity service |

Botの返信は「次に押す一つ」と概要に留める。push通知は利用者が明示選択した重要イベントだけに限定し、replyで済むものをpushにしない。

## 16. 想定ユースケース

### UC-1: 日程未定の旅行を立ち上げる

- 幹事がBotを招待し、メンションして旅行名だけで仮作成する。
- Botは参加リンクを返し、日付はWebで後から設定できる。
- 作成者はgroupと別のprivate claimでManagerになり、groupには参加権限だけのjoin grantを残す。
- 成功条件: 作成者が5分以内にdraftを作り、24時間以内に2人目が参加して候補追加またはVoteを行う。7日指標は継続利用のNorth Starとして別に見る。

### UC-2: Webで各自が候補と希望を出す

- 参加者は表示名を設定し、既存候補へ4段階希望を付ける。
- 候補がなければPlaces検索で追加し、自分が提案者として記録される。
- 幹事は未回答者ではなく「未回答数」を確認できる。メンバー一覧取得に依存しない。

### UC-3: 候補を決める

- グループは投票分布、強い反対、時間・予算制約、地理的まとまりを見る。
- 権限を持つ人が状態を検討中→確認待ち→決定/見送りへ動かす。
- 状態変更は履歴に残し、最後の一人の編集で全員の投票を上書きしない。

### UC-4: LINEで候補URLを追加する（Phase 3）

- ユーザーが自Botをメンションし、追加意図とGoogle Maps URLを送る。
- サーバーは許可ドメインと安全なリダイレクトだけを処理し、Places API等でPlace IDを解決する。
- 確信度が足りなければ候補を確定せず、Webで候補を選ばせる。

### UC-5: AI幹事に案を頼む（Phase 4）

- ユーザーが明示起動し、Webで対象日、出発地、予算、移動、雨天等を確認する。
- AIは構造化データから2〜3案を作り、希望一致度、移動負担、不採用候補、未確認事実を示す。
- 人が一案を選び、差分を確認して初めてScheduleV2へ反映する。

### UC-6: Botが使えなくなっても旅行を続ける

- Bot退出、LINE障害、規約判断変更後もWebの旅程と参加リンクは利用できる。
- Bot連携はしおりの所有・復旧・削除の唯一経路にしない。

## 17. LINE Messaging APIの実現可能性

### 17.1 総合判定

**API機能としては、薄型Bot MVPの主要動作を実現できる。** グループ参加、join/message/leave/postback webhook、同意条件を満たす場合の構造化メンション判別、groupId/roomIdと条件付きの送信者userId、reply/push、グループへのURL返信が公式仕様にある。mention/userId欠落時の安全なfallbackとManager本人確認は別の公開gateである。

一方、**「LINEグループとしおりを長期間自動で結び付ける」製品設計は規約面で条件付き**である。LINE User Data Policyの24時間制限とgroupIdの扱いについて公式確認が取れるまでは、全体を「実現可能」と断定しない。

### 17.2 公式仕様の確認結果

確認日はすべて2026-08-14。

| 論点 | 公式に確認できた事実 | TabiSyncへの判断 | 参照 |
|---|---|---|---|
| グループ招待 | Developers Consoleで「Allow bot to join group chats」を有効にする。グループ/複数人トークにBotを招待でき、同時に参加できるLINE公式アカウントは1つ | 設定と、他Botがいる場合の招待失敗UXを検証 | [Group chats and multi-person chats](https://developers.line.biz/en/docs/messaging-api/group-chats) |
| 参加・退出 | join、leave webhookがグループで届く | joinで案内、leaveで送信停止と一時状態破棄 | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| グループ投稿 | message、edit、unsend、member join/leave、postback等のイベントがある。edit webhookはgroup chatのtext message向けで、1対1/複数人roomへ一般化できない | MVPは明示メンション等だけ処理。受信可能な全投稿を保存せず、roomIdを含む設計でeditを当然視しない | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| メンション | text messageの mention.mentionees にtype=user、BotのuserId、isSelf=trueが入る。ただしプロフィール情報利用への同意がない送信者では、userIdだけでなくmention objectも含まれない | 構造化objectがある時だけ判定。欠落時は表示名文字列へfallbackせず、Bot発行のpostback actionをPoCする | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)、[User consent](https://developers.line.biz/en/docs/messaging-api/user-consent/) |
| groupId / roomId | webhook sourceにグループはgroupId、複数人トークはroomId。送信者が識別できる場合はuserId | スコープ・送信先に使える。永続保存の規約解釈は別問題 | [Group chats](https://developers.line.biz/en/docs/messaging-api/group-chats)、[FAQ](https://developers.line.biz/en/faq/) |
| 送信者userId | group/room sourceのuserIdはmessage eventにのみ含まれ、プロフィール利用同意条件の影響も受ける | userId欠落を許容する。postback actionはintent fallbackになってもtapping actor/Manager本人性を与えるとは扱わない | [Webhook event objects](https://developers.line.biz/en/reference/messaging-api/#webhook-event-objects)、[User consent](https://developers.line.biz/en/docs/messaging-api/user-consent)、[Getting user IDs](https://developers.line.biz/en/docs/messaging-api/getting-user-ids/) |
| Reply | webhookのreplyTokenで応答。tokenは1回のみ、原則受信後1分以内。再送時も既使用またはevent発生から20分超では利用不可。境界は変更されうる。1リクエスト最大5 message objects | 重いAI処理を待たず受付返信。token再利用や境界依存をしない | [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/)、[Sending messages](https://developers.line.biz/en/docs/messaging-api/sending-messages/) |
| Push | group/room宛はOAがそのchatに参加中である必要がある。個人宛は、友だち追加済み、または1対1でmessageを送ってから7日以内等の条件がある。HTTP 200でもblock、削除、非friend等で届かない場合がある | opt-in通知だけ。Manager claimはgroup eventのuserIdへ無条件pushせず、利用者が開始した1対1へのreply候補を検証 | [Sending messages](https://developers.line.biz/en/docs/messaging-api/sending-messages/)、[Group chats](https://developers.line.biz/en/docs/messaging-api/group-chats) |
| メンバー一覧 | 全member user IDs取得はverifiedまたはpremium account向けとAPI referenceに記載。日本の公式アカウント種別は現在、未認証/認証済の2種 | MVPは全員一覧に依存せず、実際にWeb参加した人をParticipantとする。日本では認証済取得を前提に再確認 | [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/)、[公式アカウント種別](https://www.lycbiz.com/jp/service/line-official-account/account-type/) |
| アカウント種別 | 日本では2026-04-01にプレミアムアカウントを廃止し認証済へ統合。プレミアムIDは別概念 | API referenceの旧表現との整合を実アカウントで確認 | [仕様変更告知](https://www.lycbiz.com/jp/news/line-official-account/20260107/)、[認証済アカウント](https://www.lycbiz.com/jp/service/line-official-account/verified-account/) |
| 過去履歴 | Bot参加前の会話履歴を取得する公式APIは確認できない | 過去候補は再投稿/転送/Web入力 | [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/) |
| text再取得 | textはwebhookでのみ取得し、後から再取得するAPIはない。引用はquotedMessageIdだけで引用元内容を取得できない | 必要な明示入力を検証後すぐ構造化し、原文保持を最小化 | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| 送信取消 | unsend webhookが届き、将来閲覧・利用できないようDB等から消すことを公式が推奨 | messageIdとの対応を短期保持し、削除/匿名化手順を実装 | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| 署名 | raw request bodyとchannel secretからHMAC-SHA256を計算し、Base64値を x-line-signature と比較。bodyを変更/parseする前に行う | Webhookの最初の必須処理。LINEは送信元IPを公開しないためIP許可リストの代替にしない | [Verify webhook signature](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/) |
| 再送・重複 | redeliveryは既定無効で有効化可能。同一eventが複数届きうる。webhookEventIdで重複判定。順序が変わりうるためtimestampも見る。再送は保証ではない | DB一意制約、冪等なdomain command、順序/version検証、dead-letter相当の運用 | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| 非同期 | LINEはwebhookイベントの非同期処理を推奨 | 署名検証とreceipt保存後すぐ2xx。簡単なreplyは1分制限を考慮し、AIは受付返信後pushまたはWeb通知 | [Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/) |
| Webhook応答 | 公式のerror statisticsはBot serverが2秒以内に応答しない場合をrequest_timeoutとして分類 | 署名検証・receipt/queue境界までを2秒未満のSLOにする | [Webhook error statistics](https://developers.line.biz/en/docs/messaging-api/check-webhook-error-statistics/) |
| Push再試行 | push等は初回からUUIDのX-Line-Retry-Keyを指定でき、同一keyの受理済み再試行は409。replyは非対応 | outbound jobごとにkeyを固定し、timeout時の二重送信を防ぐ | [Retry failed API requests](https://developers.line.biz/en/docs/messaging-api/retrying-api-request/) |
| 料金 | 日本の例はCommunication 0円/200通、Light 5,000円/5,000通、Standard 15,000円/30,000通、追加最大3円/通。replyは通数対象外、push等は対象 | 料金は変更前提。グループpushは受信人数で数えるため乱用しない | [Messaging API pricing](https://developers.line.biz/en/docs/messaging-api/pricing/) |
| 料金改定予定 | 2026-10-01から日本の追加message料金を改定予定。2026-08-14時点では未施行 | rollout日が改定後なら再計算し、文書の現行例を固定契約値にしない | [料金改定告知](https://www.lycbiz.com/jp/news/line-official-account/20260216/) |
| 通数計算 | 5人グループへ4 message objectsを1 push requestで送っても5通として計算 | メッセージbubble数より送信対象人数が費用を決める | [Messaging API pricing](https://developers.line.biz/en/docs/messaging-api/pricing/) |
| Rate Limit | endpoint・channel単位。多くの一般endpointは2,000 requests/secだが個別値が優先 | LINE上限は濫用防止ではない。group/user/IP/費用の日次上限を自前実装 | [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/) |
| Response settings | 新規Messaging API channelに紐づくOAではGreeting messageやAuto-responseが既定ONになり得る。Bot serverを使う場合はOFFが公式に推奨される | Greeting、Auto-response、Chat modeをPhase 0 checklistで固定し、一般会話へOA側が自動返信して「明示mentionのみ」を破らないようにする | [Build a bot](https://developers.line.biz/en/docs/messaging-api/building-bot/) |
| LINE Login | Messaging APIと同一providerなら同一ユーザーに同じuserIdが発行される構成がある。連携解除要件がある | 必要になればWeb participantとの本人連携に使う。MVP必須ではない | [LINE Login overview](https://developers.line.biz/en/docs/line-login/overview)、[FAQ](https://developers.line.biz/en/faq/)、[Account linking](https://developers.line.biz/en/docs/messaging-api/linking-accounts/) |
| LIFF / Mini App | LINE内Web体験や送信連携を提供するが、通常Web URLをBotが返すために必須ではない | MVPは通常Web。再ログイン摩擦やLINE内コンテキスト連携が主要課題と判明したら評価 | [Using user data in LIFF](https://developers.line.biz/en/docs/liff/using-user-profile/)、[LIFF guidelines](https://developers.line.biz/en/docs/liff/development-guidelines/)、[Introducing LINE MINI App](https://developers.line.biz/en/docs/line-mini-app/discover/introduction/) |
| データ利用 | 目的通知・同意、最小取得、目的限定、必要期間だけ保持、削除・開示対応等が必要。友だち情報・グループ情報は24時間超保存禁止と記載 | 一般会話の蓄積や二次学習をしない。groupIdの長期利用は書面確認必須 | [LINE User Data Policy](https://terms2.line.me/LINE_Developers_user_data_policy?lang=ja)、[Terms and policies](https://developers.line.biz/en/terms-and-policies) |
| 外部AI委託 | User Data Policy 3.4は第三者開示を制限し、3.4.2はservice提供に必要な業務委託先への開示をflow-down義務付きで認める。OA API利用規約にも同意・目的限定等があるが、LINE利用者messageの外部AI委託を一律禁止する明文とは断定できない | processor/DPA/再委託/保持/通知同意をLINE・法務へ確認。確認前は保守的No-Go | [LINE User Data Policy](https://terms2.line.me/LINE_Developers_user_data_policy?lang=ja)、[LINE公式アカウントAPI利用規約](https://terms2.line.me/official_account_api_terms_jp?lang=ja) |
| 外部link | OA API利用規約は、運営者が実質管理しないpageへのBot message内linkを制限する文言を持つ | Botは原則TabiSync管理pageへlinkし、Maps/予約linkの再掲可否をLINEへ確認 | [LINE公式アカウントAPI利用規約](https://terms2.line.me/official_account_api_terms_jp?lang=ja) |

### 17.3 技術的な推測

以下は公式仕様ではなく設計上の推測である。

- join/message webhookとDjangoのdomain serviceを組み合わせれば、BotからItineraryを作成できる。
- 単純な作成はreply tokenの時間内に完了できる可能性が高いが、DB/外部API障害を含むSLOは実測が必要。
- groupIdを暗号化し検索用HMACを併用すれば漏えいリスクは下げられる。ただしLINEポリシー上の保存可否は改善しない。
- LINE Loginなしでも、Web側の署名付きguest cookieで投票仮説は検証できる。ただし強い本人保証はできない。
- long-running AIはreply tokenで完了通知できない場合があるため、受付reply後のopt-in pushかWeb pollingが必要になる。

### 17.4 追加検証が必要な点

1. groupId/roomIdを「現在のしおり」に24時間超紐付けることの許可範囲。
2. groupIdのHMACや暗号文も「グループ情報の保存」に当たるか。
3. 認証済アカウントでメンバーID一覧APIが現在の日本仕様どおり利用できるか。
4. 友だち追加前後で、実際にグループへ招待できるクライアント導線と失敗表示。
5. グループ名・画像を取得・保存しないMVPで審査・利用案内を満たせるか。
6. Bot送信文、AI利用、Web遷移、削除・退出について必要な同意文言。
7. LINE内ブラウザでCookie、CSRF、Web Share、MapLibre、Google Placesが動くか。
8. reply tokenの実測余裕、Webhookのピーク、redelivery、edit/unsendの順序。
9. 公式アカウントの審査、表示名、カテゴリ、ガイドライン適合性。
10. 料金プランと月間上限の公開直前再確認。
11. userId/mention object欠落時に、Bot発行のpostback actionで安全にcreate/checkへ入れるか。postbackはManager actor識別に使わず、表示名文字列もcommand判定に使わない。
12. Manager候補が1対1を開始した場合のreply、個人pushの友だち/7日条件、200でも非配信となるcaseを実機でどう扱うか。
13. OA ManagerのGreeting、Auto-response、Chat modeを意図どおり固定し、一般会話へ自動返信しないか。

## 18. LINE APIの制約

### 18.1 製品設計に効く制約

- **過去を読めない**: Bot導入前の候補を自動整理する約束はできない。再投稿・転送・Web追加をオンボーディングに含める。
- **textを後から取り直せない**: Webhook処理失敗時にLINEから原文を再取得できない。receiptと構造化処理の信頼性が重要。
- **replyは短命**: 1回・原則1分以内なので、AI完了まで待つ設計にしない。
- **pushは有料になりうる**: グループ人数分を数える。定期進捗を既定ONにしない。
- **全メンバー把握を前提にできない**: アカウント種別、同意、イベント参加時点の制約がある。「未回答のLINEメンバー」ではなく「TabiSync参加者の未回答」を表示する。
- **構造化mentionも欠落し得る**: profile同意がない利用者では `mention` objectがない。表示名文字列だけで命令扱いせず、Botが発行したpostback actionをfallbackとして検証する。ただしgroup/roomのpostbackからManager本人性が得られるとはみなさない。
- **イベントは重複・逆順・欠落しうる**: exactly-onceをLINEに期待しない。アプリ側を冪等にする。
- **Botの送信取消はできない**: manage/edit URLと個人情報はgroupへ出さない。必要なjoin URLは返信前にscopeを検証し、短寿命・失効可能にする。
- **1グループ1公式アカウント**: 他の便利Botとの競合が招待障壁になりうる。
- **受信と利用許可は別**: Webhookに届いた一般会話を「届いたから使える」と解釈しない。
- **OA Managerの自動応答は別経路**: Greeting/Auto-responseを無効化しないと、Webhook codeが無視しても一般会話へ返信し得る。設定をrelease checklistと監視対象にする。
- **識別子の保持に規約不確実性**: 中核体験の外部依存であり、実装上の工夫だけで解消しない。

### 18.2 Conversation state

Botの質問状態は、group/room、質問種別、開始者、開始時刻、期限、状態versionだけを持ち、原文を長期保存しない。質問への回答として扱う条件を明示する。

- 同じsourceである。
- 期限内である。
- 原則として開始者の返信、quote、または専用postbackである。
- 新しい明示メンションが来たら古い状態を安全に終了する。
- 競合する作成操作はDB制約で一つにする。

### 18.3 料金・濫用境界

- reply優先、pushは明示opt-inの決定・期限通知に限定する。
- groupごと・userごと・channel全体で、分/日/月の命令、AI、push予算を持つ。
- 月間quota APIを監視し、80/95/100%で段階的に通知・停止する。
- 1回のメンションで外部URLを大量展開・AIを複数回実行しない。
- グループ人数は費用に影響するため、初期対象を2〜6人に限定することは運用上も合理的である。

### 18.4 LINE Login / LIFF / Mini Appの判断

| 選択肢 | MVP判断 | 採用条件 |
|---|---|---|
| 通常Web + guest cookie | **採用** | 参加率・投票率を最小実装で検証 |
| LINE Login | **保留** | なりすまし、複数端末、復帰識別が主要阻害要因になった場合 |
| LIFF | **保留** | LINE内でのparticipant自動連携やchat contextが、追加審査・複雑性を上回る価値を示した場合 |
| LINE Mini App | **Won't now** | 大規模配布、審査済みのLINE内一貫体験が必要になった後 |

この表は一般Participantの既定判断である。M12のprivate Manager claimが1対1/Web-firstで成立しない場合は、Managerだけの最小LINE Loginを条件付きMustとして別ADRで判断する。全員へ強制する判断には広げない。

## 19. AI幹事の定義

### 19.1 一般的なAI旅程生成との違い

AI幹事は、観光地をゼロから並べる機能ではない。参加者が明示した候補・希望・制約・確定事項を整理し、**選択可能な複数案とトレードオフを提示する意思決定支援**である。最終確定は人が行う。

### 19.2 入力

入力の正本はTabiSync上の構造化データとする。

- Participantと役割
- 参加者別の4段階希望
- WantToGo候補、Place ID、座標、滞在時間
- 旅行日程、出発地、帰着条件
- 予算、移動手段、歩行許容、希望時間帯
- 食事・アレルギー等、本人が明示した必要最小限の制約
- 営業時間、休業、予約要否、雨天適否と、その出典・確認時刻
- 確定Schedule、候補状態、確認待ち事項

LINE一般会話全文、Bot参加前の履歴、無関係な投稿、プロフィール画像は入力にしない。自由記述はプロンプトインジェクションを含む不信データとして区切る。

### 19.3 出力

- 希望一致度重視
- 定番重視
- グルメ重視
- 移動負担を抑えた案
- 低予算案
- 雨天案
- 各案の採用候補、順序、概算滞在/移動、前提
- 各案を提示した理由と、誰のどの希望を満たすか
- 採用できなかった候補と理由
- 意見が分かれる候補
- 不足情報と次に聞く一問
- 営業時間等の未確認・古い情報

生成数は通常2〜3案とし、「違いのない言い換え案」を作らない。

### 19.4 処理順

1. DBスコープと権限を確認する。
2. 構造化入力をsnapshot化し、versionを記録する。
3. 予約済み・営業時間・日程等のhard constraintsを決定的ロジックで検査する。
4. AIが異なる目的関数のPlanVariantを構成する。
5. ルールベースで重複、時間衝突、未確認値、全員の強い反対を再検査する。
6. PlanVariantをScheduleV2とは別に保存し、比較画面に出す。
7. 権限のある人が一案を選び、差分確認後にScheduleへ適用する。
8. 元データversionが変わっていれば再生成または再確認を求める。

### 19.5 ガードレール

- AI出力だけで営業時間・住所・Place ID・予約可否を確定しない。
- アレルギー、安全、交通、営業情報は公式情報の確認を促し、出典と鮮度を示す。
- 「多数決」を唯一の目的関数にしない。絶対行きたいと強い見送り、hard constraint、公平性を区別する。
- AIが投票を変更、候補を決定、予約、購入、push通知しない。
- 既存の propose_changes → 明示適用の分離を維持する。
- モデル・prompt・入力snapshot・出力・採否を追跡し、個人情報を運用ログへ重複記録しない。

### 19.6 品質評価

- hard constraint違反率
- 時間衝突率
- Place ID/座標の参照整合性
- 各案の実質的差異
- 不採用理由の入力データ整合性
- 希望充足度と最悪参加者の充足度
- 人が採用/一部採用/却下した割合
- 採用前に人が修正した項目数
- 虚偽の営業時間・予約・交通情報件数

## 20. グループ意思決定機能

### 20.1 機能評価

| 機能候補 | 現行で使えるもの | 必要な変更・新規データ | 推奨時期 |
|---|---|---|---|
| 登録不要 / ゲスト参加 | UUID URL、パスワードセッション | Itinerary単位Participant、署名付きguest session | **Must / Phase 1** |
| 共有URLからワンタップ参加 | 共有URL・モバイルWeb | 参加専用token、同意、表示名の最少入力 | **Must / Phase 1** |
| 参加者名 | なし | Participant.display_name。LINE名の自動保存はしない | **Must / Phase 1** |
| 絶対行きたい | 単一priorityは代用不可 | PreferenceVote enum | **Must / Phase 1** |
| 行けたら行きたい | 同上 | PreferenceVote enum | **Must / Phase 1** |
| どちらでもよい | 同上 | PreferenceVote enum | **Must / Phase 1** |
| 今回は見送り | 同上 | PreferenceVote enum。拒否と制約違反を混同しない | **Must / Phase 1** |
| 提案した人 | なし | WantToGoへのproposed_by相当、削除時の扱い | **Must / Phase 1** |
| 希望時間帯 | Scheduleの時刻、WantToGoの滞在時間 | 候補×参加者または候補共通のConstraint | **Should / Phase 1〜4** |
| 予算 | なし | TripConstraintと単位・範囲。費用管理とは分離 | **Should / Phase 1〜4** |
| 移動手段 | Google Maps route link | TripConstraint。実経路最適化は別機能 | **Should / Phase 1〜4** |
| 食事・アレルギー | Memoに書けるが不適切 | 明示同意、公開範囲、最小保持を伴うSensitiveConstraint | **Should。ただし法務/UX確認後** |
| 検討中 | なし | CandidateDecision.status | **Must / Phase 1** |
| 確認待ち | なし | statusと確認事項 | **Must / Phase 1** |
| 決定 | Schedule紐付けで暗黙表現 | 明示status。Schedule採用との整合ルール | **Must / Phase 1** |
| 見送り | なし | statusと任意理由 | **Must / Phase 1** |
| 営業時間 | なし | ExternalFact + source + fetched_at。Placeデータ規約確認 | **Could / Phase 3〜4** |
| 予約要否 | Memoで自由記述のみ | CandidateFact/ReservationRequirement。予約実行とは分離 | **Should / Phase 4** |
| 雨天対応 | なし | 候補属性またはExternalFact、出典・鮮度 | **Should / Phase 4** |
| 予定日未定 | WantToGo.planned_day=0 | そのまま維持。候補状態とは分ける | **実装済み / 維持** |
| 未決定事項一覧 | なし | status、未回答、欠落constraintから派生するquery/view | **Must / Phase 1** |
| 投票結果可視化 | priority表示のみ | 集計、分布、未回答、強い反対。匿名/記名設定 | **Must / Phase 1** |
| 合意状況 | なし | 決定ルールと派生表示。AIの断定値にしない | **Should / Phase 1〜4** |

### 20.2 推奨する投票語彙

内部値と日本語UIを固定し、1〜5の星とは別概念にする。

| 内部値 | UI | 意味 |
|---|---|---|
| must | 絶対行きたい | 強い希望。全候補で乱用しない説明を付ける |
| prefer | 行けたら行きたい | 積極的な賛成 |
| neutral | どちらでもよい | 反対ではない |
| pass | 今回は見送り | 今回の旅程には入れない希望。安全/アレルギー等のhard constraintは別入力 |

「未回答」はneutralに変換しない。集計では人数だけでなく分布と未回答数を出す。

### 20.3 候補状態

推奨状態遷移は、検討中 → 確認待ち → 決定または見送り。決定後も戻せるが、履歴と理由を残す。Scheduleへ追加されたから自動で決定とみなす移行期間を設けず、既存データは「状態未設定」として後方互換表示する。

### 20.4 合意の表示

「合意済み」はAIの確率ではなく、グループが選んだルールに基づく派生表示とする。MVPでは次で十分である。

- 全参加者回答済み / 未回答あり
- 強い希望あり
- 見送り希望あり
- 状態が決定 / 未決定
- 確認事項あり

自動的に決定へ遷移させず、幹事または許可された参加者が確定する。

## 21. 現状と目標のギャップ分析

| 能力 | 現状 | 目標 | ギャップの大きさ | 先行依存 |
|---|---|---|---|---|
| 相談初期の作成 | title + 日付必須のWeb作成 | LINEまたはWebでtitleだけのdraft | 中 | 日付未定時の全V2挙動 |
| 参加 | 秘密URL/共通password | 役割付きguest participant | 大 | identity、token、同意 |
| 候補 | WantToGo CRUD | 提案者、重複、状態付き候補 | 中 | Participant、状態履歴 |
| 希望 | 候補ごとに単一1〜5 | 参加者×候補の4段階 | 大 | Participant、unique vote |
| 合意 | なし | 未回答、対立、確認待ち、決定 | 大 | Vote、status、rule |
| 日程化 | planned_dayとScheduleを別操作 | plan variantを比較し、確認後にScheduleへ | 大 | 採用transaction、version |
| AI | 保存データへの回答・変更提案 | 参加者別希望から複数案と理由 | 大 | 意思決定データ、外部事実 |
| LINE | なし | 明示mentionの薄型Bot | 大 | 公式確認、Webhook基盤 |
| URL取込 | なし | 許可されたMaps URLを安全にPlaceへ | 大 | SSRF対策、Places、規約 |
| 権限 | view/edit共通token + password | view/join/edit/manageの能力分離 | 大 | token lifecycle |
| 同時編集 | last-write-wins | 行単位操作、version/conflict | 中 | API設計 |
| 計測 | 一部GA、actorなし | tokenを漏らさないfirst-party funnel | 大 | Participant、event taxonomy |
| 運用 | Web同期処理中心 | 2秒未満受付、queue、outbox、監視 | 大 | worker/queue選定 |
| Privacy | 現行Web/AI向け文言 | LINE/外部AI/削除/保持を明示 | 大 | LINE・法務確認 |

重要な依存順は、Participant → Vote/Status → 未決定 → PlanVariant/AIである。LINEはこのdomain serviceを呼ぶ入口として接続する。逆にLINE Viewから直接Itineraryを書き換えると、Webとの認可・上限・監査が分岐するため避ける。

## 22. 維持する既存機能

以下は利用実績を確認せず削除・置換しない。

- Itineraryと既存V1/V2データ
- 現行の /content/v2/&lt;pk&gt;/&lt;uuid&gt;/ URL
- 閲覧・編集passwordと既存sessionの互換
- Django Templates、現行V2 HTML、独自SCSS、Vanilla JavaScript
- 場所検索、地図、card/pinというユーザー能力。ただしGoogle Places + MapLibre/OpenFreeMapのprovider組合せは契約監査後に、許容構成を維持または移行する
- Map display adapterの抽象化
- 行きたい場所のcard、pin、modal、Day filter、予定日未定
- ScheduleV2、日別tab、当日/次予定強調、日別map、Google Maps route link
- MemoV2、ChecklistV2
- AI conciergeのlegacy経路とfeature-flagged Agent経路
- propose_changesと明示適用の分離
- URL scope、CSRF、入力上限、transaction/lock、非DEBUG error秘匿
- logo、icon、brand color

Bootstrapは現コードで確認できないため「維持対象の依存」とはしない。ただし見た目を全面刷新せず、既存Template/SCSSの互換性を保つ。

既存機能を将来廃止候補にする場合は、機能別eventと利用者ヒアリングで利用を確認し、代替、データmigration、旧URL、rollback feature flagを先に定義する。本戦略では廃止を提案しない。

## 23. 改善する既存機能

1. **作成**
   公開Product MVPは**日付未定draftを正式状態として採用する**。Phase 0でtotal_days前提の全View/Template/上限を互換監査し、成立しない、または移行費用が価値に見合わない場合は「Botで日程も聞く」へ暗黙に切り替えず、MVP scopeとH1をGo/No-Go reviewで再承認する。

2. **共有と権限**
   既存URLを維持しつつ、新規には閲覧・参加・編集・管理の能力を分ける。tokenには期限、失効、再発行、最後の利用、用途を持たせる。

3. **WantToGo**
   既存priorityは後方互換の「候補全体の参考重要度」として残し、個人投票へ転用しない。proposer、status、dedupe、versionを周辺modelで追加する。

4. **候補からSchedule**
   planned_dayは候補の希望日、ScheduleV2.day_indexは確定旅程の日と定義し、採用操作で明示的に同期する。暗黙の自動同期を避ける。

5. **共同編集**
   Memo/Checklist全体のリアルタイム化より、VoteやStatusを独立rowにして競合範囲を小さくする。Schedule等はoptimistic versionとconflict表示を検討する。

6. **モバイル**
   LINE iOS/Android内ブラウザ、外部ブラウザ、戻る、cookie、CSRF、MapLibre、Places、keyboard、safe areaを実機確認する。

7. **AI concierge**
   現行機能を残し、新しいdecision read toolsとPlanVariant提案を別Skillとしてfeature flag下に置く。既存の一問相談をAI幹事へ無理に統合しない。

8. **計測**
   UUIDをURLごと外部analyticsへ送らない。server-side first-party eventに、actorのpseudonymous ID、itinerary内部ID、source、action、timestampを保存し、分析時に集計する。

9. **Turnstile**
   作成画面の表示とserver-side検証が一致していない状態を、Bot公開前のsecurity backlogとして確認する。LINE WebhookにはTurnstileを使わず署名検証を使う。

10. **文書**
    docs/taskの実装待ち表記、READMEの公開しおり中心の将来像、design.md、ホームの未実装機能訴求を、戦略承認後に別Issueで整合させる。

11. **Google Maps Platform契約適合**
    現行のPlacesService/AutocompleteService → DB保存 → MapLibre/OpenFreeMap表示について、契約主体、billing account地域、利用Service、attribution、cache可能field、30日経過data、Place ID、end-user確認dataの扱いをGoogle/法務へ確認する。結論により、Google map表示、Places UI Kit、別の場所data provider等を比較し、既存data/URL/UXの移行・rollbackを設計する。

## 24. 新規開発する機能

### 24.1 MoSCoW一覧

| 優先 | 機能 |
|---|---|
| **Must** | M1 First-party event計測、M2 Guest Participantと参加導線、M3 参加者別4段階Vote、M4 Candidate Status/履歴/未決定、M5 権限/token lifecycle、M6 LINE Webhook core、M7 条件付きGroup Binding、M8 Audit/削除/Privacy、M9 日付未定Draft、M10 Bot Create/Check会話、M11 Proposer、M12 安全なManager取得/復旧 |
| **Should** | S1 構造化Constraint、S2 安全なGoogle Maps URL候補取込、S3 PlanVariantとAI幹事、S4 外部事実と限定通知、S5 候補からScheduleへの採用整合 |
| **Could** | C1 強い本人連携/LINE Login/LIFF、C2 継続利用portfolio（投票締切/secret ballot、複数旅行、template/再利用、V2 offline、予約、費用、公開しおりを需要順に個別判断） |
| **Won't now** | W1 全会話取込/無断scraping/AI自動確定、W2 成熟競合との機能数競争（独自routing、native全面開発、全画面realtime等） |

MoSCoW一覧の「機能」は実装Issueをそのまま束ねたものではなく、以下の**feature epic仕様カード**へ対応する。各cardは指定された10項目をすべて持ち、実装着手時にはそのcard内の機能を小さなIssueへ分割する。対応は Must=M1〜M12、Should=S1〜S5、Could=C1〜C2、Won't now=W1〜W2である。Could/Won'tの列挙項目はportfolio判断としてcardに束ねており、前倒しする場合は対象機能ごとに同じ10項目のcardを新設して再承認する。

### 24.2 Must仕様カード

#### M1. First-party event計測

- **解決する課題**: 現在の共同利用、離脱、AI採用を測れず、優先順位が推測になる。
- **ユーザー価値**: 直接見える機能ではないが、参加摩擦と不具合を改善できる。
- **競合との差**: 機能差ではなく、2人目の参加を継続最適化する学習速度。
- **既存機能との関係**: GA4は限定的。Concierge logはAI専用で流用しない。
- **想定実装範囲**: event taxonomy、server-side event store/送信層、tokenを含まないroute template、retention、dashboard/query。
- **技術的依存関係**: Participant仮IDの仕様。Phase 0では匿名sessionで先行可能。
- **セキュリティ上の注意**: UUID URL、password、LINE ID、原文、正確な位置をanalytics payloadへ送らない。
- **リスク**: 計測自体が個人追跡になる、二重発火、Bot retryの重複。
- **検証方法**: fixtureとstagingでevent一意性、漏えいscan、funnel再計算。
- **完了条件**: 作成→共有/LINE→open→join→候補→vote→status→Schedule採用を、重複除外して日次集計できる。

#### M2. Guest Participantと参加導線

- **解決する課題**: URLを開いた人が誰か、参加したかを表現できない。
- **ユーザー価値**: accountなしで表示名だけ設定し、投票と候補追加ができる。
- **競合との差**: 無登録自体はTravelCanvas等にもある。LINEから一tapで意思決定に入る点を検証する。
- **既存機能との関係**: ItineraryのUUID/password gateの内側に、Itinerary単位のParticipantを追加する。
- **想定実装範囲**: signed join token、Participant、role、HttpOnly secure cookie、join/leave/rename、同意version。
- **技術的依存関係**: token lifecycle、event、権限表。
- **セキュリティ上の注意**: join URLはbearer capabilityで、転送されたURLの所持者も参加できる。MVPではLINE group membershipを証明できないため、join以外の権限を含めず、期限・失効・再発行、session fixation、XSS、CSRF、なりすまし、未成年、削除を扱う。
- **リスク**: cookie削除で別人扱い、同名、複数端末、一人で複数Participant。
- **検証方法**: 5〜10組でjoin完了時間、2人目参加率、名前入力離脱、なりすまし報告。
- **完了条件**: accountなしの参加者が、他人のparticipant IDを操作できず、再訪時に自分のvoteへ戻れ、退出/削除できる。

#### M3. 参加者別4段階Vote

- **解決する課題**: 現priorityは最後の編集者が共有1値を上書きし、希望分布が分からない。
- **ユーザー価値**: 各自が短時間で希望を表し、未回答と反対も見える。
- **競合との差**: 投票単体はGoogle Maps、タビノワ、TravelCanvas、Limboにある。制約・状態・日程案への反映で差を作る。
- **既存機能との関係**: WantToGoに対する別model。priorityは残す。
- **想定実装範囲**: must/prefer/neutral/pass、unique participant×candidate、upsert、集計、未回答、本人の変更。
- **技術的依存関係**: Participant、行単位API、event。
- **セキュリティ上の注意**: cross-itinerary IDOR、重複、不正bulk vote、匿名性設定。
- **リスク**: 「pass」が拒否なのか無関心なのか曖昧、must乱用、多数決圧力。
- **検証方法**: 語彙比較、投票完了率、候補あたり回答率、決定までの時間、定性面談。
- **完了条件**: 4段階・未回答を区別し、同一参加者の票を原子的に一件へ保ち、権限別に集計を表示できる。

#### M4. Candidate Status、履歴、未決定事項

- **解決する課題**: 候補が出ただけで、決定/見送り/確認待ちがLINEへ戻る。
- **ユーザー価値**: 何が決まり、次に何を確認すべきかが一画面で分かる。
- **競合との差**: Limboは明確な投票workflowを持つ。TabiSyncは旅行事実確認とSchedule反映まで接続する。
- **既存機能との関係**: WantToGoを候補entityとして包み、planned_dayとは別にする。
- **想定実装範囲**: considering/needs_confirmation/decided/rejected、actor、reason、history、未回答/不足情報query。
- **技術的依存関係**: Participant/role、Vote、event、optimistic version。
- **セキュリティ上の注意**: status変更権限、監査、stored XSS、競合更新。
- **リスク**: workflowが重い、決定の定義がgroupごとに違う、状態とScheduleが食い違う。
- **検証方法**: 未決定一覧の利用率、status更新率、LINEで同じ質問が再発する回数。
- **完了条件**: 許可actorだけが遷移でき、履歴と理由が残り、未決定queryがVote/Statusと整合する。

#### M5. 権限分離とtoken lifecycle

- **解決する課題**: 同じ秘密URLが転送され、password未設定なら編集まで可能で、再発行もできない。
- **ユーザー価値**: 閲覧、参加、編集、管理を必要な人だけに渡し、漏えい時に止められる。
- **競合との差**: Wanderlog/Limbo等の権限分離に対する最低条件で、独自差ではない。
- **既存機能との関係**: 現UUID/password/sessionを壊さず、新規InviteGrant/roleを追加する。
- **想定実装範囲**: view/join/edit/manage token、expiry、revoke、rotate、使用回数、管理UI、旧URL互換。
- **技術的依存関係**: Participant、access control service、migration/compat plan。
- **セキュリティ上の注意**: join grant所持者は転送先でも参加でき、membership証明ではない。tokenはhash保存し、manage tokenはgroup、Referer、analytics、広告、OGP、log、localStorageから除外する。constant-time比較とrate limitを使う。
- **リスク**: 導線が複雑、旧URLの期待を壊す、復旧できない。
- **検証方法**: 権限matrix test、token leak review、ユーザビリティtest、rollback。
- **完了条件**: 各roleの許可/拒否が自動testされ、tokenを個別失効・再発行でき、旧URLと既存sessionが継続する。

#### M6. LINE Webhook core

- **解決する課題**: LINEを安全な入口として受ける実装がない。
- **ユーザー価値**: グループ内で招待・メンションするだけで最小操作を起動できる。
- **競合との差**: MapMemo/Lightsplitが既に入口を実証。TabiSync独自差ではなく中核体験の接続層。
- **既存機能との関係**: Viewから直接model操作せず、Webと共通のapplication serviceを呼ぶ。
- **想定実装範囲**: raw signature、events[]、join/message/edit/unsend/leave/postback、webhookEventId receipt、queue、reply/push outbox、retry key、metrics、OA Response settings checklist。
- **技術的依存関係**: LINE OA/channel、public HTTPS、worker、secret management、domain service。
- **セキュリティ上の注意**: parse前署名、2秒未満応答、本文log禁止、mention.isSelf、mention欠落時はBot発行postback actionをintent fallbackに限定してidentityには使わない、Greeting/Auto-response無効化、idempotency、outbound allowlist。
- **リスク**: reply token失効、重複/逆順、queue障害、誤返信、月間quota。
- **検証方法**: 公式fixture、invalid signature、複数events、redelivery、userId/mention object欠落、room、unsend、Response settings、timeout E2E。
- **完了条件**: 対象外本文を保存せず、同一eventを二重適用せず、2秒以内に受付し、基本commandをreply中心で完結する。

#### M7. 条件付きLINE Group Binding

- **解決する課題**: 毎回しおりを指定せず、現在の旅行へ命令を向けたい。
- **ユーザー価値**: 1グループ1進行中の分かりやすい文脈。
- **競合との差**: LINE groupから継続する体験の土台。
- **既存機能との関係**: Itineraryとは別のbinding/historyにし、しおりの生存をLINEへ依存させない。
- **想定実装範囲**: source type、条件付きencrypted IDとlookup digest、active itinerary、joined/disconnected、archive/switch、原子的一意制約。
- **技術的依存関係**: **LINEによるgroupId保存可否の書面回答**、key management、M6。
- **セキュリティ上の注意**: 暗号化、key rotation、退出/終了時削除、cross-group scope、管理者不在。
- **リスク**: ポリシーで実装不可、group一覧復元不可、招待者をownerにできない。
- **検証方法**: 公式回答、法務review、2グループ/同時作成/退出/再招待E2E。
- **完了条件**: 許可文書を保存し、1 active制約・削除期限・復旧/縮退経路をtestできる。回答が得られなければこの機能は実装しない。

#### M8. Audit、削除、Privacy controls

- **解決する課題**: 誰がWeb/LINE/AIから変更したか、unsend/退出/削除を追えない。
- **ユーザー価値**: 誤操作を説明・取消でき、保存範囲を理解できる。
- **競合との差**: 目立つ差ではなく、グループ会話とAIを扱う必須信頼基盤。
- **既存機能との関係**: Concierge logsとは分離し、PIIの複製を避ける。
- **想定実装範囲**: actor/source/action/object/result、message mapping TTL、delete/tombstone、consent version、retention job、export/delete request。
- **技術的依存関係**: Participant、Webhook receipt、policy/retention decision。
- **セキュリティ上の注意**: auditに原文/token/identifierを入れない、権限付き閲覧、tamper evidence、backup削除方針。
- **リスク**: audit自体が長期の個人追跡、unsend後に派生データだけ残る。
- **検証方法**: data inventory、retention test、unsend race、退出/退会/delete drill。
- **完了条件**: 各data classに目的・保持期間・削除trigger・閲覧者があり、自動削除と利用者請求をtestできる。

#### M9. 日付未定Draft

- **解決する課題**: 相談開始時は日程が未定なのに、現行作成formと多くのV2処理が開始日・終了日を前提にする。
- **ユーザー価値**: 旅行名だけで候補集めを始め、日程は合意後に設定できる。
- **競合との差**: draft自体は独自差ではないが、LINEで散らかる最初期へ入るための必須条件。
- **既存機能との関係**: Itinerary、作成form、`total_days`、ScheduleV2、WantToGo `planned_day`、AI read/proposal、表示/共有を後方互換で拡張する。
- **想定実装範囲**: lifecycle/dates_confirmed、Web/Bot共通create service、日付設定transaction、draft表示、日付依存actionのguard、既存rowの既定状態。
- **技術的依存関係**: 全View/Template/helper/testのdate前提inventory、schema/ADR、M1、feature flag/rollback。
- **セキュリティ上の注意**: draftでも既存と同じ作成rate limit、Turnstile方針、token scope、削除を適用し、未設定値で認可を迂回させない。
- **リスク**: runtime error、空の日tab、上限誤計算、SEO/共有の壊れ、既存data migration事故。
- **検証方法**: date dependency静的inventory、全V2 routeのdraft matrix、作成→後日設定→Schedule採用のmobile E2E、既存row回帰。
- **完了条件**: titleだけのdraftが全許可画面で安全に表示され、日付依存操作は説明付きで停止し、後から日付を一度のtransactionで確定できる。成立しなければ公開MVPを再承認する。

#### M10. Bot Create / Check会話

- **解決する課題**: Botを招待しても、曖昧な自然言語から安全に作成・確認へ進む最小会話がない。
- **ユーザー価値**: 明示操作だけでdraftを作り、同じ進行中のしおりへ戻れる。
- **競合との差**: Bot command自体は差でなく、共同意思決定Webへ一貫してつながる完了率が差になる。
- **既存機能との関係**: M9の共通create serviceと既存共有URL生成を呼び、LINE Viewから直接Itineraryを変更しない。
- **想定実装範囲**: join案内、create質問状態、title validation、作成、check、disconnect、用途限定join reply、既存active時の分岐、copy/error文言。
- **技術的依存関係**: M2、M6、条件付きM7、M9、M12、LINE公式/法務Go、Response settings。
- **セキュリティ上の注意**: 構造化mentionまたはBot発行postbackだけを起点にし、mention欠落時に表示名文字列を信用しない。状態TTL、initiator、idempotency、reply template allowlistを持つ。
- **リスク**: 同時作成、他人の回答をtitle扱い、古いstate、groupへの高権限token誤送信、reply期限切れ。
- **検証方法**: multi-user conversation fixture、mention欠落、期限切れ、concurrent create、既存active、転送join URL、response settingを含むE2Eと実機task test。
- **完了条件**: 一般会話を保存/命令化せずcreate/check/disconnectが冪等に動き、groupへはmanage/editを含まない失効可能join grantだけを返す。

#### M11. Proposer

- **解決する課題**: 現行WantToGoから誰が提案した候補か分からず、確認先とAI説明を作れない。
- **ユーザー価値**: 候補の意図を本人へ確認でき、自分の提案が見える。
- **競合との差**: 単なる票数でなく、提案・理由・条件を意思決定履歴へ残す土台。
- **既存機能との関係**: WantToGo.priorityは変えず、ItineraryParticipantとの追加関係またはCandidate wrapperで表現する。
- **想定実装範囲**: proposed_by、source(web/LINE/import/system)、created_at、匿名化/削除時表示、既存候補のunknown proposer。
- **技術的依存関係**: M2、Participant削除方針、M8、candidate creation共通service。
- **セキュリティ上の注意**: 表示名の公開範囲、なりすまし、cross-itinerary FK、削除後の匿名化、LINE userId非表示。
- **リスク**: 提案者を責める圧力、既存候補への誤帰属、Participant削除で履歴が壊れる。
- **検証方法**: 提案者表示の理解、確認往復の減少、削除/匿名化/cross-scope tests、既存候補表示test。
- **完了条件**: 新規候補へ許可actor/sourceを一貫して記録し、既存候補はunknownのまま、削除後も定めた匿名化規則で履歴整合を保つ。

#### M12. 安全なManager取得・復旧

- **解決する課題**: group command senderとWeb guestを安全に結べず、groupへmanage URLを返すと全員・転送先へ高権限が漏れる。
- **ユーザー価値**: 作成者がtoken失効、role、削除を管理でき、端末喪失時にも復旧できる。
- **競合との差**: 独自機能ではなく、無登録参加と安全な管理を両立する公開条件。
- **既存機能との関係**: 既存edit password/sessionを互換fallbackとして扱い、M2 ParticipantとM5 InviteGrantへManager identityを追加する。
- **想定実装範囲**: Bot作成を保つ1対1 reply claimまたはManager限定LINE Login、短寿命one-time claim、expected actor照合、recovery、複数Manager、revoke-all、管理者不在処理。Web-firstはBot作成を外すpivotとして別評価。
- **技術的依存関係**: M2/M5/M6、`source.userId`取得条件、友だち/1対1送信の実機検証、必要時はManager限定LINE Loginまたはemail identityのADR。
- **セキュリティ上の注意**: group/OGP/広告/analytics/Referer/log/localStorageへmanage tokenを出さず、先着claim、token replay、account recovery乗っ取りを防ぐ。
- **リスク**: userId欠落、友だち未追加でprivate delivery不可、claim離脱、本人性を上げるほど登録不要価値が下がる。
- **検証方法**: friend/7日条件、userId欠落、group→1対1またはManager限定Login照合、postback actor非依存、別人/replay、端末喪失、全token失効、復旧supportのPhase 0実機/E2E。
- **完了条件**: 選定方式とfallbackをADR化し、作成者以外がclaimできず、manage grantをgroupへ露出せず、紛失時に本人確認付きで復旧できる。方式未確定なら公開BotはNo-Go。

### 24.3 Should仕様カード

#### S1. 構造化Constraint

- **解決する課題**: 時間・予算・移動・食事制約が日程化直前まで分からない。
- **ユーザー価値**: AIと幹事が後戻りを減らせる。
- **競合との差**: 単純投票より、条件付きの希望を扱える。
- **既存機能との関係**: WantToGo、stay_minutes、Memoを参照するが、Memoを正本にしない。
- **想定実装範囲**: TripConstraint、CandidateConstraint、visibility、hard/soft、source。
- **技術的依存関係**: Participant、Privacy設計、AI schema。
- **セキュリティ上の注意**: アレルギー等は機微性が高く、任意、目的限定、公開範囲、短期保持。
- **リスク**: 入力負担、誤った医療的解釈、単位不整合。
- **検証方法**: 後から発覚した制約数、入力率、離脱、AI案修正率。
- **完了条件**: 必須/任意とhard/softを区別し、公開範囲と削除を本人が管理できる。

#### S2. 安全なGoogle Maps URL候補取込

- **解決する課題**: LINEのMaps URLをWebで再検索・転記する。
- **ユーザー価値**: 明示投稿から少ない操作で候補化できる。
- **競合との差**: MapMemoが既にURL保存を実現。投票・status・旅程までつなぐ必要がある。
- **既存機能との関係**: WantToGoのPlace ID/座標、Google Places検索へ接続。
- **想定実装範囲**: exact allowlist、短縮URL展開、Place解決、candidate preview、confirm、dedupe、failure UI、cost meter。
- **技術的依存関係**: SSRF-safe resolver、**現行利用を含むGoogle Maps Platform契約監査のGo**、許可されたPlaces/provider構成、queue、M6。
- **セキュリティ上の注意**: private/link-local/metadata IP、DNS rebinding、redirect、byte/time/content-type上限、credential URL、log redaction。
- **リスク**: Google URL形式変更、Maps料金、誤Place、利用規約違反。
- **検証方法**: URL corpus、malicious redirects、解決率、確認修正率、1候補原価。
- **完了条件**: 許可URLだけを安全に展開し、Place IDを確証できない場合は保存せず人へ選択を返し、重複を提示する。

#### S3. PlanVariantとAI幹事

- **解決する課題**: 一案を作る幹事負担と、なぜその案か説明できない。
- **ユーザー価値**: 異なるトレードオフの2〜3案を比較し、人が選べる。
- **競合との差**: AI旅程は一般化済み。参加者別希望・反対・未決定・不採用理由を明示する点。
- **既存機能との関係**: Agent Skill/Toolとpropose→applyを再利用し、Scheduleとは別draft modelを置く。
- **想定実装範囲**: snapshot、variant/items、objective、score/explanation、feedback、adopt transaction。
- **技術的依存関係**: Vote/Status/Constraint、外部事実、LINE・法務によるAI送信許可。
- **セキュリティ上の注意**: prompt injection、PII最小化、model retention/DPA、費用上限、権限再確認。
- **リスク**: hallucination、似た案、少数意見の抑圧、誤った最新情報。
- **検証方法**: offline eval、constraint violation、案差異、採用率、修正量、面談。
- **完了条件**: 2〜3案がschemaに従い、hard constraint再検査を通り、理由・不採用・未確認を出し、確認なしにScheduleを変更しない。

#### S4. 外部事実と限定通知

- **解決する課題**: 営業時間、予約、雨天、期限が古い/未確認のまま決定される。
- **ユーザー価値**: 最新性と確認責任が分かり、必要な時だけ通知される。
- **競合との差**: AI文章ではなく出典・取得時刻・確認者を見せる。
- **既存機能との関係**: Google Places等を候補metadataへ。Botは概要とWeb linkだけ。
- **想定実装範囲**: ExternalFact、source/fetched_at/expires_at、manual verification、opt-in notification/outbox、quota。
- **技術的依存関係**: 正式API契約、worker、M6/M8。
- **セキュリティ上の注意**: 外部URL、API key、push先、利用目的、グループ情報の利用時点制限。
- **リスク**: stale data、API停止、通知疲れ、LINE費用。
- **検証方法**: stale率、誤通知、opt-out、通知からの解決率、原価。
- **完了条件**: 出典・鮮度なしの事実を確定表示せず、通知は明示opt-in・budget内・取消可能。

#### S5. 候補からScheduleへの採用整合

- **解決する課題**: WantToGoの `planned_day`、Candidate Status、ScheduleV2のday/itemが別操作で食い違う。
- **ユーザー価値**: 「決定した候補」がいつ旅程へ入ったか分かり、二重登録や消失を避けられる。
- **競合との差**: tabitteも決定候補のSchedule copyを提供するため、copy自体ではなく履歴・version・AI案との一貫性が差の候補。
- **既存機能との関係**: WantToGoとScheduleV2の既存FK・日別UIを維持し、暗黙同期を追加しない。
- **想定実装範囲**: explicit adopt action、day/time確認、Schedule row作成/更新、decision history、source candidate、idempotency、undo/再採用規則。
- **技術的依存関係**: M4、Itinerary/Schedule version、M8、将来のPlanVariant Adoption。
- **セキュリティ上の注意**: edit権限、cross-itinerary IDOR、concurrent adoption、AI経路でも確認時に再認可。
- **リスク**: 既存手動Scheduleとの重複、statusだけ先に決定、undoで履歴が不整合、予定上限超過。
- **検証方法**: decide→adopt→undo、concurrency、limit、既存Schedule、planned_day不一致、AI proposalのintegration tests。
- **完了条件**: 人が差分と日を確認した一つのtransactionだけがScheduleを変更し、再実行が重複せず、候補・status・履歴から採用結果を追跡できる。

### 24.4 Could仕様カード

#### C1. 強い本人連携、LINE Login / account linking / LIFF

- **解決する課題**: cookie削除、複数端末、なりすまし、長期復帰。
- **ユーザー価値**: 自分の参加・投票へ安全に戻れる。
- **競合との差**: LINE Login自体は差ではない。
- **既存機能との関係**: accountless guestを残し、必要な人だけupgradeする。
- **想定実装範囲**: 同一provider、ID token server検証、account link nonce、unlink、deauthorize。
- **技術的依存関係**: 自社User設計、LINE審査、Privacy、M2。
- **セキュリティ上の注意**: client profile値を本人確認に使わない、token検証、provider分離、解除/退会。
- **リスク**: 登録摩擦、同意範囲増大、guest merge事故。
- **検証方法**: multi-device失敗率、なりすまし率、login funnel A/B。
- **完了条件**: guestを強制せず安全にlink/unlinkでき、重複participant mergeをrollbackできる。

#### C2. 継続利用機能

- **解決する課題**: 旅行後の再利用と収益機会がない。
- **ユーザー価値**: 過去旅行、template、offline、予約、費用、公開共有を再利用できる。
- **競合との差**: 多くは競合が強く、単独差にならない。
- **既存機能との関係**: Itinerary、Checklist、Memo、blog tokenを活かす。
- **想定実装範囲**: archive/template/cloneから、需要順に一つずつ。予約・費用・publicを束ねて同時実装しない。
- **技術的依存関係**: retention/ownership、収益仮説、V2 service worker等。
- **セキュリティ上の注意**: 古いtoken、個人/予約/支払情報、公開範囲。
- **リスク**: core検証前のscope拡大、成熟競合との正面衝突。
- **検証方法**: 2回目作成率、要望頻度、WTP、旅行中/後event。
- **完了条件**: 各機能ごとに先行KPIと撤退基準を置き、core共同参加率を悪化させない。

### 24.5 Won't now仕様カード

#### W1. 全会話取込、無断scraping、AI自動確定

- **解決する課題**: 自動化を最大化したい要求。
- **ユーザー価値**: 見かけ上の操作は減る。
- **競合との差**: 差より信頼・規約リスクが大きい。
- **既存機能との関係**: 現行AIの明示入力・確認適用原則に反する。
- **想定実装範囲**: **当面実装しない**。明示mention/postback/収集modeと許可APIだけ。
- **技術的依存関係**: なし。
- **セキュリティ上の注意**: 同意、著作権、規約、個人情報、prompt injection、誤予約。
- **リスク**: LINE停止、ユーザー信頼喪失、法的問題。
- **検証方法**: 自動化要求はinterviewで記録するが、実データ収集で試さない。
- **完了条件**: backlogに実装Issueを作らず、境界をprivacy notice・architecture testで守る。

#### W2. 成熟競合との機能数競争

- **解決する課題**: 「全部入り」に見せたい要求。
- **ユーザー価値**: 一つのappで完結する可能性。
- **競合との差**: Wanderlog/NAVITIME/tabiori/Funlidayが優位で、差にならない。
- **既存機能との関係**: 現行V2を維持するが、native app、独自route、予約、写真、費用、offlineを同時拡張しない。
- **想定実装範囲**: **当面実装しない**。
- **技術的依存関係**: 大規模な外部data/契約/運用。
- **セキュリティ上の注意**: 支払・予約・位置履歴はriskを急増させる。
- **リスク**: coreの検証遅延、保守不能。
- **検証方法**: core利用後の要望と離脱理由を計測。
- **完了条件**: roadmap reviewで北極星への寄与を示せない機能をPhase 5より前へ入れない。

## 25. 当面開発しない機能

次は「価値がない」ではなく、初期仮説の検証を遅らせ、競合優位または規約リスクが大きいため保留する。

- LINE一般会話全文の保存・要約・AI送信
- Bot参加前の履歴取得を前提にしたimport
- Instagram/TikTok等のHTML scraping
- 不確実なURLをLLMだけでPlaceに確定
- AIによる候補status確定、Schedule即時反映、予約、購入
- LINEグループへの定期push既定ON
- LINE全member IDの取得を必須にする設計
- 全参加者へのLINE Login、LIFF、Mini AppのMVP強制。Manager限定の本人連携はM12の結果で別判断
- 複数の進行中旅行と自然言語だけの自動切替
- 公開しおりmarketplace
- 航空・宿泊予約、価格比較、決済、割勘
- 独自公共交通/車route最適化
- native iOS/Android app
- V2全面offline、写真album、旅行SNS
- V1削除、既存URL変更、全面UI redesign

## 26. データモデルへの影響

以下は影響範囲を示す概念案であり、今回モデル変更やmigrationは行わない。名称・fieldは実装IssueでADRとschema reviewを経て確定する。

### 26.1 再利用する中心

- Itinerary: 旅行の集約root
- WantToGo: 場所候補
- ScheduleV2: 人が採用した確定旅程
- MemoV2 / ChecklistV2: 補足と実行支援
- ConciergeChatLog / ToolCallLog: 既存AI経路のrun追跡

Itinerary.reset_emailをowner IDに、WantToGo.priorityを個人Voteに、MemoをConstraintに流用してはならない。

### 26.2 概念model

| 概念model | 主なfield / 制約 | 目的・既存との関係 |
|---|---|---|
| **ItineraryLifecycle** またはItinerary追加field | draft/active/archived/deleted、dates_confirmed、version | 旅行名だけのdraft、active/historyを表す。既存rowはactive相当へ後方互換 |
| **ItineraryParticipant** | itinerary FK、public UUID、display_name、role、status、guest session digest、optional account、consent_version、joined_at | Itinerary内だけの人物。LINE全体の人格と無条件統合しない |
| **InviteGrant** | itinerary、purpose(view/join/edit/manage)、token digest、expires_at、revoked_at、max/use count | 既存Itinerary.tokenを壊さず、新規招待のbearer能力とlifecycleを分離。joinはLINE membership証明ではない |
| **ManagerClaim** | itinerary、expected actor reference、token digest、delivery channel、expires/used/revoked、recovery state | 高権限tokenをgroupへ出さず、作成者のprivate claimと復旧を追う。方式はPhase 0 ADR後のみ |
| **CandidateDecision** | one-to-one WantToGo、status、version、changed_by、reason、decided_at | 候補状態。planned_dayと分ける |
| **CandidateStatusHistory** | decision、from/to、actor、source、reason、created_at | 説明・監査・競合解決 |
| **PreferenceVote** | candidate、participant、value、note(optional)、updated_at、unique(candidate, participant) | 4段階個人Vote。priorityを上書きしない |
| **CandidateProposer** またはCandidate追加field | candidate、participant(optional)、source、created_at、anonymized_at | 提案者と入力経路。既存候補はunknownで、LINE userIdを表示しない |
| **TripConstraint** | itinerary、participant(optional)、type、hardness、value/unit、visibility、source、expires_at | 予算、移動、時間等。機微情報は分離/最小化 |
| **CandidateConstraint / ExternalFact** | candidate、type、value、source_url/source_name、observed_at、expires_at、verification_status | 営業時間、予約要否、雨天等の出典と鮮度 |
| **DecisionIssue** | itinerary、candidate(optional)、type、status、question、owner(optional)、due_at | 未決定を明示保存する場合。MVPではVote/Statusから派生queryで始めてもよい |
| **PlanVariant** | itinerary、input_snapshot/version、objective、status、summary、model metadata、created_by | 確定Scheduleと分離したAI/手動案 |
| **PlanVariantItem** | variant、candidate/Schedule参照、day/order/time、assumptions | 案の項目 |
| **PlanFeedback / Adoption** | variant、participant、reaction、adopted_by、adopted_at、resulting_version | 比較、採否、Schedule適用 |
| **ProductEvent** | event_id、actor pseudonym、itinerary internal ID、source、name、properties allowlist、occurred_at | 北極星とfunnel。秘密値を入れない |
| **AuditEvent** | actor、source(web/LINE/AI/system)、action、object ref、result、created_at | 操作説明。raw本文は入れない |
| **LineWebhookReceipt** | webhook_event_id unique、type、message_id(optional)、occurred_at、received_at、status、redelivery | 重複排除と処理状態。payload本文は原則保存しない |
| **LineEphemeralState** | source lookup、initiator(optional)、state、version、expires_at、minimal payload | 旅行名質問、収集mode等。短期TTL |
| **LineConversationBinding** | source type、encrypted group/room ID、lookup digest、active itinerary、state、joined/left | **公式に長期保存が許可された場合のみ** |
| **LineOutboundMessage** | job UUID/retry key、target ref、kind、payload digest、status、attempts、quota cost | push/replyのoutboxと重複防止 |
| **PlaceImportAttempt** | input domain、URL digest、resolution status、Place ID、error class、expires_at | URL原文を長期保持せず解析・原価・失敗を追う |
| **PlaceDataProvenance** | candidate、provider/service、field class、obtained/confirmed/refresh時刻、retention class、attribution version | 現行/新規の場所fieldがどの契約・保持条件に従うかを監査。schema化の要否はGoogle/法務判断後 |

### 26.3 主な一意性・整合性

- PreferenceVote: candidate + participantで一件。
- CandidateDecision: WantToGoごとに一件。
- active binding: 許可される場合、source identityごとにactive一件。
- LineWebhookReceipt: webhookEventIdで一件。HTTP request単位ではなくevent単位。
- ManagerClaim: 未使用の有効claimを目的/actor単位で一件にし、使用時は原子的にconsumeする。
- outbound push: job UUIDをX-Line-Retry-Keyにし、payloadと宛先を再試行で変えない。
- Schedule採用: Itinerary versionまたは選択範囲のoptimistic lockを検査。
- WantToGo dedupe: Place ID一致を第一候補。Place IDがない場合は正規化name/address/座標近接を候補提示に使い、自動mergeしない。

### 26.4 LINE識別子

漏えい対策として、API送信に必要なgroupId/userIdはapplication-level encryption、検索にはkeyed HMAC、鍵はDB外でrotation可能にする案が妥当である。しかし、これは**保存が規約上許可された後の安全策**であり、保存可否の代替ではない。

userIdがWebhookにない正常系を許容する。グループmember一覧をParticipantの正本にせず、Webで明示参加した人だけをItineraryParticipantにする。LINE Loginを追加する場合も同一provider、unlink、退会、guest mergeを別途設計する。

### 26.5 後方互換とmigration時の注意

- 既存Itinerary.token、blog_embed_token、password、URLを維持する。
- 既存WantToGoにVoteを自動生成しない。priorityを特定人物の意思と推測しない。
- 既存WantToGoのstatusは「未設定」とし、勝手にdecidedへしない。
- datesが必須だった既存View/Templateでdraftを開いた場合の表示を全経路で定義する。
- planned_dayとScheduleV2.day_indexの優先規則を明文化し、採用serviceでだけ変換する。
- Participant削除時、Vote/提案者/履歴を物理削除・匿名化・SET_NULLのどれにするか、Privacy要件から決める。
- manage token/claimは既存の「最近のしおり」localStorageへ決して追加せず、移行時に第三者scriptのない専用routeを使う。
- LINE bindingを削除してもItineraryは削除しない。逆方向も明示状態を持つ。

## 27. システム構成案

### 27.1 論理構成

~~~mermaid
flowchart LR
    G[LINEグループ] --> LP[LINE Platform]
    LP -->|HTTPS Webhook| WH[署名検証・Receipt]
    WH -->|2秒以内に2xx| LP
    WH --> Q[Queue / Worker]
    Q --> APP[共通Application Service]
    APP --> DB[(PostgreSQL)]
    APP --> OUT[Reply / Push Outbox]
    OUT --> LP

    W[TabiSync Web] --> AUTH[Access / Participant]
    AUTH --> APP
    APP --> PLACE[Google Places等]
    APP --> AI[OpenAI / AI幹事]
    AI -->|PlanVariant / Proposal| DB
    DB --> W
~~~

### 27.2 境界

- Webhook endpointはraw bytesで署名を検証し、events[]を個別receipt化して、2秒未満を目標に応答する。
- 署名失敗は副作用なし。対象外の通常会話は本文を保存せず2xx。
- queue workerがmention/postback/有効stateだけをcommandへ変換する。
- WebとLINEは同じapplication service、validation、limit、transaction、auditを通る。
- AI、Places、短縮URL解決はWebhook requestから切り離す。
- AIはDBを直接更新せずPlanVariant/Proposalを返す。採用serviceが権限とversionを再確認する。
- reply tokenが間に合う単純操作はreply、長時間処理は受付reply後にWebで確認し、必要時だけretry-key付きpush。

### 27.3 非同期基盤

現リポジトリにはqueue/worker/Redisがない。Phase 0で次を比較する。

- PostgreSQL-backed job + transactional outbox: 依存は少ないが、polling、lock、retry、dead-letterを自前設計する。
- Celery/RQ等 + broker: 成熟したretry/worker運用があるが、Python 3.8対応、broker、deploy/monitoringが増える。

選定条件は、Webhook p99、outbox整合性、運用人数、失敗復旧、Python更新計画であり、流行だけで決めない。いずれも「DB変更とoutbound messageの二重書き」を避けるtransactional outboxを持つ。

### 27.4 既存インフラへの影響

- docker-composeへworker/brokerを足す可能性がある。
- Gunicorn timeoutをAI待ち時間で伸ばすのではなく、requestを短くする。
- Nginx/CloudflareがWebhook bodyを変更せず、HTTPS、body size、timeout、WAFを適切に通すか確認する。
- Channel secret/access tokenは環境変数またはsecret managerで保持し、log、DB、clientへ出さない。
- deploy workflowには現在test/check CIを確認できない。Webhook/security change前にCI gateを別Issueで検討する。
- entrypointの起動時makemigrationsは、worker/複数instance化前に運用見直しが必要。

### 27.5 可用性と縮退

- LINE障害時もWeb URLで計画を継続できる。
- AI障害時もVote/Status/Scheduleは利用できる。
- Places障害時は手入力候補を許すが、未確認表示にする。
- queue障害時はWebhookを無条件に成功扱いして失わず、receipt insert/queue境界の設計に従い非2xxまたはDB jobへ残す。
- quota超過時はpush/AIを止め、replyまたはWebで明示する。作成済み旅程を壊さない。

## 28. セキュリティ

### 28.1 Threat / Control

| 脅威・要件 | 推奨control | 検証 |
|---|---|---|
| 偽Webhook | raw body + channel secretのHMAC-SHA256、constant-time比較、parse前実施 | 改行/絵文字/invalid/missing header fixture |
| 重複・再送 | webhookEventId unique、冪等command、transaction、outbound retry key | duplicate/redelivery/timeout/409 test |
| 逆順event | timestamp、object version、状態遷移guard | edit→unsend、leave→late message、concurrent create |
| 遅い処理 | 2秒未満受付、queue、AI/URL分離 | load test、p95/p99、queue outage |
| reply token誤用 | 一回、原則1分未満、使用状態、blind retry禁止 | expired/used/redelivery test |
| group/user ID漏えい | 許可後だけ暗号化保存、HMAC lookup、key rotation、log redaction | DB dump/log scan、rotation drill |
| Bot誤送信 | Template allowlist、manage/edit token・個人情報を非送信。join grantは用途限定・期限/失効付きのTabiSync URLだけ。Bot送信は取消不可と想定 | snapshot test、red-team prompt、転送scenario |
| 一般会話の過剰処理 | 構造化mention.isSelf、Bot発行postback action、有効stateのみ。postbackはintent限定でidentityに使わず、mention欠落を文字列名で代替しない | consent/mention欠落、unrelated chat fixture、observability without text |
| URL/token漏えい | 用途別token、hash保存、短期/失効、Referrer-Policy、analytics scrub、OGP設計。manage tokenはlocalStorage禁止 | external request inspection、shared-device、rotate/revoke test |
| 秘密URL page上の第三者JS | join/manage/claim routeから広告・第三者analyticsを除外し、CSP、Subresource Integrityまたはself-host、Referrerを監査。既存V2もdata flowを棚卸し | browser network/DOM inspection、CSP report、XSS scenario |
| QR生成fallback | qrcode依存を本番必須にし、秘密share URLをapi.qrserver.comへ送るfallbackを新token設計で使用しない | dependency欠落test、outbound network inspection |
| Guestなりすまし | signed HttpOnly secure cookie、join grant、role、optional link upgrade | session fixation、stolen token scenario |
| 重複投票 | DB unique、upsert、rate limit。強い本人性が必要ならoptional Login | concurrent vote test、cookie resetを別指標化 |
| IDOR | すべてItinerary scopeでcandidate/participant/variantを解決 | cross-itinerary testを全endpointへ |
| CSRF | Web session操作にDjango CSRF、SameSite、Origin/Referer確認 | missing/wrong token test |
| XSS | Django escaping、JSON安全埋込、URL scheme allowlist、Markdown sanitizer | stored XSS payload、CSP検討 |
| SSRF | 第28.3節のresolver。LLMへfetchさせない | private IP、redirect、DNS rebinding corpus |
| Bot大量message | group/user/channel token bucket、command/URL数上限、block/leave手順 | burst/slow abuse test |
| AI費用悪用 | explicit action、daily/group budget、model/tool/run上限、circuit breaker | quota/concurrency/billing alarm |
| LINE外への流出 | groupへ最少summary、Web permission、転送可能性の表示、token失効 | 別group転送E2E |
| 個人/位置情報 | data minimization、visibility、retention、delete/export、AI redaction | inventory/retention/DSAR drill |
| secret漏えい | environment/secret manager、最小権限、rotation、no client/log | secret scanning、rotation rehearsal |
| 管理/監査権限 | audit viewer制限、operator action記録、PII非格納 | authorization tests |
| Manager bootstrap乗っ取り | expected actorとのprivate claim、短期一回token、先着claim禁止、本人確認付きrecovery、revoke-all | userId欠落、別人、replay、端末喪失E2E |

### 28.2 権限表の原則

| Action | Viewer | Participant | Editor | Manager | Bot/System |
|---|---:|---:|---:|---:|---:|
| 旅程閲覧 | ○ | ○ | ○ | ○ | scope内 |
| 自分のVote | × | ○ | ○ | ○ | 明示postback時のみ |
| 候補追加 | × | 設定で○ | ○ | ○ | 明示command時のみ |
| 他人のVote変更 | × | × | × | 原則× | × |
| Candidate status変更 | × | 提案のみ/設定 | ○ | ○ | 自動確定× |
| Schedule編集 | × | ×または限定 | ○ | ○ | 確認後applyのみ |
| token/role/削除 | × | 自分のみ | × | ○ | retention処理のみ |

既存のedit passwordなししおりは互換動作を保つが、新規LINE旅程には安全側のroleを既定にする。

### 28.3 外部URL resolver

MVP後の最初の対応対象はGoogle Maps共有URLだけに絞る。通常Web URLはリンクとして候補メモへ保存する前に人へ確認し、Instagram/TikTok等はURLを表示してWebで手入力させる。scrapingを前提にしない。

推奨pipeline:

1. 入力からURLを一件だけ抽出し、長さ・scheme・credential・portを検査する。Phase 3 ADRの開始値は最大2,048文字、HTTPS、port 443だけとし、実URL corpusで狭める/変更する。
2. HTTPSかつexact hostname allowlistに一致するGoogle Maps系だけを受ける。suffixの曖昧一致をしない。
3. 短縮URLは専用HTTP clientで展開する。各redirectでDNSを再解決し、IPv4/IPv6のloopback、private、link-local、multicast、reserved、cloud metadataを拒否する。redirectは開始値5回までとする。
4. 接続2秒、読取3秒、全体5秒、応答64KiBを開始上限とし、HTML/text等の必要Content-Type以外を拒否する。値はPhase 3 ADRと負荷/security testで確定し、proxy環境でも到達先IPを検証する。
5. HTML scrapingではなく、URLに含まれるPlace情報と、契約監査で許可されたGoogle Places API/UI Kitまたは代替providerを使って場所を解決する。現行Places API contentをnon-Google mapへ重ねてよいとは仮定しない。
6. 候補name/address/座標をpreviewし、人が「追加」を押して初めてWantToGoを作る。
7. Place ID一致は重複として既存候補を提示する。fallback一致は自動mergeしない。
8. 解決不能ならLLMで確定せず、WebのPlaces検索候補を返す。
9. URL原文やredirect chainを通常logへ残さず、domain、digest、result、costだけを短期記録する。

robots.txtとサイト利用規約を尊重し、許可APIがないサイトのcrawlをしない。LINE公式アカウントAPI利用規約は、Bot messageに運営者が実質管理しないページへのlinkを置くことを制限する文言があるため、Botは原則TabiSync管理ページだけへlinkし、外部Maps/予約linkはWeb上で表示する設計をLINEへ確認する。

Google Maps Platformについては、2026-08-14時点の固有規約14.2がPlaces API contentのnon-Google map併用を制限し、14.3が**緯度経度に限り**cacheを30日までとする一方、15.1はPlaces UI Kitにnon-Google map併用の例外を置く。Core Services SummaryはPlaces Library, Maps JavaScript API経由もPlaces APIとして列挙し、Maps JavaScript API policyはcache/storageを原則制限してplace_idを例外とし、Place Nameのsession外持続化がscrapingになり得ると説明する。したがって30日はname/address/rating等の包括的保存許可ではない。現在のPlacesServiceはUI Kitではない。契約、billing account地域、個別合意、field provenanceにより判断が変わり得るため、違反とも適合とも本書で断定しない。新規URL取込より前に、既存WantToGoのname/address/lat/lng/rating/place_idの取得元・保存期間・attributionをfield別に棚卸しする。

Google API keyは用途を分ける。browser側は許可originのHTTP referrer制限と必要APIだけ、server側は可能なら固定egress IP制限と必要APIだけを別key/project/quotaで与える。一つのbrowser keyをserver resolverへ流用せず、日次budget alert、key rotation、staging/production分離をPhase 0契約監査とPhase 3 ADRへ含める。

### 28.4 Rate Limitと費用guard

- Web: IPだけでなくParticipant/Itinerary/action単位を追加する。信頼proxy設定を本番確認。
- LINE inbound: source、senderがある場合user、command kind、channel全体。
- URL: 1 commandあたり1件、group/日、domain/分、同一digest cache。
- AI: Itinerary/Participant/group/channelの日次・月次、同時実行、token/tool/time。
- outbound: reply優先、push opt-in、group人数推定を原価へ、quota APIとbudget alert。
- 429/5xx: 指数backoffとjitter、retry可否をendpoint仕様に従う。replyを再試行しない。

## 29. プライバシー

### 29.1 原則

1. Botが受信できる情報と、TabiSyncが保存・AI処理する情報を分ける。
2. 本人が明示した旅行目的の入力だけを構造化する。
3. 一般会話、グループ名、画像、member一覧、profile画像をMVPで保存しない。
4. inviter一人の操作を、他の全memberの同意とみなさない。
5. LINE由来情報を広告、横断profile、二次学習へ使わない。
6. 外部AIへの委託可否、通知・同意、DPA、保持、再委託を確認するまでLINE文面を送らない。
7. 退出、unsend、連携解除、Participant削除、旅程削除、service終了の削除経路を持つ。
8. join/manage/claim等の能力URL pageには広告・第三者analyticsを載せず、高権限tokenをlocalStorageへ保存しない。既存秘密URL pageの第三者送信は別途監査する。

### 29.2 Data inventoryと暫定保持案

保持期間は法務・LINE確認前の設計案であり、承認値ではない。

| Data | MVPでの扱い | 暫定保持 / 削除trigger |
|---|---|---|
| raw Webhook body | 署名検証とparseにのみ使用、application log禁止 | memory内、request終了で破棄 |
| 対象外の一般message本文 | mention判定等の最小parse後、保存・AI送信しない | 即時破棄 |
| 明示command本文 | 可能なら直ちに構造化し、原文を残さない | 最大24時間未満を上限候補。unsend時即削除 |
| message ID対応 | unsend/editとjob取消のため | 必要最短。LINE/法務確認後に固定 |
| webhookEventId receipt | 冪等化のためpayloadなしで保持 | redeliveryの非公開期間を踏まえ運用値を決め、定期削除 |
| groupId/roomId | **書面許可まで永続保存しない** | PoCは24時間未満。許可後も退出/終了/解除で削除 |
| userId | 欠落可。本人連携を使う場合だけ | 目的中＋必要最短、unlink/退会で削除 |
| LINE display name / image / group name / group image | MVPでは取得・保存しない | なし |
| Web guest name | Itinerary内表示用、pseudonymous | 退出/削除/旅程retentionまで |
| 候補・Vote・Status | 明示操作で作られたTabiSync正本 | 旅程の保持方針まで。LINE由来の派生扱いを法務確認 |
| allergy等のConstraint | 任意、visibility明示、AI送信別同意 | 旅行終了後の短期削除を既定候補 |
| AI input/output | structured snapshotを最小化 | 現行logも含め保持期間を新設。削除要求を伝播 |
| Product/Audit event | 原文・token・生LINE IDを除外 | 集計目的の期限を定め、pseudonym rotation |
| URL import | domain/digest/result中心 | debugging/cost目的の短期保持 |
| 現行「最近のしおり」localStorage | 秘密UUID URL全体をclientに保持する現状を棚卸し。manage/edit/claim tokenは追加しない | 利便性、端末共有、XSSを評価し、最小情報/明示削除/期限へ移行 |
| 第三者広告・script request | 新規join/manage/claim pageでは送信しない。既存V2のAdSense/AMP/CDN/OGP/Refererをnetwork監査 | 同意・契約・必要性に基づき削減。request/URL/tokenが外部へ出ないことをrelease前確認 |
| Places由来field | provider/service/field provenance、取得時刻、end-user確認、attribution、保持条件をinventory化 | Google/法務判断まで新規拡大しない。許容期間/refresh/削除またはprovider移行をfield別に決定 |

### 29.3 Unsend、Edit、退出

- unsend: messageIdで未実行jobを取消し、原文を削除し、以後AI利用を止める。既に作った候補は自動削除か「確認待ち」へ戻すかを利用者へ説明し、選択可能にする。外部AIへ既送信のdataは回収不能であるため、送信前境界が重要。
- edit: 原文を保存しない設計では、既に構造化した候補との差分を自動確定せず、再確認を求める。
- leave: reply tokenはない。bindingをdisconnected、pending push/jobを停止し、規定対象のLINE dataを削除する。Itinerary自体はWeb productの選択に従う。
- Botが送ったmessageは削除・unsendできないため、manage/edit grantと個人情報を返信しない。groupへ必要なjoin grantは用途限定・期限付き・失効可能にし、転送可能性を表示する。

### 29.4 現行ポリシーの改定点

project_tabisync/templates/docs/privacy_policy.html は、個人を特定しない情報だけを収集し、個人情報は原則収集しない、匿名化してAI学習へ利用する場合があると説明する。新戦略と現行AI logを踏まえ、少なくとも次を正確にする必要がある。

- 運営主体と連絡先
- Web、LINE、guest、email、位置、投票、AIのdata分類
- 取得経路、必須/任意、目的、法的根拠/同意
- LINE Platform、OpenAI、Google等の委託/第三者、data所在地・保持
- 一般会話を処理しない境界
- AI model改善への利用有無。既定で二次学習しない方針を推奨
- 各dataの保持期間、backup、削除・開示・訂正・利用停止
- unsend、Bot退出、unlink、旅程削除
- 未成年、アレルギー等の機微情報
- cookie/analytics/広告と秘密URL非送信
- policy変更の通知方法。「予告なく変更」だけに依存しない

AI concierge termsの「外部AIへしおり情報が送信される」説明は土台になるが、LINE投稿の送信許可にはそのまま流用しない。LINEグループ参加時の短い通知、Web上の完全なnotice、AI実行直前の確認を組み合わせる。

### 29.5 Go/No-Go

- 社内tester限定、reply中心、非AI、短期状態PoC: **Go**
- 一般公開のgroupId永続binding: LINEの書面確認まで **No-Go**
- LINE由来文面の外部AI送信: LINE・法務確認まで保守的に **No-Go**。公式の一律禁止を確認したという意味ではない
- profile/member一覧の収集: 明確な必要性・同意・認証済要件が出るまで **No-Go**
- groupへ高権限tokenを出さないManager claim/recovery: 方式とE2Eが確定するまで **公開Bot No-Go**
- 現行Places由来data flowの拡大と新規URL取込: Google/法務による許容構成の決定まで **No-Go**

本節は法的助言ではない。日本法上の個人情報保護、通信の秘密、未成年、旅行情報の機微性も専門家確認を行う。

## 30. MVP

### 30.1 提示案の評価

依頼で示された17項目は、公開MVPの垂直sliceとして概ね適切である。ただし次を修正する。

- 「Django上でしおり作成」は、WebとBotで共通application serviceを使うことを要件にする。
- 公開MVPは日付未定draftをV2全体で正式対応する。Phase 0互換監査で成立しなければ、Bot質問だけを増やして進めずMVPを再承認する。
- 「LINEグループとしおりの関連付け」は、groupId長期保存の書面許可を前提条件にする。
- 「操作log」はraw message logではなく、receipt/audit/product eventに分ける。
- Webの候補追加、Vote、Status、未決定事項、guest participantをBotより先、または並行して成立させる。
- 閲覧/参加/編集権限とtoken失効をMVPへ追加する。
- 作成者の安全なManager claim/recoveryをMVPへ追加し、groupへmanage/edit tokenを返信しない。
- URL取込とAI幹事はMVPから外す判断を維持する。

### 30.2 二段階MVP

#### A. 社内技術PoC

目的は、価値検証ではなくAPI・運用・規約質問を具体化すること。

- 未認証のtest OA
- test groupだけ
- Allow bot to join group chats
- OA ManagerのGreeting/Auto-responseを無効化し、Chat modeを意図どおり固定
- join案内、構造化mention.isSelfまたはBot発行fallback、create/check/disconnect
- AIなし、外部URL解析なし、member一覧なし
- reply中心、pushは試験用に限定
- group contextは24時間未満
- raw body/一般messageを保存しない
- signature、events[]、userId/mention object欠落とpostback actionのintent-only fallback、redelivery、unsend、leave、2秒応答を検証

PoCを一般ユーザーへ拡大しない。

#### B. 公開Product MVP

LINE・法務のGo条件を満たした場合だけ公開する。

**含める**

1. Web/Bot共通の日付未定draft
2. Guest Participantとワンタップ参加
3. 参加者別4段階Vote
4. Candidate Statusと未決定一覧
5. proposer
6. 閲覧/参加/編集/管理の権限とtoken lifecycle
7. private Manager claim/recovery。方式未確定なら公開No-Go
8. server-side product event
9. Bot join案内
10. 構造化mentionまたは安全なfallbackによる作成/確認
11. 条件付き1 group 1 active itinerary
12. 用途限定・期限/失効付きjoin grantのreply
13. signature、event receipt、queue、idempotency
14. edit/unsend/leaveの最低限処理
15. audit、retention、privacy notice、削除
16. group/user/channel/API/AI原価のrate/budget guard。MVPではAIを無効

**含めない**

- Google Maps URL取込
- AI幹事、複数Plan
- push reminderの既定ON
- 全member列挙
- 全参加者へのLINE Login、LIFF、Mini App強制。Manager identityで他方式が成立しない場合の最小LINE LoginはPhase 0で再判断
- 複数active itinerary
- 予約、費用、公開しおり、V2 offline
- 一般会話全文

### 30.3 MVPの完了体験

1. testではない実在groupがBotを招待する。
2. privacy案内を見て、構造化mentionまたはBotが発行した安全なfallbackから一件のdraftを作る。
3. Botは、閲覧・参加だけを許す用途限定・期限付き・失効可能なbearer join grant URLをgroupへ返信し、edit/manage grantは返信しない。
4. 作成者がprivate claimでManagerになり、端末喪失時の復旧経路を確認する。
5. 転送されたjoin URLの所持者も参加でき、MVPではLINE group membershipを証明しないことを案内した上で、2人以上がWeb Participantになる。
6. 候補を一件以上作り、2人以上がVoteする。
7. 候補をdecided/rejectedのどちらかへ進める。
8. Botへ「しおりを確認」で同じactive itineraryを返せる。
9. 退出/削除/失効が安全に動く。

Botがcreate linkを返すだけではMVPの価値検証を完了したとみなさない。

### 30.4 暫定成功基準

最初の5〜10組は統計的判定ではなく問題発見用とする。その上で次を暫定gateにする。

- 観察対象5〜10組のうち80%以上が補助なし、または一度の説明でBotを招待できる。分子/分母と区間を併記する。
- 招待したgroupの60%以上がdraft作成を完了する。分母が5組未満ならgate判定せず追加検証する。
- 作成したgroupの半数以上で、24時間以内に2人目がjoinし、候補追加またはVoteを行う。
- 参加した人の過半数が最低一件Voteする。
- 重大なprivacy誤解、誤返信、cross-group漏えい、二重作成が0件。
- 5組以上の面談で、幹事が「整理/催促/決定のどれが減ったか」を具体例で説明できる。

値はbaseline取得後に更新し、達成するためにtest participantや同一人物を水増ししない。

## 31. 段階的ロードマップ

### Phase 0: 調査・計測・ユーザー検証

- **仮説**: H1aとしてLINEで候補が散らかるgroupがBot招待・draft開始を受け入れるかを先に測り、H1bとして実際のjoin/voteが可能な環境で24時間以内の2人目の意味ある操作を測る。
- **対象ユーザー**: 候補URLが既に3件以上ある2〜6人の実在group 5〜10組、現行利用者、幹事。
- **成果物**: 現行funnel baseline、event taxonomy、interview、招待/作成理解を測るclickable prototype、実URLでjoin/voteできる安全なWizard-of-Ozまたは限定build、LINE社内PoC、LINE/Google data inventoryと公式照会、日付未定draftの全V2互換inventory、Manager claim実機比較とADR/復旧E2E案、H0a〜H0d decision record、threat model、MVP decision。
- **技術的依存関係**: test OA、HTTPS staging、秘密を含まないtest data、簡易event instrumentation案。
- **完了条件**: 5〜10組でH1aの招待/開始taskを観察する。H1bは実操作可能なWizard-of-Oz/限定buildを使えたgroupだけで予備値を記録し、clickable prototypeのclickを「2人目参加」と数えない。draftは全V2 date依存をinventory化してGoまたはMVP再承認、Managerは1対1 reply/限定Loginの実機結果・ADR・復旧E2EとGo/No-Goを残す。section 17.4の各回答/未解決判定、Google Places + non-Google map/field別保存の継続・移行判断も必要。
- **検証方法**: H1aはtask-based prototype usability、H1bはtokenized実URLの行動event + group diary/interview、ほかにPoC logs、policy/legal review。
- **KPI**: H1aの招待/開始意向・task完了・所要時間、H1bの実join/操作、mention/fallback成功、privacy理解、技術error。各値に分子/分母と検証方式を付ける。
- **次Phase基準**: Phase 1へは、対象5〜10組の60%以上が招待/開始taskを完了し、重大なprivacy拒否がなく、draftがGoであること（またはMVP再承認）を求める。H1bは予備signalとしPhase 1で正式gateにする。Phase 2公開にはH0aのgroup binding/縮退とH0c Managerが別途Go、Phase 4にはH0d外部AIがGoであることを求める。H0b GoogleがNo-Goなら、影響する現行data flowをfeature拡大前に是正する。

### Phase 1: グループ意思決定MVP

- **仮説**: account不要のParticipant、Vote、Status、未決定一覧で、LINEだけより候補決定が進む。
- **対象ユーザー**: Web直作成と将来LINE groupの双方、2〜6人。
- **成果物**: 日付未定draft、Guest Participant、join grant、Vote、Status/history、未決定、proposer、Web-first Manager/role/token、event、privacy UI。
- **技術的依存関係**: schema/migration、access control、server event、既存V2 compatibility。
- **完了条件**: 権限matrix、cross-itinerary、concurrency、token lifecycle、mobile browser testsを通し、既存URL/データに回帰がない。
- **検証方法**: 20件程度のeligible itineraryでWeb funnelと面談。小標本は区間も併記。
- **KPI**: join完了率、2人以上操作率、Vote回答率、status更新率、未決定減少、time-to-first-decision。
- **次Phase基準**: H1bの正式gateとして作成groupの半数以上で24時間以内に2人目がjoin + add/voteし、7日共同参加率40%以上、参加者の過半数がVote、重大な権限事故0。未達ならLINEを拡大せずWeb摩擦を直す。

### Phase 2: LINE Bot MVP

- **仮説**: LINE入口はWeb直共有よりcreateと2人目参加を増やす。
- **対象ユーザー**: Phase 1適合groupのうち、LINEで相談中のgroup。
- **成果物**: join/mention/fallback/create/check/disconnect、private Manager claim、条件付きbinding、Webhook core、queue/outbox、reply、edit/unsend/leave、quota/audit。
- **技術的依存関係**: H0aのgroup bindingまたは受容可能な縮退、H0c Manager Go、Phase 1 application service、worker、secret/monitoring、本番proxyとOA Response settings確認。H0d外部AI GoはAI無効のPhase 2には不要。
- **完了条件**: signature/idempotency/2秒応答、userId/mention object欠落、postback actionのintent-only fallback、複数event、redelivery、Manager claim/recovery、退出、誤送信、quotaのE2Eとrunbook。
- **検証方法**: Web直作成とのcohort比較、10〜30 groupの限定beta、support transcript。
- **KPI**: invite→create、command trigger種別ごとの成功、reply latency、link open、2人目join、共同参加率、leave率、paid messages/trip、Webhook error。
- **次Phase基準**: invite→create 60%以上、valid command trigger success 95%以上、p99 Webhook受付2秒未満、重大incident 0、LINE cohortの共同参加がWeb baselineを改善。値はbeta前にbaselineで再設定。

Phase 1とPhase 2は完全な直列にしない。Phase 0中にWebhook技術spikeと共通application service設計を並行する。ただし、公開Botが書き込むdomainはParticipant/Vote/Statusと権限が安定してから接続する。

### Phase 3: 候補収集

- **仮説**: Google Maps URLからのpreview/confirmが、候補追加者数を増やし転記時間を減らす。
- **対象ユーザー**: Maps URLをLINEへ送り合うgroup。
- **成果物**: SSRF-safe resolver、Google allowlist、Place resolution、preview/confirm、dedupe、failure UX、cost dashboard。
- **技術的依存関係**: Phase 2 queue、H0bのGoogle Maps Platform契約Goまたは許可された代替provider、請求、URL corpus、M8 retention。
- **完了条件**: security corpus、redirect/DNS test、API規約review、manual fallback、原価limit。
- **検証方法**: 実際の匿名化URL形式corpus、解決成功/修正/重複、task time比較。
- **KPI**: supported URL解決率、確認後正答率、候補追加完了率、median追加時間、重複回避、1候補API費用。
- **次Phase基準**: 対応Maps URLの80%以上をpreviewまで解決し、人の確認後の正答95%以上、重大SSRF 0、原価budget内。閾値はcorpus分類後に再調整。

### Phase 4: AI幹事

- **仮説**: 参加者別希望・制約から理由付き2〜3案を出すと、単一AI案より採用と納得が増える。
- **対象ユーザー**: 候補5件以上、2人以上Vote、日程/主要constraint入力済みのgroup。
- **成果物**: PlanVariant、decision tools、snapshot/version、外部事実、2〜3案、理由/不採用/未確認、compare/adopt。
- **技術的依存関係**: H0dのLINE/法務による外部AI Go、Phase 1 data、Phase 3 facts、AI eval、cost guard。
- **完了条件**: curated evalでhard constraint違反0、schema/権限/confirm、model failure fallback、既存concierge回帰なし。
- **検証方法**: 人手作成/単一案とのblind評価、adoption、修正量、理由の根拠監査。
- **KPI**: eligible groupの実行率、比較完了、全部/一部採用、採用までの時間、修正項目、constraint違反、AI費用/trip。
- **次Phase基準**: 重大誤情報/自動確定0、提案groupの30%以上で一部以上採用、幹事負担の定性改善、費用上限内。小標本後に再設定。

### Phase 5: 継続利用と収益化

- **仮説**: 意思決定で価値を得たgroupは、次旅行、template、旅行後記録、限定有料AIへ戻る。
- **対象ユーザー**: 旅行完了group、2回目作成者、AI高利用group。
- **成果物**: archive/current切替、clone/templateを優先し、公開、予約、費用、affiliate、有料AIは個別business caseで選ぶ。
- **技術的依存関係**: ownership/retention、billing/legal、affiliate disclosure、support。
- **完了条件**: 各機能にWTP、unit economics、privacy/security review、rollback flagがある。
- **検証方法**: fake-door、price interview、cohort、small paid pilot。
- **KPI**: 90/180日2回目作成、template利用、paid conversion、gross margin、support/incident、core共同参加率。
- **次Phase基準**: 2回目作成とWTPが観測され、収益機能がcore体験を悪化させず、外部依存原価を上回る。

## 32. KPI

### 32.1 North Star

**7日以内の意味ある共同参加率**

分子:

- 作成から7日以内に、異なる2人以上の有効Participantが、
- 候補追加、Vote、Candidate Status提案/変更、Schedule編集のいずれかを行った、
- eligible itineraryの件数。

分母:

- 同期間に作成されたeligible itinerary。
- test、staff、spam、bot retry duplicate、即時削除、migration生成を除く。

同一cookieだけでなく、optional LINE link/account、network/behavior anomalyを不正検知に使うが、強い本人証明がないguest cohortは別表示する。Organizer一人が二つのguestを作って水増しできる限界を注記する。

この指標は戦略に適する。作成数やBot利用ではなく「2人目が意思決定に参加したか」を測るためである。ただし、旅行が実際に決まったかは補助outcomeで監視する。

### 32.2 Funnel

| 段階 | KPI | 定義上の注意 |
|---|---|---|
| Awareness | LINE訴求LP到達、invite CTA click | 現ホームはGA対象外。秘密URLと分離 |
| Invite | Bot group招待率 | join webhook / invite CTA unique。直接招待は分母不明として別 |
| Activation | join→valid command trigger、trigger→draft作成 | mentionとpostback intent fallbackを分け、重複event除外。userId欠落を自動的な失敗にしない |
| Handoff | Bot返信link open率 | token原文をanalyticsへ送らず、redirect eventで測る |
| Join | unique Participant数、open→join率 | guest再作成を別計測 |
| Contribute | 参加者操作率、候補追加者数 | viewを意味ある操作に含めない |
| Vote | Vote付き候補率、参加者回答率 | neutralと未回答を分ける |
| Decide | 候補→decided/rejected、未決定減少 | status変更だけの水増しを防ぐ |
| Schedule | decided候補→Schedule採用率 | planned_dayだけを採用としない |
| AI | eligible実行、compare、全部/一部採用 | 起動率だけを成功にしない |
| Retain | 90/180日2回目旅行作成 | 同group/同Participantの定義をPrivacyと整合 |

### 32.3 必須KPI一覧

- しおり作成数
- LINE経由作成率
- invite CTA→join webhook率
- Bot参加→しおり作成完了率
- valid mention処理成功率
- 共有link open率
- 1しおりあたりParticipant数
- openしたParticipantの意味ある操作率
- 2人以上操作したしおり率
- 複数人が候補追加した率
- Vote付き候補率と回答者率
- 候補からSchedule採用率
- 旅程確定率
- AI実行率、比較率、全部/一部採用率
- 2回目旅行作成率
- Bot group退出率
- LINE reply/push通数、AI/Places費用、総変動費 / trip

### 32.4 品質・Guardrail

- Webhook p50/p95/p99、署名失敗、duplicate、queue lag、dead-letter
- cross-group/cross-itinerary access incident
- token失効までの時間、漏えい報告
- unsend/delete完了時間
- 一般message保存件数。目標0
- 外部AIへ非同意LINE文面を送った件数。目標0
- AI hard constraint違反、誤った事実、確認なし適用。重大件数0
- push opt-out、leave、block、苦情
- guest duplicate推定率
- 月間LINE/AI/Places budget消費率

### 32.5 Event例

itinerary_created、share_link_issued、line_join_received、line_mention_valid、line_command_completed、join_link_opened、participant_joined、candidate_created、vote_upserted、candidate_status_changed、decision_issue_resolved、variant_generated、variant_adopted、schedule_item_created_from_candidate、line_left、token_revoked。

propertiesはallowlistにし、title、message text、URL、token、display name、group/user ID、addressを入れない。

## 33. 技術的リスク

| リスク | 影響 | 対策 / Trigger |
|---|---|---|
| groupId長期保存が規約不可 | 中核の自動binding不可 | Phase 0書面回答。No-Goなら短期context + code指定またはWeb-first |
| LINE文面の外部AI委託不可 | Bot内AI不可 | Webで改めて同意入力、または非AI organizer。書面/法務 |
| reply 1分、Webhook 2秒 | timeout・無応答 | 受付分離、reply即応、queue/outbox、限定push |
| duplicate/逆順/欠落 | 二重作成・誤状態 | event unique、version、idempotent service、reconciliation |
| queue新設と運用負担 | 障害点増加 | DB queueとbroker比較、runbook/metrics、small PoC |
| Python 3.8基準 | SDK/security update制約 | LINE開発前にupgrade impact調査を別Issue化 |
| 日付未定がV2前提を破る | runtime error/UI欠落 | 全total_days経路監査、正式lifecycle、feature flag |
| token/role追加の互換 | 既存URL利用者をlock out | additive model、旧path test、rollback、段階移行 |
| planned_dayとSchedule二重表現 | 決定と旅程の不整合 | 責務定義、adoption service、整合check |
| concurrent editor | last-write-wins、Vote消失 | row model、unique/upsert、optimistic version |
| SSRF/DNS rebinding | 内部network侵害 | exact allowlist、各redirect解決、IP block、egress control |
| Google URL/API変更・費用 | 取込停止・赤字 | resolver adapter、fallback、cache/limit、billing alert |
| 現行Places dataをnon-Google mapへ表示・長期保存 | 契約不適合、既存data/地図の移行 | Phase 0でGoogle/法務、Service Specific Terms 14/15、attribution、field provenance、30日cacheを監査。違反を断定せず安全なprovider構成へ |
| AI hallucination/cost | 誤旅程・費用 | structured schema、rule recheck、human apply、budget |
| analytics/広告/第三者JSへのtoken leak | 秘密URL・DOM流出 | join/manage/claimは第三者scriptなし、first-party event、CSP、route template、Referrer/OGP/network review |
| localStorageの秘密URL | 共有端末・XSS・端末紛失で再利用 | manage token禁止、recent itinerary最小化/期限/消去、XSS対策 |
| Nginx/Cloudflare本番未確認 | Webhook失敗・header偽装 | staging/prod checklist、origin restriction、trusted CIDR |
| Bot message取消不可 | join grant等の転送・残存 | manage/editは非送信、joinは用途限定/期限/失効、controlled template |
| member/userId/mention object欠落 | command/Manager照合失敗 | Web guestを正本、postbackはintent fallbackのみ、Managerは別本人照合。文字列mentionを信用しない |
| Manager claimが未解決 | 高権限漏えい、管理者不在 | Phase 0 ADR/実機、private claim、recovery。未解決ならBot作成No-Go |

## 34. プロダクト上のリスク

| リスク | 兆候 | 対応 |
|---|---|---|
| Bot招待が気持ち悪い/面倒 | invite CTAは押すがjoinしない | Web-only導線を残す、案内と処理範囲を短く明示 |
| グループに他OAがいる | 招待時自動退出 | 1 OA制約を事前案内。BotなしWebへfallback |
| 2人旅行に投票が重い | join後Voteしない | 2人はreaction中心、3人以上は集計を強める |
| 状態管理が仕事になる | status未更新、LINEに戻る | defaultを少なくし、未決定を自動派生 |
| 投票が多数決圧力になる | passを付けづらい | secret ballot/表示範囲をCouldで検証、hard constraint分離 |
| 幹事権限が強すぎる | 他人の意見が反映されない | Vote不変、履歴、採用理由、role透明性 |
| 直接競合が追随/先行 | MapMemo/タビノワ/Limboの機能拡張 | end-to-end共同参加とSchedule反映で学習速度を上げる |
| LINE依存が大きい | 規約/価格/障害 | Webを正本にし、Botなしで継続可能 |
| 通知疲れ | leave/block/opt-out上昇 | reply優先、push opt-in、頻度上限 |
| AIが価値より話題性 | 実行するが採用しない | 採用/修正/未決定減少をgate、Phase 4まで待つ |
| 若年層の支払意欲が低い | 高利用だがpaid conversionなし | B2C課金を急がず、affiliateも透明性/利益を検証 |
| 旅行頻度が低い | 2回目作成が少ない | group reuse/テンプレートをデータ後に。MAUを唯一KPIにしない |
| 小標本を過信 | 5〜10組の偶然 | 定性発見→20〜30組beta→cohort比較へ段階化 |
| Privacy説明が難しい | 「全部読まれる」と誤解 | mentionのみ、Web正本、一般会話0保存を製品UIで証明 |

## 35. 検証すべき仮説

優先順。

| ID | 仮説 | 検証 | 支持signal | 反証 / 判断 |
|---|---|---|---|---|
| H0a | groupId/roomId bindingは規約上許容条件を満たせる | LINE書面照会、法務 | 識別子、保持、利用時点、削除条件が明文化 | 不可/回答不能なら永続bindingをNo-Go、短期contextを別評価 |
| H0b | 現行Places由来dataの保存・non-Google map表示を含め、許容される場所provider構成を確立できる | Google/法務、契約・field provenance監査 | 継続または移行構成、retention、attributionが明文化 | 判断不能なら該当data flowの拡大をNo-Go |
| H0c | 作成command senderが高権限tokenをgroupへ出さずManagerになり、復旧できる | 1対1 reply claim/Manager限定Loginの実機・threat test | Bot作成を維持する本人照合方式と復旧が成立 | Web-firstしか成立しない場合はBot作成成功と数えずMVP再承認。先着claim/group配布だけならNo-Go |
| H0d | LINE由来文面の外部AI委託は通知・同意・委託先条件を満たせる | LINE書面照会、法務、DPA/再委託/保持review | 許可scopeとflow-downが明文化 | 不可/回答不能ならPhase 4のLINE文面AIをNo-Go。非AI organizerは継続 |
| **H1a** | LINEで候補が散らかる実在groupはBot招待とdraft開始を受け入れる | 5〜10組のtask-based prototype | 60%以上が招待/開始task完了、重大privacy拒否なし | 招待拒否/理解不能なら入口・targetを見直す |
| **H1b** | 利用可能なguest Webでは24時間以内に2人目が意味ある操作をする | Wizard-of-Oz/限定buildの実URL event。clickable prototypeは不可 | 作成groupの半数以上で2人目がjoin + add/vote | OrganizerだけならWeb参加摩擦/共同価値を見直す |
| H2 | 4段階Voteと未決定一覧は幹事の整理・催促を減らす | Web MVP、diary/interview | 未決定減少、同じ確認の再投稿減、具体的負担減 | Voteは付くが決定しないならstatus/質問設計を変更 |
| H3 | accountなしguestは登録必須より共同参加を増やす | funnel比較、task test | open→join、join→voteが高い | duplicate/なりすましが価値を上回るならoptional Loginを前倒し |
| H4 | LINE入口はWeb shareだけより2人目参加を増やす | comparable cohort | 共同参加率の実質的改善 | createだけ増え共同参加不変ならBot投資を縮小 |
| H5 | Maps URL取込は候補追加者数を増やす | Phase 3 A/B/task | median追加時間低下、複数提案者増 | 解決失敗/誤Place/費用が高ければWeb検索を維持 |
| H6 | 理由付き複数AI案は単一案より採用される | blind比較 | 一部以上採用、修正量低下、納得度向上 | 類似案/誤情報ならAIを要約・質問に縮退 |
| H7 | 初期targetは大学生より「候補URL 3件以上・未決定」で切る方が強い | segment別cohort | problem-based cohortのactivationが高い | 年齢/旅行型で強い差が出ればtargetを再定義 |
| H8 | 旅行後に再作成または有料価値がある | 90/180日cohort、fake door | 再作成、template demand、WTP | 低ければsession productとしてunit economicsを設計 |

**最初に検証するproduct仮説はH1a、その直後がH1b**である。H0a〜H0dはPhase別の実施可否gateであり、利用価値の第一仮説とは分ける。H1aまたはH1bが反証された状態で、URL resolverやAI幹事を実装しない。

## 36. 未確認事項

### 36.1 Product / User

- 現在のしおり作成数、共有率、複数人利用、再訪、旅行完了
- 現行利用者が実際にLINEで相談している割合
- 日付必須、password、候補追加、編集の実離脱
- 2〜6人、大学生/若年層、日帰り〜2泊のどのsegmentが最も痛みを持つか
- Bot招待、guest名、投票公開範囲、AI利用への受容
- 幹事が削減したいのが候補転記、催促、日程化、予約のどれか
- 強い本人性が必要な被害/不安の頻度
- willingness to pay、支払者、旅行頻度

### 36.2 LINE / Legal

- groupId/roomId、encrypted/HMAC derived value、bindingの24時間超保存可否
- グループ情報の「ユーザーがサービスを操作する際のみ利用」の具体的範囲
- LINE文面をOpenAI等へ送る業務委託の許容条件とOA API規約との整合
- inviter/command senderの同意で扱える範囲、他memberへのnotice
- 退出、unsend、旅行終了時に削除すべき派生data
- 外部Maps/予約URLをBot messageへ含める可否
- 日本の認証済OAでmember IDs APIが利用可能か
- 友だち追加前後のグループ招待UX、他OA参加時の実挙動
- group command senderを1対1で照合してManager claimを渡せる友だち/userId/push条件と、欠落時のWeb-first/Manager限定Login fallback
- mention object欠落時のBot発行postback action導線（intent限定、identity不可）、Greeting/Auto-response/Chat modeの実設定と監視
- 審査、アカウント名/カテゴリ、商用利用条件
- 2026-10-01以後の追加message料金

### 36.3 Infrastructure / Operation

- 本番Nginx、Cloudflare WAF、origin直アクセス遮断、body/timeout/header
- 実際のTRUSTED_PROXY_CIDRS、HTTPS、secret rotation
- PostgreSQL backup/restore、retention、incident response
- worker/brokerの運用選択とPython upgrade時期
- monitoring、alert、on-call、LINE API outage runbook
- Google Maps Platformの契約主体/billing地域/個別合意、Places API contentのnon-Google map併用、field別cache/保存、30日経過data、attribution、Place ID/end-user確認dataの扱い
- 現行WantToGo各fieldのprovider provenanceと取得日。許容されるGoogle map/Places UI Kit/別provider移行案
- browser用HTTP-referrer制限keyとserver用IP制限keyの分離、quota/billing alert、Phase 3 resolver上限値の実URL corpus適合
- OpenAI DPA/retention/data residency/model training設定
- GA4/Search Consoleの実dataと秘密URLへの設定
- V2のAdSense/AMP広告/第三者CDNが秘密URL・DOM・Refererを実際にどこへ送るか、CSP適用可否
- `tabisync_recent_itineraries` 等localStorageの実利用率、共有端末/XSS risk、URL最小化・期限・消去UX
- LINE内ブラウザのiOS/Android/PC実機互換

### 36.4 Repository

- create/Edit passwordでTurnstile表示とserver検証が不一致な意図
- 現行productionでAgent feature flagをどのItineraryへ有効化しているか
- ConciergeChatLog等の実保持期間と削除運用
- READMEの公開しおりplatform構想を新戦略でどう扱うか
- docs/taskと実装のsource of truthをどう更新するか
- design.mdの新design適用範囲
- V1利用量と廃止予定。今回は変更しない

### 36.5 Competitor

- TravelCanvas、タビノワ、MapMemo、旅のしおりの利用者規模、継続運営、実機品質
- Limboの日本市場利用、Android/Web作成対応、投票ルールの実運用
- Google Maps絵文字投票の日本の全client/共有設定での挙動
- AVA/Funliday/tabioriのguest・投票・候補stateの最新実機仕様
- LINE Official Account directory、App Store、国内startupを対象にした追加探索
- 各社の価格・無料枠・AI/LINE機能の更新

公開検索で同じ組合せを確認できなかったことは、市場に存在しない証明ではない。Phase 0で実機accountを作る範囲と、利用者への「現在どうやっているか」調査を追加する。

## 37. 次に作成すべきIssue

以下は推奨する分割案であり、Issue自体は作成していない。概ね依存順だが、調査・法務・inventoryは並行できる。

| 順 | Issue案 | 主な成果 / 完了条件 | 依存 |
|---:|---|---|---|
| 1 | **research: 5〜10組のLINE旅行groupでH1a/H1bを分けて検証する** | prototypeは招待/開始、実URLはjoin/voteを計測し、分母と限界を明記 | なし |
| 2 | **legal: LINE groupId/roomId保持を公式照会する** | 質問票、書面回答、識別子・利用時点・retention・縮退のdecision record | なし |
| 3 | **legal/security: 現行Google Places→MapLibre data flowを契約・field単位で監査する** | terms/契約、provenance、retention、attribution、key分離、継続/移行ADR | なし |
| 4 | **domain: 日付未定draftの全V2依存をinventory化する** | total_days前提、lifecycle案、compat/rollback、GoまたはMVP再承認 | なし。Phase 0で先行 |
| 5 | **analytics: Token-safe product event taxonomyを設計する** | event dictionary、PII allowlist、North Star query、retention、QA plan | 1と並行 |
| 6 | **architecture: Participant・role・guest identityのADRを作る** | identity lifecycle、cookie、multi-device、delete/merge、権限表 | 1、5 |
| 7 | **security: view/join/edit/manage token lifecycleのADRを作る** | bearer制約、旧URL互換、hash、expiry/revoke/rotate、広告/Referer/localStorage対策 | 6 |
| 8 | **security: Manager private claim/recoveryを実機検証しADR化する** | 1対1 reply/限定LoginをBot作成案として比較し、Web-firstはpivot扱い。userId欠落、recovery、No-Go条件 | 2、6、7。12と並行 |
| 9 | **domain: Vote・Candidate Status・未決定・proposerのschema/APIを設計する** | enum、unique、history、state transition、concurrency、DoD | 6 |
| 10 | **domain: 候補→Schedule採用規則を設計する** | planned_day/day_index責務、adopt/undo/idempotency、compat | 4、9 |
| 11 | **prototype: Web group decision MVPをuser testする** | clickableは理解、limited buildは実行動を測る。実装承認後のみcode Issueへ分割 | 4、6〜10 |
| 12 | **spike: LINE Webhook・Response settings・欠落mentionを検証する** | test OA、署名、fallback、redelivery/unsend、2秒SLO、raw logなし | 2 |
| 13 | **architecture: Queue、transactional outbox、retry/runbookを選定する** | ADR、failure matrix、deploy/monitoring、Python compatibility | 12 |
| 14 | **privacy: LINE/guest向けdata inventoryとPolicy改定案を作る** | notice、consent、retention、delete/unsend/leave、第三者script checklist | 2、6、12 |
| 15 | **security: LINE Bot threat modelとabuse/cost limitsを定義する** | STRIDE等、rate/quota、secret rotation、incident runbook | 8、12〜14 |
| 16 | **beta: LINE create/check/disconnectの限定MVPを設計する** | state machine、join grant、Manager claim、copy、E2E、feature flag、rollback | H0a/H0cがGo、9〜15 |
| 17 | **security: Google Maps URL resolver threat modelとcorpusを作る** | allowlist、SSRF、数値上限ADR、分離key、許可provider、preview/confirm | 3がGo、Phase 2検証後 |
| 18 | **legal/privacy: LINE由来文面の外部AI委託条件を確認する** | User Data Policy 3.4.2、同意/目的、DPA、再委託、保持、flow-down、H0d decision | 14または先行質問票 |
| 19 | **domain: PlanVariantとAI幹事evaluation仕様を作る** | input schema、objective、hard rules、explanation、adopt、offline eval | Phase 1 data、18がGo |
| 20 | **ops: LINE/AI/Places unit economics dashboardを設計する** | trip別原価、quota alerts、budget shutdown | 5、13 |
| 21 | **docs: README/design/task文書と承認戦略を整合させる** | 陳腐化箇所を更新しsource of truthを明記 | 戦略承認後 |
| 22 | **tech debt: Python runtimeとdependency upgrade影響を調査する** | supported version、Django/LINE SDK/worker compatibility、移行plan | LINE実装前 |

実装Issueは、1〜5の結果と戦略承認前に作らない。特に16、17、19を同時に開始しない。

## 38. 参考情報

### 38.1 Repository evidence

主要な根拠。行番号は対象commitで変わりうるため、class/function名を優先する。

- AGENTS.md
- README.md
- design.md
- project_tabisync/project_tabisync/settings.py
- project_tabisync/tabisync/middleware.py
- project_tabisync/tabisync/models.py
  - Itinerary、ScheduleV2、WantToGo、MemoV2、ChecklistV2
  - ConciergeChatLog、ConciergeToolCallLog
- project_tabisync/tabisync/urls.py
- project_tabisync/tabisync/views/itinerary_v2.py
  - CreateView、ItineraryDetailV2View、EditContentFormV2View
- project_tabisync/tabisync/views/access_control.py
  - has_view_access、has_edit_access、ViewPasswordRequiredMixin、EditPasswordRequiredMixin
- project_tabisync/tabisync/views/want_to_go.py
  - WantToGoMapView、WantToGoV2View
- project_tabisync/tabisync/views/schedule_v2.py
  - ScheduleV2EditView、schedule_v2_row_save/delete
- project_tabisync/tabisync/views/memo_v2.py、checklist_v2.py
- project_tabisync/tabisync/views/concierge.py
  - ConciergeV2View、concierge_v2_apply_changes
- project_tabisync/tabisync/concierge_agent/
  - agent.py、registry.py、usage.py、skills/、tools/
- project_tabisync/tabisync/concierge_tools/
  - read_tools.py、proposal_tools.py、edit_actions.py、ui_tools.py
- project_tabisync/tabisync/views/utils.py
  - input limits、Turnstile、trusted proxy client IP、JSON parser
- project_tabisync/templates/tabisync/content/
  - base.html、content.html、want_list.html、concierge_v2.html、memo_v2.html、list_v2.html
- project_tabisync/static/js/map_renderer.js
- project_tabisync/static/sw.js
- project_tabisync/tabisync/tests/
- docs/task/task-001〜009、docs/fix/
- Pipfile、Pipfile.lock、package.json
- containers/django/Dockerfile、entrypoint.sh
- docker-compose.yml、docker-compose-staging.yml
- .github/workflows/deploy.yml

### 38.2 LINE official sources

すべて2026-08-14確認。

- [Group chats and multi-person chats](https://developers.line.biz/en/docs/messaging-api/group-chats/)
- [Build a bot / Response settings](https://developers.line.biz/en/docs/messaging-api/building-bot/)
- [Receive messages (webhook)](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)
- [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/)
- [LINE Developers FAQ](https://developers.line.biz/en/faq/)
- [Verify webhook signature](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/)
- [Retry failed API requests](https://developers.line.biz/en/docs/messaging-api/retrying-api-request/)
- [Check webhook error causes and statistics](https://developers.line.biz/en/docs/messaging-api/check-webhook-error-statistics/)
- [Sending messages](https://developers.line.biz/en/docs/messaging-api/sending-messages/)
- [Getting user IDs](https://developers.line.biz/en/docs/messaging-api/getting-user-ids/)
- [Consent on getting user profile information](https://developers.line.biz/en/docs/messaging-api/user-consent/)
- [Messaging API pricing](https://developers.line.biz/en/docs/messaging-api/pricing/)
- [2026-10-01追加メッセージ料金改定予定](https://www.lycbiz.com/jp/news/line-official-account/20260216/)
- [日本のLINE公式アカウント種別](https://www.lycbiz.com/jp/service/line-official-account/account-type/)
- [2026-04-01プレミアムアカウント統合告知](https://www.lycbiz.com/jp/news/line-official-account/20260107/)
- [How to link user IDs on the LINE Platform](https://developers.line.biz/en/tips/2026/04/09/user-id-linking/)
- [User account linking](https://developers.line.biz/en/docs/messaging-api/linking-accounts/)
- [LINE Login overview](https://developers.line.biz/en/docs/line-login/overview)
- [Using user data in LIFF apps and servers](https://developers.line.biz/en/docs/liff/using-user-profile/)
- [LIFF development guidelines](https://developers.line.biz/en/docs/liff/development-guidelines/)
- [Introducing LINE MINI App](https://developers.line.biz/en/docs/line-mini-app/discover/introduction/)
- [LINEユーザーデータポリシー](https://terms2.line.me/LINE_Developers_user_data_policy?lang=ja)
- [LINE Developers Agreement](https://terms.line.me/LINE_Developers_Agreement)
- [LINE公式アカウントAPI利用規約](https://terms2.line.me/official_account_api_terms_jp?lang=ja)
- [Terms and policies index](https://developers.line.biz/en/terms-and-policies)

### 38.3 Google Maps Platform official sources

すべて2026-08-14確認。本書は契約違反を断定せず、実際の契約主体、billing地域、個別合意、利用serviceとdata provenanceをGoogle/法務へ確認する。

- [Google Maps Platform Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms)
- [Google Maps Platform Core Services Summary](https://cloud.google.com/maps-platform/terms/maps-services)
- [Maps JavaScript API policies and attributions](https://developers.google.com/maps/documentation/javascript/policies)
- [Places Library, Maps JavaScript API (Legacy)](https://developers.google.com/maps/documentation/javascript/legacy/places)
- [Google Maps Platform pricing overview](https://developers.google.com/maps/billing-and-pricing/pricing)

### 38.4 Competitor official / operator sources

すべて2026-08-14確認。比較結果は第9節に記載。各社・運営者の公開説明であり、特記しない限りhands-on、現行稼働、利用規模を検証したものではない。

- tabiori: [FAQ](https://tabiori.com/faq/)、[App Store](https://apps.apple.com/jp/app/tabiori-%E5%85%B1%E6%9C%89%E3%81%A7%E3%81%8D%E3%82%8B%E6%97%85%E3%81%AE%E3%81%97%E3%81%8A%E3%82%8A/id1193502519)
- Wanderlog: [Pro](https://wanderlog.com/pro)、[共同編集](https://help.wanderlog.com/hc/en-us/articles/4625495771163-Add-friends-to-plan-together)、[AI](https://wanderlog.com/trip-plan-assistant)、[route optimization](https://help.wanderlog.com/hc/en-us/articles/13545624787867-Optimize-route)、[offline](https://help.wanderlog.com/hc/en-us/articles/13545182856859-Download-trip-plan-for-offline-access)、[予約mail取込](https://help.wanderlog.com/hc/en-us/articles/4625693334811-Add-flight-hotel-and-rental-car-details-by-forwarding-an-email)
- NAVITIME Travel: [App Store](https://apps.apple.com/jp/app/%E6%97%85%E3%81%AE%E3%81%97%E3%81%8A%E3%82%8A%E4%BD%9C%E6%88%90-%E6%97%85%E8%A1%8C%E8%A8%88%E7%94%BB-navitime-travel/id1279724919)、[AI発表](https://corporate.navitime.co.jp/topics/pr/202403/29_5725.html)
- AVA Travel: [App Store](https://apps.apple.com/jp/app/%E3%82%A2%E3%83%90%E3%83%88%E3%83%A9%E3%83%99%E3%83%AB-%E6%B5%B7%E5%A4%96%E6%97%85%E8%A1%8C%E8%A8%88%E7%94%BB-%E6%97%85%E3%81%AE%E3%81%97%E3%81%8A%E3%82%8A-ai%E6%97%85%E8%A1%8C%E3%82%A2%E3%83%97%E3%83%AA/id6470335943)、[LINE OA](https://page.line.me/274usoti)、[LINE AI説明](https://travel.ava-intel.com/feature/column/line-ai-travel-recommendation/)
- Funliday: [FAQ](https://www.funliday.com/jp/faq)、[AI](https://www.funliday.com/ai?hl=ja)、[共同編集](https://www.funliday.com/posts/funliday-function-collaborative-editing/)、[Maps取込](https://www.funliday.com/posts/funliday-app-new-function-from-map-imoport-list-for-japaese/)
- Google Maps: [共有list](https://support.google.com/maps/answer/7280933?hl=ja)、[絵文字投票等](https://blog.google/products-and-platforms/products/maps/google-maps-updates-november-2023/)、[offline](https://support.google.com/maps/answer/6291838?hl=ja)、[Ask Maps発表とrollout範囲](https://blog.google/products-and-platforms/products/maps/ask-maps-immersive-navigation/)、[Ask Maps help](https://support.google.com/maps/answer/16842041?hl=en)
- Google Sheets: [共同作業](https://support.google.com/a/users/answer/13309904?hl=ja)、[Drive共有](https://support.google.com/drive/answer/2494822?hl=ja)、[offline](https://support.google.com/docs/answer/6388102?co=GENIE.Platform%3DDesktop&hl=ja)
- TravelCanvas: [公式サイト](https://travelcanvas.app/ja)
- タビノワ: [公式サイト](https://travelers-circle.com/)
- Limbo: [App Store](https://apps.apple.com/us/app/limbo-group-trip-planner/id6450775556)
- 旅のしおり: [公式サイト](https://tabinoshiori.jp/)
- tabitte: [公式サイト](https://tabitte.com/)
- TabinoTe: [公式サイト](https://tabinote-app.com/)、[公式FAQ](https://tabinote-app.com/faq)
- MapMemo: [開発者製品ページ](https://www.kinjo.me/products/6vmlzh5uc)
- Lightsplit: [運営者LINE Bot製品記事](https://lightsplit.com/ja/blog/lightsplit-line-bot-%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%97-%E5%89%B2%E3%82%8A%E5%8B%98)
- るるぶ＋AIチャット: [開始発表](https://jtbpublishing.co.jp/topics/CL000730)、[終了告知一覧](https://plus.rurubu.jp/news)

### 38.5 最終判断の要約

- **事実**: TabiSync Webの候補UI、map adapter、Schedule、共有、AI確認適用は再利用できる。ただし現行Places由来data→MapLibre/OpenFreeMapのflowは契約監査を通過した場合に限る。
- **事実**: Participant、個人Vote、Status、LINE、event、複数Planはない。
- **事実**: 競合は無登録共有、投票、LINE URL収集、AI旅程を要素別に既に提供する。
- **事実**: Messaging APIでgroup Botの技術PoCは可能。
- **未確認**: groupIdの長期binding、LINE文面の外部AI委託、安全なManager claim、現行Places→non-Google map data flowの契約適合。
- **提案**: Web意思決定domainを先に作り、薄型Botを接続し、URL取込とAIはdataと規約が整ってから進める。
- **撤退条件**: 実在groupで2人目の意味ある参加が起きない、またはLINEの中核bindingが許可されず縮退UXも受容されない場合、LINE中心戦略を拡大しない。
