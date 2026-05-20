from RPLCD.i2c import CharLCD
from time import sleep
import os
import json
import time

FLAG_FILE  = "/tmp/claude_servo.flag"
PID_FILE   = "/tmp/claude_servo.pid"
USAGE_FILE = "/tmp/claude_usage.json"

DISPLAY_INTERVAL = 3  # 切り替え間隔（秒）


def read_usage():
    try:
        with open(USAGE_FILE) as f:
            data = json.load(f)
        session = data.get("five_hour", {}).get("utilization")
        week    = data.get("seven_day", {}).get("utilization")
        return session, week
    except Exception:
        return None, None


def make_bar(pct, width=16):
    if pct is None:
        return "-" * width
    filled = round(width * pct / 100)
    return "#" * filled + "-" * (width - filled)


def make_label(label, pct):
    pct_str = f"{pct:.0f}%" if pct is not None else "--%"
    gap = max(1, 16 - len(label) - len(pct_str))
    return (label + " " * gap + pct_str)[:16]


print("start")

lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2)

print("lcd connected")

show_session = True
last_switch  = 0.0
was_active   = False

while True:
    now = time.time()
    is_active = os.path.exists(FLAG_FILE) or os.path.exists(PID_FILE)

    if is_active:
        was_active = True
        sleep(0.5)
        continue

    if was_active:
        was_active = False
        last_switch = 0.0

    if now - last_switch >= DISPLAY_INTERVAL:
        session_pct, week_pct = read_usage()

        if show_session:
            line1 = make_label("Session", session_pct)
            line2 = make_bar(session_pct)
        else:
            line1 = make_label("This Week", week_pct)
            line2 = make_bar(week_pct)

        lcd.home()
        lcd.write_string(line1.ljust(16))
        lcd.crlf()
        lcd.write_string(line2.ljust(16))

        show_session = not show_session
        last_switch  = now

    sleep(0.1)
