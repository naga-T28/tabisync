# Task 008: 本番ドメインのHTTPS・www正規化リダイレクトを整備する

- 種別: インフラ / DNS / Nginx / Django設定
- 優先度: Medium
- 状態: 調査済み / 実装待ち
- 対象: 本番（および必要であればステージング）の入口となるドメイン・リバースプロキシ設定
- 対象外: アプリケーションコードの機能変更、Task 007のSearch Console/Bing登録そのもの（本タスクはその前提となるドメイン正規化のみを扱う）
- 調査基準日: 2026-08-13

## 前提

Task 004で`PUBLIC_BASE_URL`（例: `https://tabisync.com`）を導入し、canonical・OGP・JSON-LD・サイトマップ・`robots.txt`のSitemap行が全てこの値を単一の正とするようになっている。しかし、実際にそのURL以外の経路（`http://`、`www.tabisync.com`、末尾スラッシュ有無の別バリエーション）でアクセス可能なままだと、検索エンジンから見て同一コンテンツが複数URLで存在することになり、`PUBLIC_BASE_URL`を導入した効果が薄れる。本タスクはその入口を1つに統一する。

**本タスクはNginx・DNSなど本番インフラの変更を伴い、本番権限と明示的な承認が必須である。この文書はリポジトリ内で確認できる現状整理と、実施者（人）向けの実装・確認手順を示すのみで、Claudeが単独で実施することはない。**

## 現状整理（コード調査済み）

- このリポジトリにNginx設定ファイルは含まれていない（`containers/`配下は`containers/django/Dockerfile`と`entrypoint.sh`のみ）。`docker-compose.yml`・`docker-compose-staging.yml`にもNginxサービス定義がない。したがって、HTTP→HTTPS・www統一のリダイレクトは本リポジトリ外（サーバー側のNginx設定、またはDNS/CDNレベル）で管理されている、もしくは未設定である可能性が高い。
- `project_tabisync/settings.py`では、本番相当（`DEBUG=False`）時に`SECURE_SSL_REDIRECT = USE_HTTPS`（既定`True`）、`SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`が設定されており、Djangoの手前にTLS終端を行うプロキシが存在する前提の構成になっている。
- `ALLOWED_HOSTS`は環境変数`ALLOWED_HOSTS`（カンマ区切り）をそのまま使う。複数ホスト（例: `tabisync.com,www.tabisync.com`）を許可している場合、Django自体はどちらのHostでもリクエストを受け付けてしまい、正規化はプロキシ側の責務になる。
- `CSRF_TRUSTED_ORIGINS`は`ALLOWED_HOSTS`から`USE_HTTPS`に応じて自動生成されるため、正規ドメインを1つに絞ってもCSRF設定側の追加変更は基本的に不要（`ALLOWED_HOSTS`を絞ればここも自動的に絞られる）。
- 開発環境の`CSRF_TRUSTED_ORIGINS`には`https://staging.tabisync.com`がハードコードされている。ステージングドメインが存在することが分かるため、ステージング側の正規化・`noindex`運用もあわせて確認する（Task 004で「ステージングでは全ページをnoindexとし、本番URLのサイトマップを生成・送信しない」方針は明文化済みだが、実際のステージング環境変数設定は本タスクの対象）。

## 決めるべきこと

- [ ] 正規ホストを`tabisync.com`（apex）と`www.tabisync.com`のどちらにするか決定する（`PUBLIC_BASE_URL`は既に`https://tabisync.com`を例に設定されているため、特段の理由がなければapexを正規とする想定）。
- [ ] 末尾スラッシュの扱いを確認する（Django既定の`APPEND_SLASH`挙動と、Nginx側リダイレクトが二重にならないようにする）。
- [ ] ステージング（`staging.tabisync.com`）を検索エンジンから完全に遮断する方法（`noindex`ヘッダーの一律付与、または Basic認証・IP制限との併用）を決定する。

## 実装タスク

### DNS・証明書

- [ ] 正規ホストとリダイレクト元ホスト（apex/www双方、httpも）すべてに有効なTLS証明書が発行されていることを確認する。
- [ ] DNSレコードが正規ホスト・リダイレクト元ホストの両方について正しく設定されていることを確認する。

### Nginx（またはCDN/プロキシ）側

- [ ] `http://` → `https://`の301リダイレクトを設定する。
- [ ] 非正規ホスト（apexを正規とする場合は`www.tabisync.com`）→ 正規ホストへの301リダイレクトを設定する。
- [ ] 上記2つを1回のリダイレクトで正規URLに到達できるよう統合する（`http://www.tabisync.com/x` → `https://tabisync.com/x`のように2ホップにしない）。
- [ ] リダイレクト時にパス・クエリ文字列を保持する。
- [ ] `X-Forwarded-Proto`ヘッダーをDjangoへ正しく転送する（`SECURE_PROXY_SSL_HEADER`の前提と一致させる）。
- [ ] ステージング環境で、全レスポンスに`X-Robots-Tag: noindex, nofollow`または同等のブロックを設定する（Nginx側で一律付与するか、Django側の`ALLOWED_HOSTS`/環境変数で判定して`meta robots`を切り替えるかを決定し実装する）。

### Django側の確認（本リポジトリで対応可能な範囲）

- [ ] 本番環境変数`ALLOWED_HOSTS`が正規ホスト（および必要な内部ヘルスチェック用ホスト等）のみを含み、不要な別名を含んでいないことを確認する。
- [ ] `PUBLIC_BASE_URL`が正規ホストと一致していることを確認する（Task 004で導入済みの起動時チェックが、正規ホスト設定時にエラーなく起動することを確認する）。
- [ ] ステージング環境変数で`PUBLIC_BASE_URL`をステージング自身のURLに設定し、本番URLをサイトマップへ出力しないことを確認する（Task 004の`get_domain`/`get_protocol`実装により`PUBLIC_BASE_URL`を切り替えるだけで反映される）。

## 検証コマンド

```bash
# httpからのリダイレクト
curl -I http://tabisync.com/

# wwwからのリダイレクト（正規ホストをapexとする場合）
curl -I https://www.tabisync.com/

# 正規URLが200で応答する
curl -I https://tabisync.com/

# リダイレクトが1回で正規URLに到達する
curl -IL http://www.tabisync.com/ | grep -i "^location\|^HTTP"

# ステージングがnoindexであること
curl -s https://staging.tabisync.com/ | grep -i "noindex"
curl -I https://staging.tabisync.com/ | grep -i "x-robots-tag"
```

## 完了条件

- `http://`、`www`有無の全パターンが1回の301リダイレクトで単一の正規URL（`PUBLIC_BASE_URL`と一致）へ到達する。
- 正規ホスト以外では`X-Forwarded-Proto`が正しくDjangoへ伝わり、Django側のHTTPS関連セキュリティ設定（`SECURE_SSL_REDIRECT`等）と矛盾しない。
- ステージング環境が検索エンジンから確実に除外されている。
- `ALLOWED_HOSTS`・`PUBLIC_BASE_URL`が環境ごとに正しい値へ設定されている。

## 注意事項

- 本タスクの実施には本番DNS・証明書・リバースプロキシへのアクセス権限が必要であり、実施前に必ず人による承認を得る。
- リダイレクト設定の変更はサイト全体の可用性に影響するため、本番反映前にステージングまたは同等の環境で動作確認する。
- 正規ホストの決定（apex/www）はSEO評価の蓄積に関わるため、一度決めたら安易に変更しない。変更する場合はTask 007のSearch Console運用と連携し、影響を監視する。
