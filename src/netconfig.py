"""Cooperative Wi-Fi reconnect and an AP configuration web page."""
import network
import time
try:
    import usocket as socket
    import ujson as json
except ImportError:
    import socket
    import json


def unquote(value):
    value = value.replace("+", " ")
    data = bytearray()
    index = 0
    while index < len(value):
        if value[index] == "%":
            data.append(int(value[index + 1:index + 3], 16))
            index += 3
        else:
            data.extend(value[index].encode("utf-8"))
            index += 1
    return data.decode("utf-8")


class Wifi:
    def __init__(self, config):
        self.config = config
        self.station = network.WLAN(network.STA_IF)
        self.station.active(True)
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(False)
        self.server = None
        self.ssid = config.WIFI_SSID
        self.password = config.WIFI_PASSWORD
        self.last_attempt = time.ticks_ms()
        if not self.ssid:
            try:
                with open("wifi.json") as saved:
                    credentials = json.load(saved)
                self.ssid = credentials["ssid"]
                self.password = credentials["password"]
            except (OSError, ValueError, KeyError):
                pass
        if self.ssid:
            self.connect()
        else:
            self.start_ap()

    def online(self):
        return self.station.isconnected()

    def connect(self):
        self.last_attempt = time.ticks_ms()
        try:
            self.station.disconnect()
            self.station.connect(self.ssid, self.password)
        except OSError as error:
            print("WiFi connect:", error)

    def start_ap(self):
        if self.server is not None:
            return
        self.ap.active(True)
        self.ap.config(essid=self.config.AP_NAME, password=self.config.AP_PASSWORD,
                       authmode=network.AUTH_WPA_WPA2_PSK)
        server = socket.socket()
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", 80))
            server.listen(1)
            server.setblocking(False)
        except Exception:
            server.close()
            raise
        self.server = server
        print("Connect AP:", self.config.AP_NAME, "Open:", self.ap.ifconfig()[0])

    def stop_ap(self):
        if self.server is not None:
            self.server.close()
            self.server = None
        self.ap.active(False)

    def poll(self):
        if self.online():
            if self.server is not None:
                self.stop_ap()
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_attempt) >= self.config.NETWORK_RETRY:
            self.start_ap()
            if self.ssid:
                self.connect()
            else:
                self.last_attempt = now
        if self.server is not None:
            self.serve_one()

    def serve_one(self):
        try:
            client, address = self.server.accept()
        except OSError:
            return
        stream = None
        reconnect = False
        try:
            client.settimeout(2)
            stream = client.makefile("rb", 0)
            request = stream.readline()
            if len(request) > 2048:
                raise ValueError("Request too large")
            parts = request.decode("utf-8").split()
            if len(parts) < 2:
                raise ValueError("Invalid request")
            header_size = len(request)
            while True:
                header = stream.readline()
                header_size += len(header)
                if not header or header in (b"\r\n", b"\n"):
                    break
                if header_size > 4096:
                    raise ValueError("Headers too large")
            target = parts[1]
            message = "Choose your 2.4 GHz Wi-Fi."
            if target.startswith("/save?"):
                values = {}
                for pair in target.split("?", 1)[1].split("&"):
                    key, value = pair.split("=", 1)
                    values[unquote(key)] = unquote(value)
                ssid = values.get("ssid", "").strip()
                password = values.get("password", "")
                if not ssid or len(ssid.encode("utf-8")) > 32:
                    raise ValueError("SSID must be 1-32 bytes")
                if password and not 8 <= len(password.encode("utf-8")) <= 63:
                    raise ValueError("Password must be 8-63 bytes")
                with open("wifi.json", "w") as saved:
                    json.dump({"ssid": ssid, "password": password}, saved)
                self.ssid, self.password = ssid, password
                reconnect = True
                message = "Saved. Connecting... Check the OLED."
            html = ("<!doctype html><html><head><meta name='viewport' content='width=device-width'>"
                    "<title>Weather Clock</title></head><body><h2>Weather Clock Wi-Fi</h2>"
                    "<p>%s</p><form action='/save' method='get'>"
                    "<p>SSID: <input name='ssid' maxlength='32' required></p>"
                    "<p>Password: <input name='password' type='password' maxlength='63'></p>"
                    "<button>Save and connect</button></form></body></html>") % message
            body = html.encode("utf-8")
            response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                        "Content-Length: %d\r\nConnection: close\r\n\r\n") % len(body)
            packet = response.encode() + body
            offset = 0
            while offset < len(packet):
                sent = client.send(packet[offset:])
                if not sent:
                    break
                offset += sent
        except Exception as error:
            print("AP request:", error)
            try:
                client.send(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n"
                            b"Content-Type: text/plain\r\n\r\n"
                            b"Invalid Wi-Fi settings. Check SSID and password, then go back.")
            except OSError:
                pass
        finally:
            if stream is not None:
                stream.close()
            client.close()
        if reconnect:
            self.connect()

    def ip(self):
        if self.online():
            return self.station.ifconfig()[0]
        if self.server is not None:
            return self.ap.ifconfig()[0]
        return "--"
