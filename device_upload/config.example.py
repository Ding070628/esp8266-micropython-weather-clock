# Copy this file to config.py, fill in the values, and upload config.py.
WIFI_SSID = "YOUR_2.4G_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SENIVERSE_KEY = "YOUR_SENIVERSE_PRIVATE_KEY"
WEATHER_LOCATION = "nanjing"  # City pinyin, city ID, or "ip".
CITY_LABEL = ""  # Optional English label when the API city name is non-ASCII.

OLED_SCL = 5  # D1
OLED_SDA = 4  # D2
OLED_ADDRESS = 0x3C
OLED_ROTATE_180 = True
DHT_PIN = 12  # D6
BUTTON_PIN = 14  # D5 / GPIO14
BUTTON_ACTIVE_LEVEL = 1  # Released: 0; pressed: 1 for the tested module.

AP_NAME = "WeatherClock"
AP_PASSWORD = "weather8266"
NTP_HOST = "ntp1.aliyun.com"
UTC_OFFSET = 8 * 3600

WEATHER_INTERVAL = 30 * 60 * 1000
WEATHER_RETRY = 60 * 1000
NTP_INTERVAL = 30 * 60 * 1000
NTP_RETRY = 60 * 1000
NETWORK_RETRY = 15 * 1000
DHT_INTERVAL = 2000
