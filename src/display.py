"""Three 128x64 pages and code-driven weather icons, no font download."""
import framebuf
import time


def ascii_text(value):
    return "".join(char if 32 <= ord(char) < 127 else "?" for char in str(value))


def category(code):
    if code in (0, 2):
        return "SUN"
    if code in (1, 3):
        return "CLEAR"
    if code == 9:
        return "OVERCAST"
    if 4 <= code <= 8:
        return "CLOUD"
    if code in (11, 12):
        return "THUNDER"
    if code in (20, 21):
        return "SLEET"
    if 10 <= code <= 19:
        return "RAIN"
    if 22 <= code <= 25:
        return "SNOW"
    if 26 <= code <= 29:
        return "DUST"
    if code == 30:
        return "FOG"
    if code == 31:
        return "HAZE"
    if 32 <= code <= 36:
        return "WIND"
    if code == 37:
        return "HOT"
    if code == 38:
        return "COLD"
    return "UNKNOWN"


def circle(screen, cx, cy, radius):
    x, y, delta = radius, 0, 1 - radius
    while x >= y:
        for dx, dy in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
            screen.pixel(cx + dx, cy + dy, 1)
        y += 1
        if delta < 0:
            delta += 2 * y + 1
        else:
            x -= 1
            delta += 2 * (y - x) + 1


def icon(screen, x, y, size, code):
    kind = category(code)
    mid, radius = size // 2, max(2, size // 5)
    if kind in ("SUN", "HOT"):
        circle(screen, x + mid, y + mid, radius)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            screen.line(x + mid + dx * (radius + 2), y + mid + dy * (radius + 2),
                        x + mid + dx * (radius + 3), y + mid + dy * (radius + 3), 1)
    elif kind == "CLEAR":
        circle(screen, x + mid, y + mid, radius + 2)
        for row in range(size):
            for col in range(size):
                if (col - (mid + 3)) ** 2 + (row - (mid - 2)) ** 2 <= (radius + 2) ** 2:
                    screen.pixel(x + col, y + row, 0)
    elif kind in ("FOG", "HAZE", "DUST", "WIND"):
        for offset in (3, 6, 9):
            screen.hline(x + 1 + (offset % 2), y + offset, size - 3, 1)
        if kind == "WIND":
            screen.line(x + size - 4, y + 2, x + size - 2, y + 3, 1)
    elif kind in ("COLD", "SNOW"):
        screen.vline(x + mid, y + 2, size - 4, 1)
        screen.hline(x + 2, y + mid, size - 4, 1)
        screen.line(x + 3, y + 3, x + size - 4, y + size - 4, 1)
        screen.line(x + 3, y + size - 4, x + size - 4, y + 3, 1)
    elif kind == "UNKNOWN":
        screen.text("?", x + 3, y + 3)
    else:
        base = y + size // 2
        circle(screen, x + size // 3, base - 1, radius)
        circle(screen, x + mid + 1, base - 3, radius + 1)
        screen.fill_rect(x + 2, base, size - 4, 3, 1)
        if kind in ("RAIN", "SLEET"):
            for offset in (3, 7, 11):
                screen.line(x + offset, base + 4, x + offset - 1, base + 6, 1)
        elif kind == "THUNDER":
            screen.line(x + mid, base + 3, x + mid - 2, base + 5, 1)
            screen.line(x + mid - 2, base + 5, x + mid + 1, base + 5, 1)
            screen.line(x + mid + 1, base + 5, x + mid - 1, base + 7, 1)


class Display:
    def __init__(self, oled, config):
        self.oled = oled
        self.config = config
        self.big_buffer = bytearray(5 * 8)
        self.big = framebuf.FrameBuffer(self.big_buffer, 40, 8, framebuf.MONO_VLSB)

    def text(self, value, x, y, count=None):
        limit = (128 - x) // 8 if count is None else count
        self.oled.text(ascii_text(value)[:limit], x, y)

    def large_time(self, value):
        self.big.fill(0)
        self.big.text(value, 0, 0)
        for y in range(8):
            for x in range(40):
                if self.big.pixel(x, y):
                    self.oled.fill_rect(x * 2, 10 + y * 2, 2, 2, 1)

    def status(self, app, name):
        if not app.wifi.online():
            return "OFFLINE"
        entry = app.entries[name]
        if entry["data"] is None:
            return "WAIT" if entry["ok"] is None else "FAIL"
        if not entry["ok"] or time.ticks_diff(time.ticks_ms(), entry["last_success"]) >= self.config.WEATHER_INTERVAL:
            return "STALE"
        return "OK"

    def draw(self, app):
        self.oled.fill(0)
        if app.page == 0:
            self.current(app)
        elif app.page == 1:
            self.forecast(app)
        else:
            self.network(app)
        self.oled.show()

    def current(self, app):
        local = app.clock.local()
        if local:
            weekday = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")[local[6]]
            self.text("%04d-%02d-%02d %s" % (local[0], local[1], local[2], weekday), 8, 0)
            self.large_time("%02d:%02d" % (local[3], local[4]))
            self.text("%02d" % local[5], 83, 18)
        else:
            self.text("DATE: NOT SYNCED", 0, 0)
            self.large_time("--:--")
            self.text("--", 83, 18)
        now = app.entries["now"]["data"]
        if now:
            icon(self.oled, 98, 8, 30, now["code"])
            city = self.config.CITY_LABEL or now["city"]
            self.text(city, 0, 30, 12)
            self.text(now["text"], 0, 42, 11)
            self.text("%dC" % now["temperature"], 96, 42)
        else:
            if app.wifi.server is not None:
                self.text("AP:" + self.config.AP_NAME, 0, 30)
                self.text(app.wifi.ip(), 0, 42)
            else:
                self.text("Weather: no data", 0, 30)
                self.text(app.entries["now"]["error"] or "Waiting...", 0, 42)
        if app.indoor is None:
            self.text("IN:-- RH:--", 0, 54)
        else:
            self.text("IN:%dC RH:%d%%%s" % (app.indoor[0], app.indoor[1], "!" if not app.dht_ok else ""), 0, 54)

    def forecast(self, app):
        self.text("3-DAY FORECAST", 8, 0)
        days = app.entries["daily"]["data"]
        if days:
            for index, day in enumerate(days[:3]):
                y = 10 + index * 18
                self.text(day["date"][5:], 0, y)
                icon(self.oled, 42, y, 16, day["code"])
                self.text(category(day["code"]), 61, y)
                self.text("%d~%dC" % (day["low"], day["high"]), 61, y + 8)
        else:
            self.text("No forecast data", 0, 22)
            self.text(app.entries["daily"]["error"] or "Waiting...", 0, 34)

    def network(self, app):
        self.text("WIFI:" + ("ONLINE" if app.wifi.online() else "OFFLINE"), 0, 0)
        self.text(app.wifi.ip(), 0, 8)
        self.text(app.clock.status(app.wifi.online()), 0, 16)
        self.text("NOW:" + self.status(app, "now"), 0, 24)
        self.text("LAST:" + app.entries["now"]["stamp"], 0, 32)
        self.text("FC:" + self.status(app, "daily"), 0, 40)
        self.text("LAST:" + app.entries["daily"]["stamp"], 0, 48)
        if app.wifi.server is not None:
            self.text("AP:" + self.config.AP_NAME, 0, 56)
        else:
            errors = [entry["error"] for entry in app.entries.values() if entry["error"]]
            self.text(errors[0] if errors else "D5: NEXT PAGE", 0, 56)
