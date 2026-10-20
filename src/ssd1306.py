"""Small SSD1306 I2C framebuffer driver for ESP8266 MicroPython."""
import framebuf


class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C, rotate=False):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.buffer = bytearray(width * height // 8)
        self.command = bytearray(2)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        commands = (0xAE, 0x20, 0x00, 0x40, 0xA0 if rotate else 0xA1,
                    0xA8, height - 1, 0xC0 if rotate else 0xC8,
                    0xD3, 0x00, 0xDA, 0x12, 0xD5, 0x80, 0xD9, 0xF1,
                    0xDB, 0x30, 0x81, 0xCF, 0xA4, 0xA6, 0x8D, 0x14, 0xAF)
        for command in commands:
            self.write_cmd(command)
        self.fill(0)
        self.show()

    def write_cmd(self, value):
        self.command[0] = 0x80
        self.command[1] = value
        self.i2c.writeto(self.addr, self.command)

    def show(self):
        for command in (0x21, 0, self.width - 1, 0x22, 0, self.height // 8 - 1):
            self.write_cmd(command)
        self.i2c.writeto(self.addr, b"\x40" + self.buffer)
