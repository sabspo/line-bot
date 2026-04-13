# Google Sheets 連携 価格問い合わせボット

Google スプレッドシートをマスタとして読み込み、ユーザーの価格問い合わせメッセージに対して自動返信を返す試作アプリです。自動返信で完結しない問い合わせは、手動返信キューに積んで管理画面から対応できます。

## できること

- `team` `aliases` `price_table_items` `templates` `test_cases` シートを参照して返信文を生成
- チーム名や alias からチームを特定
- `自動応答対象 = 対象` かつ `確認ステータス = OK` の商品だけを一覧化
- `要確認` 商品があれば `TMP-003` を使って自動返信
- チーム不明や商品未登録のケースは手動対応キューに保存
- 管理 API / 管理画面から手動返信を送信

## ファイル構成

- `main.py`: CLI 実行入口
- `sheets_client.py`: Google Sheets 読み込み
- `reply_service.py`: 返信判定ロジック
- `manual_reply_store.py`: 手動返信キュー保存
- `app.py`: Flask + LINE Webhook + 管理 API
- `models.py`: dataclass 定義
- `config.py`: 設定値
- `tests/`: 単体テスト / 統合テスト / 手動返信テスト

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Google Sheets 認証

サービスアカウント JSON はプロジェクト外に置き、`SERVICE_ACCOUNT_FILE` で参照する運用を推奨します。

```powershell
$env:SERVICE_ACCOUNT_FILE="C:\Users\info\.secrets\line-bot-service-account.json"
$env:SPREADSHEET_URL="https://docs.google.com/spreadsheets/d/1-oLYHthSg4pawoW5F-UOqIY6hz4mkvM8gl39CXDgKoA/edit?usp=sharing"
```

注意:

- JSON は Git 管理配下や OneDrive 同期対象に置かない
- サービスアカウントの `client_email` を対象スプレッドシート共有に追加する
- 権限はまず `閲覧者` で十分

## LINE / 手動返信の環境変数

```powershell
$env:CHANNEL_ACCESS_TOKEN="..."
$env:CHANNEL_SECRET="..."
$env:MANUAL_REPLY_ADMIN_TOKEN="長くて推測しにくい文字列"
$env:MANUAL_REPLY_STORAGE_FILE="C:\Users\info\OneDrive\デスクトップ\line-bot\data\pending_manual_replies.json"
```

補足:

- `CHANNEL_ACCESS_TOKEN` と `CHANNEL_SECRET` は LINE Webhook 用
- `MANUAL_REPLY_ADMIN_TOKEN` は管理 API と管理画面保護用
- `MANUAL_REPLY_STORAGE_FILE` は未設定なら `data/pending_manual_replies.json`

## CLI 実行

```bash
python main.py "つくしヤングラガーズ小学部です。商品の価格を教えてください。"
```

## Python からの利用例

```python
from reply_service import generate_reply

reply = generate_reply("つくしヤングラガーズ小学部です。商品の価格を教えてください。")
print(reply)
```

## LINE Webhook 起動

```bash
python app.py
```

`/callback` に LINE Webhook を向けると、受信メッセージに応じて自動返信します。

## 自動返信と手動返信の運用

現在の判定方針:

- `TMP-001`: 価格一覧を自動返信
- `TMP-003`: 要確認商品を除いた一覧を自動返信
- `TMP-002`: 自動返信したうえで手動対応キューに保存
- `TMP-004`: 自動返信したうえで手動対応キューに保存

手動返信フロー:

1. ユーザーが問い合わせ
2. 自動返信できない案件はキューへ保存
3. 管理者が一覧を確認
4. 管理者が返信文を入力して送信
5. LINE に push 送信し、案件を `replied` に更新

## 管理 API

### 未対応一覧取得

```http
GET /manual-replies
X-Admin-Token: <MANUAL_REPLY_ADMIN_TOKEN>
```

### 管理画面

```text
GET /manual-replies/ui
```

ブラウザで開き、`X-Admin-Token` ヘッダを付けてアクセスしてください。

### 手動返信送信

```http
POST /manual-replies/<request_id>/reply
X-Admin-Token: <MANUAL_REPLY_ADMIN_TOKEN>
Content-Type: application/json

{
  "user_id": "Uxxxxxxxx",
  "message_text": "担当者が確認してご連絡します。"
}
```

フォーム送信にも対応しています。

## テスト

通常実行:

```bash
pytest -q
```

現在のテスト対象:

- 返信ロジックの単体テスト
- 実シート統合テスト
- `test_cases` シート照合
- 手動返信キュー保存
- 管理 API / 管理画面

直近の確認結果:

- `19 passed, 3 skipped`

`SERVICE_ACCOUNT_FILE` が設定され、実シートにアクセスできる状態では、実シート統合テストも通る想定です。

## 補足

- 列名の揺れに備えて、主要列は複数候補で探索しています
- 空欄や `None` に強いように文字列化して比較しています
- チーム不明や商品未登録を完全に無視せず、手動返信へ自然につなげる構成にしています
