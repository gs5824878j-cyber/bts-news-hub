# FOREMIRA 移行準備

作業ブランチ prepare/foremira。当初の準備段階では本番反映を保留。現在は利用者の移行変更許可と所有確認・DNS設定後に、BTSから段階的に切り替える。未切替サービスへのリンクは旧公開URLを維持する。

全体の試験・URL対応・バックアップ・未確認事項と切り替え手順は `/workspace/foremira-migration/README.md` を参照。

## ローカル回帰試験

`python3 -m unittest discover -s tests -v`
