import spidev
from array import *
import RPi.GPIO as GPIO
import time

commands = {
    "reset_data_pointer": [0x20, 0x0D, 0x00],
    "update_display": [0x24, 0x01, 0x00],
    "upload_header": [0x20, 0x01, 0x00, 0x10],
    "upload_image_data": [0x20, 0x01, 0x00, 0xFA],
    "get_device_info": [0x30, 0x01, 0x01, 0x00],
}

class PervasiveDisplay(object):
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        # pin 16: low=busy
        GPIO.setup(16, GPIO.IN)
        GPIO.setup(12, GPIO.OUT)

        # disable and re-enable TCOM
        GPIO.output(12, GPIO.HIGH)
        GPIO.output(12, GPIO.LOW)
        time.sleep(0.1) # wait for initialization

        self.spi = spidev.SpiDev()
        self.spi.open(0,0)
        
        # self.spi.max_speed_hz = 3000000
        self.spi.mode = 0b11
        self.spi.bits_per_word = 8

        self.image_header = [0x3a, 0x01, 0xe0, 0x03,
                             0x20, 0x01, 0x04, 0x00,
                             0x00, 0x00, 0x00, 0x00,
                             0x00, 0x00, 0x00, 0x00]

    def wait_for_ready(self):
        while GPIO.input(16) == GPIO.LOW:
            pass
    
    def send_command(self, cmd, data=list()):
        self.wait_for_ready()
        self.spi.xfer2(commands[cmd] + data)
        self.wait_for_ready()

    def get_response(self, bytes):
        return self.spi.readbytes(bytes)

    def send_image(self, epd_data):
        out = []
        self.send_command("upload_header", self.image_header)
        out.append(self.get_response(2))
        for index in range(0, len(epd_data), 250):
            self.send_command("upload_image_data",
                              epd_data[index:index + 250])
            out.append(self.get_response(5))
        return out

    def write_image(self, epd_data):
        out = bytes(epd_data)
            
        with open("epd_output.epd", "wb") as f:
            f.write(out)

    def update_display(self):
        self.send_command("update_display")
        return self.get_response(2)

    def get_device_info(self):
        self.send_command("get_device_info")

    def reset_data_pointer(self):
        self.send_command("reset_data_pointer")
        return self.get_response(2)
