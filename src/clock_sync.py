"""NTP clock with explicit UTC+8 conversion and sync state."""
import time
import machine
try:
    import usocket as socket
    import ustruct as struct
except ImportError:
    import socket
    import struct


class Clock:
    def __init__(self, host, offset):
        self.host = host
        self.offset = offset
        self.synced = False
        self.last_ok = False
        self.error = "Not synced"

    def sync(self):
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            connection.settimeout(2)
            request = bytearray(48)
            request[0] = 0x23
            connection.sendto(request, socket.getaddrinfo(self.host, 123)[0][-1])
            reply = connection.recv(48)
            if len(reply) != 48 or (reply[0] & 7) not in (4, 5) or reply[1] == 0 or reply[0] >> 6 == 3:
                raise ValueError("Invalid NTP reply")
            seconds = struct.unpack("!I", reply[40:44])[0]
            epoch = 3155673600 if time.gmtime(0)[0] == 2000 else 2208988800
            utc = time.gmtime(seconds - epoch)
            if utc[0] < 2024:
                raise ValueError("Invalid NTP time")
            machine.RTC().datetime((utc[0], utc[1], utc[2], utc[6], utc[3], utc[4], utc[5], 0))
            self.synced = True
            self.last_ok = True
            self.error = ""
        except Exception as error:
            self.last_ok = False
            self.error = str(error)
            print("NTP:", self.error)
        finally:
            connection.close()
        return self.last_ok

    def local(self):
        return time.gmtime(time.time() + self.offset) if self.synced else None

    def stamp(self):
        value = self.local()
        if value is None:
            return "--:--:--"
        return "%02d:%02d:%02d" % (value[3], value[4], value[5])

    def status(self, online):
        if not self.synced:
            return "NTP:WAIT" if online else "NTP:NONE"
        if not online:
            return "NTP:HOLD"
        return "NTP:OK" if self.last_ok else "NTP:RETRY"
