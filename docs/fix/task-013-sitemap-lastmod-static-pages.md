# Task 013: サイトマップのlastmodをガイド・規約ページにも設定する

- 観点: SEO
- 優先度: Medium

## 問題

`StaticViewSitemap.lastmod()`（`tabisync/sitemaps.py`）は`tabisync:updates`以外常に`None`を返しており、ガイド5ページや利用規約・プライバシーポリシーなど更新頻度のあるページの`lastmod`がサイトマップに反映されていない。

## 実装指示

1. `updates`向けに実装済みの「テンプレートファイルの`mtime`を`lastmod`として使う」ロジックを、`SITEMAP_URL_NAMES`内の他の静的テンプレート（ガイド5ページ、利用規約、プライバシーポリシー、AIコンシェルジュ利用規約、プロフィール）にも汎用化して適用する。
2. URL名からテンプレートパスを引けるマッピング、または各Viewの`template_name`を参照する仕組みを`lastmod()`内に実装する。
3. `create`ページのように今後もフォームが中心のページは、対応する説明文テンプレートの`mtime`を使うか、明示的に対象外のままにするかを決める。

## テスト

- `sitemap.xml`を生成し、`SITEMAP_URL_NAMES`内の各URLに妥当な`lastmod`（未来日・不正値でない）が出力される。
- 対象テンプレートファイルが存在しない・アクセスできない場合に例外を出さず`None`にフォールバックする（既存の`updates`向け実装と同じtry/except方針を踏襲する）。
- `pipenv run python manage.py test tabisync`が成功する。
