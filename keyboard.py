import os
import pty
import pyte
from threading import Thread
from epaper import EPaper
import time

from key_events import ExclusiveKeyReader
from keys import KeyHandler

screen = pyte.Screen(34, 18)
stream = pyte.Stream()

stream.attach(screen)

os.environ["COLUMNS"] = "34"
os.environ["LINES"] = "18"

paper = EPaper("/dev/ttyS0", debug=False)

child_pid, fd = pty.fork()

if child_pid == 0:
    os.execlp("/bin/bash", "PaperTerminal", "-i")
else:
    def read_bash():
        while True:
            try:
                out = os.read(fd, 4096)
                stream.feed(out.decode("utf-8"))
            except OSError:
                break

    bash_thread = Thread(target=read_bash)
    bash_thread.daemon = True
    bash_thread.start()

    def displayer():
        prev_screen = ""
        prev_x, prev_y = 100, 100 # impossible!
        while True:
            s = screen.display
            if (("\n".join(s) != prev_screen) or
                (prev_x != screen.cursor.x) or
                (prev_y != screen.cursor.y)):
                
                paper.cls()
                paper.draw_screen(s)
                paper.draw_cursor(screen.cursor.y, screen.cursor.x)
                paper.finalize()
                prev_screen = "\n".join(s)
                prev_x, prev_y = screen.cursor.x, screen.cursor.y
            time.sleep(2)

    display_thread = Thread(target=displayer)
    display_thread.daemon = True
    display_thread.start()
    
    def feed_fn(asc):
        os.write(fd, bytes(chr(asc), "utf-8"))

    with ExclusiveKeyReader("/dev/input/event1") as key_reader:
        key_handler = KeyHandler(key_reader, feed_fn)
        key_handler.run()
