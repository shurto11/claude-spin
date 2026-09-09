# claude-spin

Raspberry Pi に繋いだ **SG90 サーボ** と **I2C キャラクタ LCD (16x2)** を、Claude Code の動作状況に連動させるガジェットです。

- Claude が**応答中** → サーボが左右にスイングし、LCD に `bakusoku` が流れる
- Claude が**待機中** → LCD に Claude の使用量（5時間セッション / 週間）をバーグラフで交互表示

## 構成

| ファイル | 役割 |
| --- | --- |
| `servo.py` | サーボのスイング制御 + LCD への文字スクロール（応答中の演出） |
| `app.py` | 待機中に `/tmp/claude_usage.json` を読んで使用率を LCD に表示 |
| `Dockerfile` | `servo.py` 用イメージ（RPLCD / smbus2 / lgpio） |
| `Dockerfile.lcd` | `app.py` 用イメージ（RPLCD / smbus2） |
| `docker-compose.yml` | 常駐する `lcd` サービス（使用量表示）の定義 |
| `claude-lcd.service` | Docker を使わず systemd で `app.py` を常駐させる場合のユニット |

### 状態ファイル

| パス | 内容 |
| --- | --- |
| `/tmp/claude_servo.flag` | 存在する間サーボが動く。消すと停止して 90° に戻る |
| `/tmp/claude_servo.pid` | スイング中のプロセス PID（`start` 時のみ） |
| `/tmp/claude_usage.json` | 使用量 JSON。`five_hour.utilization` / `seven_day.utilization` を参照 |

`app.py` は flag / pid のどちらかが存在する間は LCD への描画を止め、`servo.py` に LCD を明け渡します。

## ハードウェア

- Raspberry Pi（I2C 有効化済み: `/dev/i2c-1`）
- SG90 サーボ → **GPIO18**（PWM 50Hz、パルス幅 500〜2500µs）
- I2C LCD 16x2（PCF8574 バックパック、アドレス `0x27`）

## セットアップ

```bash
sudo apt install -y python3-lgpio i2c-tools
pip install RPLCD smbus2 lgpio

# LCD がアドレス 0x27 で見えることを確認
i2cdetect -y 1
```

## 使い方

### 直接実行

```bash
python3 servo.py start   # バックグラウンドでスイング開始（fork + flag 作成）
python3 servo.py stop    # flag を削除して停止・中央へ復帰
python3 servo.py run     # フォアグラウンド実行（Docker / SIGTERM で停止）
```

### Docker

```bash
# 使用量表示（常駐）
docker compose up -d lcd

# サーボ演出（Claude 応答中だけ起動する想定）
docker build -t claude-spin .
docker run --privileged --device /dev/gpiochip0 --device /dev/i2c-1 \
  -d --name claude-servo claude-spin python servo.py run
docker stop claude-servo && docker rm claude-servo
```

### systemd（Docker を使わない場合）

```bash
sudo cp claude-lcd.service /etc/systemd/system/
sudo systemctl enable --now claude-lcd
```

> `claude-lcd.service` の `ExecStart` はパスが `/home/shurto11/claude-spin/app.py` になっています。設置場所に合わせて書き換えてください。

## Claude Code との連携

Claude Code の hooks から、SSH 越しに Raspberry Pi の Docker コンテナを起動・停止します。

- **UserPromptSubmit**（応答開始）→ `claude-servo` コンテナを起動 → サーボが回る
- **Stop**（応答終了）→ 使用量 JSON を Pi の `/tmp/claude_usage.json` に転送し、コンテナを停止 → LCD が使用量表示に戻る

使用量は `claude.ai/api/oauth/usage` を叩いて取得した JSON をそのまま流し込む形です。

## 注意

- `servo.py run` を Docker で動かす場合、`/tmp` はコンテナ内の名前空間になります。`app.py` 側（`lcd` サービスはホストの `/tmp` をマウント）とフラグを共有して LCD の取り合いを避けるには、サーボ側のコンテナにも `-v /tmp:/tmp` を付けてください。
- GPIO と I2C にアクセスするため、コンテナは `--privileged`（または該当デバイスの権限）が必要です。
