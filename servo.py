#!/usr/bin/env python3
"""SG90 servo controller for Claude Code integration
Usage:
  python3 servo.py start   # サーボ揺らし開始（バックグラウンド）
  python3 servo.py stop    # 停止・中央に戻す
  python3 servo.py run     # サーボ揺らし開始（フォアグラウンド・Docker用）
"""

import sys
import os
import time

SERVO_PIN = 18
PWM_FREQ  = 50
FLAG_FILE = "/tmp/claude_servo.flag"
PID_FILE  = "/tmp/claude_servo.pid"


def angle_to_pw(angle):
    return int(500 + (angle / 180.0) * 2000)


def sweep_loop():
    import lgpio
    import threading
    from RPLCD.i2c import CharLCD

    h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(h, SERVO_PIN)
    lgpio.tx_servo(h, SERVO_PIN, angle_to_pw(90))
    time.sleep(0.3)

    lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2)

    def scroll_text():
        text = "bakusoku"
        width = 16
        pos = 0
        while os.path.exists(FLAG_FILE):
            line = "".join(
                text[col - pos] if 0 <= col - pos < len(text) else " "
                for col in range(width)
            )
            lcd.home()
            lcd.write_string(line)
            pos = (pos + 1) % (width + len(text))
            time.sleep(0.15)

    t = threading.Thread(target=scroll_text, daemon=True)
    t.start()

    angle = 90
    direction = 1

    try:
        while os.path.exists(FLAG_FILE):
            angle += direction * 4
            if angle >= 170:
                angle = 170
                direction = -1
            elif angle <= 10:
                angle = 10
                direction = 1
            lgpio.tx_servo(h, SERVO_PIN, angle_to_pw(angle))
            time.sleep(0.02)

        lgpio.tx_servo(h, SERVO_PIN, angle_to_pw(90))
        time.sleep(0.5)
    finally:
        t.join(timeout=1)
        lcd.clear()
        lcd.close(clear=True)
        lgpio.tx_servo(h, SERVO_PIN, 0)
        lgpio.gpiochip_close(h)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def start():
    if os.path.exists(FLAG_FILE):
        return  # すでに動作中

    open(FLAG_FILE, "w").close()

    pid = os.fork()
    if pid == 0:
        os.setsid()
        sweep_loop()
        sys.exit(0)
    else:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))


def stop():
    if os.path.exists(FLAG_FILE):
        os.remove(FLAG_FILE)

    for _ in range(30):
        time.sleep(0.1)
        if not os.path.exists(PID_FILE):
            break


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("start", "stop", "run"):
        print("Usage: python3 servo.py start|stop|run")
        sys.exit(1)

    if sys.argv[1] == "start":
        start()
    elif sys.argv[1] == "stop":
        stop()
    else:
        import signal
        def handle_sigterm(signum, frame):
            if os.path.exists(FLAG_FILE):
                os.remove(FLAG_FILE)
        signal.signal(signal.SIGTERM, handle_sigterm)
        open(FLAG_FILE, "w").close()
        sweep_loop()
