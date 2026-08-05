# Task 007: 入力検証と外部HTTP処理を堅牢化する

- 観点: セキュリティ、コードの冗長性、処理速度
- 優先度: Medium

## 問題

- `views/utils.py:verify_turnstile` は `json` をimportしておらず、成功レスポンスでも例外となります。
- Turnstileの `urlopen` にtimeoutがなく、Webワーカーが長時間占有され得ます。
- 例外を `print` しており、ログ方針と不一致です。
- `apply_want_to_go_payload` は不正数値を空値へ丸め、モデルの文字数・緯度経度・priority/day範囲を保存前に明示検証しません。
- 複数のJSONエンドポイントでデコード・型検査・エラー応答が重複し、一部は不正JSONで500になり得ます。

## 実装指示

1. Turnstile処理に必要なimport、短い設定可能timeout、構造化logger、secret未設定時の明示的な安全側エラーを追加する。
2. Turnstileへ送るIPはTask 003の共通取得処理を使う。
3. JSON bodyのサイズ、object型、Content-Type、デコードを検証する共通helperを作る。
4. 行きたい場所入力をDjango Form等で検証し、緯度 `[-90,90]`、経度 `[-180,180]`、旅行日範囲、許可priority、文字数上限を400エラーとして返す。不正値を黙ってNoneへ変換しない。
5. 外部APIエラーの詳細やsecretを非DEBUG応答へ出さない。

## テスト

- Turnstile成功・拒否・timeout・不正JSON・secret未設定をモックで確認する。
- 各JSON APIの空body、配列body、巨大body、不正UTF-8、不正Content-Typeを確認する。
- 境界値および範囲外の位置・日・priority・長文を確認する。

