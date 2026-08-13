# Task 015: ガイド・FAQ・プロフィールページ用にOGP画像を個別設定する

- 観点: SEO
- 優先度: Medium

## 問題

ホームは`og_title`/`og_description`を上書きしているが`og_image`は上書きしておらず、FAQ・ガイド5ページ・プロフィール・お問い合わせなど他の公開ページも同様に`base.html`の既定OGP画像（`tabisync-v2-ogp.webp`）のままになっている。SNSでシェアされた際にページ内容と無関係な画像が表示され、クリック率に影響しうる。

## 実装指示

1. 優先度の高いページ（ガイド5ページ、FAQ）から、ページ内容が伝わるOGP用画像（1200×630px想定）を用意する。
2. 各テンプレートの`{% block og_image %}`・`{% block twitter_image %}`を、用意した画像への絶対URLで上書きする。
3. `{% block og_image_alt %}`も内容に合わせて上書きする。
4. 画像追加後、本番デプロイ後にFacebook Sharing DebuggerやTwitter Card ValidatorでOGP表示を確認する（本番URLが必要なため、デプロイ後の確認作業として記録する）。

## テスト

- 各ページの`<meta property="og:image">`が意図した画像URLになっていることをHTMLソースで確認する。
- 画像ファイルが実際に200で取得できる。
- `pipenv run python manage.py test tabisync`が成功する。
