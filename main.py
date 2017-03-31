import os
import pty
from threading import Thread
from datetime import datetime, timedelta
import time
import pyte

from key_events import ExclusiveKeyReader
from keys import KeyHandler
import pervasive
from pil2epd import convert
from PIL import Image, ImageFont, ImageDraw
from fontlist import FontList

class PaperTerm(ExclusiveKeyReader):
    """Runs an in-memory instance of bash, communicating with an in-memory
    VT102 emulator, whose output is mirrored on an e-paper screen.  If
    debug==True, the responses to serial requests will be waited for
    and printed to the initiating terminal, slowing display
    considerably..

    """
    def __init__(self,
                 keyboard,
                 display_tty,
                 rows=24,
                 cols=80,
                 debug=False,
                 use_lcd=False):
        
        ExclusiveKeyReader.__init__(self, keyboard)
        
        self.cols = cols
        self.rows = rows
        
        # set up an in-memory screen and its communication stream
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.display = pervasive.PervasiveDisplay()
        
        self.debug = debug

        self.use_lcd = use_lcd

        os.environ["COLUMNS"] = "%s" % cols
        os.environ["LINES"] = "%s" % rows

        self.last_keypress = datetime.fromordinal(1)
        
        try:
            fonts = FontList.all().by_partial_name("roboto mono").bold()
            font = [font for font in fonts
                    if font not in fonts.slanted()][0]
        except IndexError:
            raise Exception("You must install the Roboto Mono font.")

        self.font = ImageFont.truetype(font["path"], size=15)

    def _ready_for_screen_update(self):
        """Determine if the user has stopped typing for a bit; if so, say yes
        to a screen redraw."""
        if (datetime.now() - self.last_keypress).total_seconds() > 0.5:
            return True
        else:
            return False

    def _read_bash(self):
        """To be run in a separate thread, reading from the Bash process and
        feeding the VT102 emulator.

        """
        while True:
            try:
                out = os.read(self.bash_fd, 4096)
                try:
                    self.stream.feed(out.decode("utf-8"))
                except UnicodeDecodeError:
                    pass  # at least don't die if there's weird input
            except OSError:
                break # if there's nothing to read, kill the reader
                      # thread

    def _write_lcd(self):
        from i2c_lcd import Lcd

        self.lcd = Lcd()
        # previous values, allowing us to wait for change before
        # displaying
        prev_screen = ""
        prev_x, prev_y = 100, 100 # off the screen
        last_draw_time = datetime.now()

        draw_num = 0

        while True:
            s = self.screen.display
            scrn_x, scrn_y = self.screen.cursor.x, self.screen.cursor.y

            s = ["".join([c for c in line
                          if ord(c) < 127])
                 for line in s]
            
            # draw to LCD
            lcd_width = 40

            start_x, end_x = scrn_x - 20, scrn_x + 20
            if start_x < 0:
                start_x, end_x = 0, end_x - start_x
            elif end_x > self.cols:
                start_x, end_x = self.cols - lcd_width, self.cols

            try:
                if scrn_y == 0:
                    l1, l2 = (s[scrn_y][start_x:end_x],
                              s[scrn_y + 1][start_x:end_x])
                else:
                    l1, l2 = (s[scrn_y - 1][start_x:end_x],
                              s[scrn_y][start_x:end_x])
                    
            except IndexError:
                pass

            # if the display or cursor position has changed, redraw
            if (l1 + "\n" + l2 != prev_screen or
                (prev_x != scrn_x) or
                (prev_y != scrn_y)):
                
                time.sleep(0.1)
                
                self.lcd.backlight(1)
                
                self.lcd.display_string(l1.ljust(lcd_width), 1)
                self.lcd.display_string(l2.ljust(lcd_width), 2)
                
                if scrn_y == 0:
                    self.lcd.show_cursor(1, scrn_x - start_x)
                else:
                    self.lcd.show_cursor(2, scrn_x - start_x)
                    
                time.sleep(0.1)
                
                prev_screen = l1 + "\n" + l2
                prev_x = scrn_x
                prev_y = scrn_y
                last_draw_time = datetime.now()
            elif (datetime.now() - last_draw_time).seconds > 5:
                self.lcd.backlight(0)
    
    def _write_display(self):
        """To be run in a separate thread, reading from the VT102 emulator and
        feeding the serial e-paper display.

        """

        # previous values, allowing us to wait for change before
        # displaying
        prev_screen = ""
        prev_x, prev_y = 100, 100 # off the screen

        draw_num = 0

        while True:
            s = self.screen.display
            scrn_x, scrn_y = self.screen.cursor.x, self.screen.cursor.y
            
            if (("\n".join(s) != prev_screen) or
                (prev_x != scrn_x) or
                (prev_y != scrn_y)) and self._ready_for_screen_update():

                image = Image.new("1", (800, 480), 1)


                drawer = ImageDraw.Draw(image)
                
                for row_ind in range(len(s)):
                    drawer.text((14, 18 * row_ind), s[row_ind], font=self.font)

                char_width = 9.0
                drawer.rectangle([int(scrn_x * char_width + 14), scrn_y * 18,
                                  int(scrn_x * char_width + 14 + char_width), scrn_y * 18 + 18],
                                 outline=0)
                image = image.rotate(270)
                
                epd_data = convert(image)
                self.display.reset_data_pointer()
                self.display.send_image(epd_data)
                self.display.update_display()
                
                prev_screen = "\n".join(s)
                prev_x, prev_y = (scrn_x,
                                  scrn_y)
                

    def _subterm(self, rows, columns, rows_above_cursor=1, columns_before_cursor=5):
        screen = self.screen.display
        x, y = (self.screen.cursor.x,
                self.screen.cursor.y)
        subscreen = screen[
            self.screen.cursor.y - rows_above_cursor:
            self.screen.cursor.y - rows_above_cursor + rows]
        for row_index in range(len(subscreen)):
            subscreen[row_index] = subscreen[row_index][
                self.screen.cursor.x - columns_before_cursor,
                self.screen.cursor.x - columns_before_cursor, + columns]

        return subscreen
            
                           
            
    def start(self):
        """Start driving the terminal emulator and display."""

        # bash will run in a separate thread
        child_pid, self.bash_fd = pty.fork()

        if child_pid == 0:
            #if we're in the child thread, start bash
            os.execlp("/bin/bash", "PaperTerm", "-i")
            
        else:

            # otherwise, start reading from bash,
            self.bash_thread = Thread(target=self._read_bash)
            self.bash_thread.daemon = True # die if main thread ends
            self.bash_thread.start()

            if self.use_lcd:
                # writing to the lcd
                self.lcd_thread = Thread(target=self._write_lcd)
                self.lcd_thread.daemon = True # die with main thread
                self.lcd_thread.start()

            # writing to the display, 
            self.display_thread = Thread(target=self._write_display)
            self.display_thread.daemon = True # die with main thread
            self.display_thread.start()

            # and reading from the keyboard
            def feed_fn(asc):
                os.write(self.bash_fd, bytes(chr(asc), "utf-8"))
                self.last_keypress = datetime.now()

            key_handler = KeyHandler(self, feed_fn)
            key_handler.run() # loops until program end

    def __exit__(self, *args, **kwargs):
        if self.use_lcd:
            self.lcd.clear()
            self.lcd.backlight(0)
            
if __name__ == "__main__":
    with PaperTerm("/dev/input/event0", "/dev/ttyS0", use_lcd=True) as term:
        term.start()
