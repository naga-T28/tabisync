# Task 006: スケジュールの全件走査・逐次更新を削減する

- 観点: 処理速度
- 優先度: Medium

## 問題

`count_schedules_for_day` と `reorder_schedules_for_day` は、その日の予定だけでなく、しおりの全予定をPythonへ読み込み、`get_schedule_day_index` で選別します。並び替えは変更行ごとに `save()` するため最大N回UPDATEします。保存経路から複数回呼ばれ、データ量と同時編集の増加に比例して遅くなります。

V1の `prepare_travel_dates_with_schedules` にも日付ごとの関連取得によるN+1余地があり、`get_travel_date_range_context` は同一QuerySetへ `exists/first/last` を別々に発行します。

## 実装指示

1. `ScheduleV2.day_index` を現行V2の正規キーとして欠損データをmigrationで補完し、必要なら非NULL制約と複合indexを追加する。
2. 件数確認はDBの `filter(day_index=...).count()` にする。
3. 並び順更新は対象日のみ取得し、変更対象を `bulk_update` する。
4. 保存・削除・AI適用のトランザクション境界内で順序が一貫するようにする。
5. V1は `Prefetch` で予定を開始時刻順に取得し、日付範囲は評価済みリストまたは単一集計で求める。
6. `(itinerary, day_index, start_time, order)` など実クエリに合うindexを `EXPLAIN` で確認してから追加する。

## テスト

- 旧 `day_index=NULL` データの移行結果を確認する。
- 作成、日移動、削除後のorderが連番になる。
- `assertNumQueries` で表示・保存時クエリ数を固定し、予定件数増加でN+1にならない。
- migrationのdry-runと全テストを実行する。

