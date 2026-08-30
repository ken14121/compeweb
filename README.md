# compeweb

Cloudflare Workers（静的アセット + API）でホストしている小さなサイト集。

| パス | 中身 |
|---|---|
| `/` | 高校生設計競技 2026-27（`public/index.html`） |
| `/eva/` | エヴァ件数カウンター（`public/eva/index.html`） |

## エヴァ件数カウンター

指定した期間に **42 のキャンパスで完了したピア評価（scale_teams）が何件あったか** を数えて表示します。
エヴァポイントセールの開始時刻を入れれば「セール開始後に何件レビューが行われたか」がそのまま出ます。

### 仕組み

42 API はページングされたエンドポイントで総件数を `x-total` ヘッダに返すので、
**件数を取るのに全件ページングは不要**（1 集計 = 1 リクエスト）です。

```
GET /v2/scale_teams
  ?filter[campus_id]=26
  &range[filled_at]=<開始>,<終了>
  &page[size]=1
→ x-total: 5616
```

`filled_at`（評価が完了した時刻）が基準なので、開始済みで未完了の評価は数に入りません。

- Worker（`src/index.js`）が client credentials でトークンを取り、集計値だけをブラウザに返します。
  `client_secret` はブラウザに一切渡りません。
- 42 API のレート制限（2 req/秒・1200 req/時）に合わせて、Worker 側で 550ms 間隔に直列化しています。
- トークンと集計結果は isolate のメモリにキャッシュします（過去の期間は 12 時間、現在を含む期間は 60 秒）。
  消えても正しさには影響しません。
- 日別の内訳は 1 区間 = 1 リクエストなので、必要なときだけボタンで取得します（最大 62 区間、
  62 日を超える期間は自動で週単位に切り替わります）。

### エンドポイント

| | |
|---|---|
| `GET /api/count?from=<ISO>&to=<ISO>` | 期間内の件数 `{ from, to, total, cached }` |
| `GET /api/config` | キャンパス情報とセール開始の既定値 |
| `GET /api/health` | 疎通確認 |

## セットアップ

### 1. 42 の OAuth アプリを作る

https://profile.intra.42.fr/oauth/applications/new

| 欄 | 値 |
|---|---|
| Name | 任意（ユニーク必須） |
| Description | 集計しか出さないこと・個人データを保存しないことを書く |
| Application type | Create statistics |
| Redirect URI | `http://localhost:8787/callback`（このアプリは client credentials のみ使うので実際には未使用） |
| Scopes | `public`（`/v2/scale_teams` が 403 なら `projects` を追加） |

### 2. 認証情報を入れる

ローカル:

```bash
cp .dev.vars.example .dev.vars   # 中身を実際の値に。.dev.vars はコミットされません
npm install
npm run dev                      # http://localhost:8787/eva/
```

本番:

```bash
npx wrangler secret put FT_CLIENT_ID
npx wrangler secret put FT_CLIENT_SECRET
npm run deploy
```

**`client_secret` をリポジトリやフロントエンドに置かないこと。** 漏らした場合は
アプリを Destroy して作り直すのが確実です（intra には手動の再発行ボタンがありません）。

### 3. キャンパスとセール開始（任意）

`wrangler.jsonc` の `vars` で設定します。

| 変数 | 既定 | 意味 |
|---|---|---|
| `CAMPUS_ID` | `26` | 42Tokyo。他キャンパスは `/v2/campus?page[size]=100` で調べる |
| `CAMPUS_NAME` | `42Tokyo` | 画面の表示名 |
| `SALE_START` | 空 | 「セール開始から」プリセットの既定値。例 `2026-08-25T18:00:00+09:00` |

`SALE_START` が空でも、画面上で開始日時を入れて「開始をセール開始として保存」を押せば
ブラウザ（localStorage）に保存されます。

## 動作確認メモ

`curl` で 42 API を叩くときは **`-g`（`--globoff`）が必須** です。付けないと curl が
`page[size]` の角括弧を範囲指定として解釈し、`bad range in URL` で失敗します
（`-s` を付けていると何も表示されないので、原因が分かりにくい）。

```bash
export FT_UID='u-s4t2ud-...'
read -s "FT_SECRET?Secret: " && export FT_SECRET

TOKEN=$(curl -s -X POST https://api.intra.42.fr/oauth/token \
  -d grant_type=client_credentials -d client_id="$FT_UID" -d client_secret="$FT_SECRET" \
  | jq -r .access_token)

curl -sS -g -D - -o /dev/null -H "Authorization: Bearer $TOKEN" \
  "https://api.intra.42.fr/v2/scale_teams?filter[campus_id]=26&range[filled_at]=2026-08-01T00:00:00.000Z,2026-08-30T00:00:00.000Z&page[size]=1"
```
