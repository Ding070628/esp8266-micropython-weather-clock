"""Upload with its sibling modules; MicroPython runs main.py on reset."""
import gc
import time
import machine
import dht
import config
from ssd1306 import SSD1306_I2C
from netconfig import Wifi
from clock_sync import Clock
from weather import Weather
from display import Display


def due(now, deadline):
    return time.ticks_diff(now, deadline) >= 0


class App:
    def __init__(self):
        self.page = 0
        self.button = machine.Pin(config.BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.button_reading = self.button.value()
        self.button_stable = self.button_reading
        self.button_changed = time.ticks_ms()
        self.sensor = dht.DHT11(machine.Pin(config.DHT_PIN))
        self.indoor = None
        self.dht_ok = False
        self.clock = Clock(config.NTP_HOST, config.UTC_OFFSET)
        self.weather = Weather(config.SENIVERSE_KEY, config.WEATHER_LOCATION)
        self.entries = {}
        now = time.ticks_ms()
        for name in ("now", "daily"):
            self.entries[name] = {"data": None, "ok": None, "error": "", "stamp": "--:--:--",
                                  "last_success": now, "next": now}
        self.next_ntp = now
        self.next_dht = time.ticks_add(now, config.DHT_INTERVAL)
        self.next_draw = now
        self.was_online = False
        i2c = machine.I2C(scl=machine.Pin(config.OLED_SCL), sda=machine.Pin(config.OLED_SDA), freq=100000)
        self.display = None
        if config.OLED_ADDRESS in i2c.scan():
            oled = SSD1306_I2C(128, 64, i2c, config.OLED_ADDRESS, config.OLED_ROTATE_180)
            self.display = Display(oled, config)
            oled.text("Weather Clock", 0, 0)
            oled.text("Starting WiFi...", 0, 16)
            oled.show()
        else:
            print("OLED not found. Check D1/D2, address and power.")
        self.wifi = Wifi(config)
        print("Weather Clock ready. D5/GPIO14 switches 3 pages.")

    def handle_button(self):
        reading = self.button.value()
        now = time.ticks_ms()
        if reading != self.button_reading:
            self.button_reading = reading
            self.button_changed = now
        if time.ticks_diff(now, self.button_changed) >= 40 and reading != self.button_stable:
            self.button_stable = reading
            if reading == config.BUTTON_ACTIVE_LEVEL:
                self.page = (self.page + 1) % 3
                self.next_draw = now

    def read_indoor(self):
        try:
            self.sensor.measure()
            self.indoor = (self.sensor.temperature(), self.sensor.humidity())
            self.dht_ok = True
        except (OSError, ValueError) as error:
            self.dht_ok = False
            print("DHT11:", error)
        self.next_dht = time.ticks_add(time.ticks_ms(), config.DHT_INTERVAL)

    def refresh(self, name):
        entry = self.entries[name]
        gc.collect()
        try:
            # Commit only after all required JSON fields have been validated.
            result = self.weather.now() if name == "now" else self.weather.daily()
            entry["data"] = result
            entry["ok"] = True
            entry["error"] = ""
            entry["last_success"] = time.ticks_ms()
            stamp = self.clock.stamp()
            if stamp == "--:--:--":
                stamp = "NO NTP"
            entry["stamp"] = stamp
            interval = config.WEATHER_INTERVAL
            print("Weather", name, "updated at", stamp)
        except Exception as error:
            entry["ok"] = False
            entry["error"] = str(error)
            interval = config.WEATHER_RETRY
            print("Weather", name, "failed:", error)
        entry["next"] = time.ticks_add(time.ticks_ms(), interval)
        gc.collect()

    def run(self):
        while True:
            self.handle_button()
            self.wifi.poll()
            now = time.ticks_ms()
            online = self.wifi.online()
            if online and not self.was_online:
                # Refresh both endpoints immediately when Wi-Fi comes back.
                self.next_ntp = now
                for entry in self.entries.values():
                    entry["next"] = now
            self.was_online = online
            if due(now, self.next_dht):
                self.read_indoor()
            if self.display is not None and due(now, self.next_draw):
                try:
                    self.display.draw(self)
                except OSError as error:
                    print("OLED:", error)
                self.next_draw = time.ticks_add(time.ticks_ms(), 200)
            # One network task per loop; requests are bounded by socket timeouts.
            if online:
                if due(now, self.next_ntp):
                    ok = self.clock.sync()
                    self.next_ntp = time.ticks_add(time.ticks_ms(), config.NTP_INTERVAL if ok else config.NTP_RETRY)
                elif due(now, self.entries["now"]["next"]):
                    self.refresh("now")
                elif due(now, self.entries["daily"]["next"]):
                    self.refresh("daily")
            time.sleep_ms(20)


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
