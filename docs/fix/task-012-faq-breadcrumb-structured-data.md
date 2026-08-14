# Task 012: FAQページにパンくずリストとBreadcrumbList構造化データを追加する

- 観点: SEO
- 優先度: Medium

## 問題

ガイド5ページ（`docs/guide_sample.html`等）は`docs/_guide_breadcrumb.html`をincludeし、`BreadcrumbList`のJSON-LDも`_build_guide_page_context`（`tabisync/views/static_pages.py`）経由で生成しているが、同じ階層にある`docs/qanda.html`（FAQ、`/qa/`）は目次のみでパンくず表示も`BreadcrumbList`もない。FAQは検索流入が期待される主要ページであり、他ページと構成が非対称になっている。

## 実装指示

1. `QAView.get_context_data`（`tabisync/views/static_pages.py`）で、ガイドページと同じ`build_breadcrumb_list`（`tabisync/seo.py`）を使い、「ホーム > よくある質問」のパンくずデータを組み立てる。
2. `docs/qanda.html`の`{% block meta_extra %}`内のJSON-LDへ、既存の`FAQPage`と並べて`@graph`形式で`BreadcrumbList`を追加する（ホームの`home_json_ld`と同じ`@graph`パターンを踏襲する）。
3. `docs/qanda.html`のテンプレート冒頭に`{% include "docs/_guide_breadcrumb.html" %}`を追加し、画面表示のパンくずとJSON-LDを同じデータから生成する。

## テスト

- FAQページのJSON-LDがJSONとしてparseでき、`BreadcrumbList`と`FAQPage`の両方を含む。
- 画面上にパンくず「ホーム > よくある質問」が表示される。
- 既存の`faq_json_ld`が引き続き正しい質問・回答を含む。
- `pipenv run python manage.py test tabisync`が成功する。
