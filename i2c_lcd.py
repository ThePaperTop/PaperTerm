import smbus
from time import *

# LCD Address
ADDRESS = 0x3F

# commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00

En = 0b00000100 # Enable bit
Rw = 0b00000010 # Read/Write bit
Rs = 0b00000001 # Register select bit


class I2cDevice(object):
   def __init__(self, addr, port=1):
      self.addr = addr
      self.bus = smbus.SMBus(port)

   # Write a single command
   def write_cmd(self, cmd):
      self.bus.write_byte(self.addr, cmd)

   # Write a command and argument
   def write_cmd_arg(self, cmd, data):
      self.bus.write_byte_data(self.addr, cmd, data)

   # Write a block of data
   def write_block_data(self, cmd, data):
      self.bus.write_block_data(self.addr, cmd, data)

   # Read a single byte
   def read(self):
      return self.bus.read_byte(self.addr)

   # Read
   def read_data(self, cmd):
      return self.bus.read_byte_data(self.addr, cmd)

   # Read a block of data
   def read_block_data(self, cmd):
      return self.bus.read_block_data(self.addr, cmd)



class Lcd(object):
   def __init__(self, address=ADDRESS):
      self.device = I2cDevice(address)

      self.write(0x03)
      self.write(0x03)
      self.write(0x03)
      self.write(0x02)

      self.write(LCD_FUNCTIONSET | LCD_2LINE | LCD_5x8DOTS | LCD_4BITMODE)
      self.write(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
      self.write(LCD_CLEARDISPLAY)
      self.write(LCD_ENTRYMODESET | LCD_ENTRYLEFT)

   def reset(self):
      self.write(0x03)
      self.write(0x03)
      self.write(0x03)
      self.write(0x02)

      self.write(LCD_FUNCTIONSET | LCD_2LINE | LCD_5x8DOTS | LCD_4BITMODE)
      self.write(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
      self.write(LCD_CLEARDISPLAY)
      self.write(LCD_ENTRYMODESET | LCD_ENTRYLEFT)
      
   # clocks EN to latch command
   def strobe(self, data):
      self.device.write_cmd(data | En | LCD_BACKLIGHT)
      self.device.write_cmd(((data & ~En) | LCD_BACKLIGHT))

   def write_four_bits(self, data):
      self.device.write_cmd(data | LCD_BACKLIGHT)
      self.strobe(data)

   # write a command to lcd
   def write(self, cmd, mode=0):
      self.write_four_bits(mode | (cmd & 0xF0))
      self.write_four_bits(mode | ((cmd << 4) & 0xF0))

   # write a character to lcd (or character rom) 0x09: backlight | RS=DR<
   # works!
   def write_char(self, charvalue, mode=1):
      self.write_four_bits(mode | (charvalue & 0xF0))
      self.write_four_bits(mode | ((charvalue << 4) & 0xF0))
  
   # put string function
   def display_string(self, string, line):
      if line == 1:
         self.write(0x80)
      if line == 2:
         self.write(0xC0)
      if line == 3:
         self.write(0x94)
      if line == 4:
         self.write(0xD4)

      for char in string:
         self.write(ord(char), Rs)

   # clear lcd and set to home
   def clear(self):
      self.write(LCD_CLEARDISPLAY)
      self.write(LCD_RETURNHOME)

   # define backlight on/off (lcd.backlight(1); off= lcd.backlight(0)
   def backlight(self, state): # for state, 1 = on, 0 = off
      if state == 1:
         self.device.write_cmd(LCD_BACKLIGHT)
      elif state == 0:
         self.device.write_cmd(LCD_NOBACKLIGHT)

   # add custom characters (0 - 7)
   def load_custom_chars(self, fontdata):
      self.write(0x40);
      for char in fontdata:
         for line in char:
            self.write_char(line)

   def show_cursor(self, line, pos):
      if line == 1:
         pos_new = pos
      elif line == 2:
         pos_new = 0x40 + pos
      elif line == 3:
         pos_new = 0x14 + pos
      elif line == 4:
         pos_new = 0x54 + pos

      self.write(0x80 + pos_new)

      self.write(0x0E)
         
   # define precise positioning (addition from the forum)
   def display_string_pos(self, string, line, pos):
      if line == 1:
         pos_new = pos
      elif line == 2:
         pos_new = 0x40 + pos
      elif line == 3:
         pos_new = 0x14 + pos
      elif line == 4:
         pos_new = 0x54 + pos

      self.write(0x80 + pos_new)

      for char in string:
         self.write(ord(char), Rs)
