# Task 008: ステージング環境をコード側でnoindexへ強制する

- 観点: SEO
- 優先度: Critical

## 問題

`settings.py`の開発環境`CSRF_TRUSTED_ORIGINS`にステージング用ドメイン`staging.tabisync.com`が存在するが、環境を判定して`X-Robots-Tag`やmeta robotsを一律`noindex`にする仕組みがない。`base.html`/`base_home.html`の`{% block robots_meta %}`は既定で`index, follow`（`templates/base.html`）を返すため、本番と同じアプリケーションコードのままステージングを公開すると、そのまま検索エンジンのインデックス対象になり得る。

一度ステージングURLがインデックスされると、本番と同一・類似コンテンツの重複ドメインとしてクロール予算・評価が分散し、除去にも時間がかかる。`docs/task/task-008-origin-redirect-normalization.md`ではNginx側の対応も含めて整理済みだが、Django側だけで確実に守れる部分がまだ実装されていない。

## 実装指示

1. 環境変数（例: `ENVIRONMENT`）を追加し、`settings.py`で値が`production`でない場合に`IS_PRODUCTION = False`のようなフラグをsettingsへ公開する。
2. `MIDDLEWARE`へ軽量なミドルウェアを追加し、`IS_PRODUCTION`が`False`のとき、全レスポンスへ`X-Robots-Tag: noindex, nofollow`を強制的に設定する（テンプレート側の`robots_meta`ブロックの値に関わらず上書きする）。
3. デプロイ手順・READMEに、ステージングでは新しい環境変数を明示的に`production`以外へ設定する必要がある旨を追記する。
4. `PUBLIC_BASE_URL`がステージング自身のURLを指している前提を崩さないことを確認する（`tabisync/sitemaps.py`の`get_domain`/`get_protocol`は`PUBLIC_BASE_URL`を参照済みのため、環境変数さえ正しく設定すればサイトマップも自動的にステージング用URLになる）。

## テスト

- `ENVIRONMENT`未設定・`staging`・`development`のいずれでも、任意のURL（公開ページ・noindex対象ページ双方）のレスポンスへ`X-Robots-Tag: noindex, nofollow`が付くことを確認する。
- `ENVIRONMENT=production`のときは公開ページで余分な`X-Robots-Tag`が付与されず、noindex対象ページでは既存の`add_noindex_header`由来のヘッダーのみが付くことを確認する（本番の`index, follow`ページを誤ってnoindexにしない）。
- 既存のcanonical・OGP・JSON-LD・サイトマップの出力がこの変更で変化しないことを確認する。
- `pipenv run python manage.py test tabisync`が成功する。
