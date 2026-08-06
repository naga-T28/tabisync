# コードレビュー修正タスク一覧

`project_tabisync` 配下を、セキュリティ、コードの冗長性、処理速度の観点でレビューした結果です。各ファイルは、そのまま実装担当者へ渡せる単位に分割しています。

## 推奨実施順

1. `task-001-want-to-go-edit-authorization.md`（Critical）
2. `task-002-safe-json-embedding.md`（High）
3. `task-003-proxy-aware-rate-limit.md`（High）
4. `task-004-atomic-limit-enforcement.md`（High）
5. `task-005-centralize-itinerary-access-control.md`（Medium）
6. `task-006-optimize-schedule-ordering-and-queries.md`（Medium）
7. `task-007-harden-input-and-external-http-handling.md`（Medium）

## 共通完了条件

- V2の修正をV1へ無条件に展開しない。
- UUIDトークン、閲覧パスワード、編集パスワードの役割を維持する。
- 外部APIはテストでモックする。
- `pipenv run python manage.py check` と `pipenv run python manage.py test tabisync` が成功する。
- モデル変更時はmigrationを追加し、`makemigrations --check --dry-run` も成功する。

