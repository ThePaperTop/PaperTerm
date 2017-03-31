from copy import copy

_alphabet = "abcdefghijklmnopqrstuvwxyz"

control_codes = {'NUL': 0,
                 'BS': 8,
                 'EOT': 4,
                 'CR': 13,
                 'SI': 15,
                 'DC3': 19,
                 'ESC': 27,
                 'SO': 14,
                 'FF': 12,
                 'DC1': 17,
                 'HT': 9,
                 'VT': 11,
                 'SUB': 26,
                 'BEL': 7,
                 'ETX': 3,
                 'CAN': 24,
                 'LF': 10,
                 'ENQ': 5,
                 "DEL": 127}

_key_assoc = {
    "KEY_GRAVE": ord("`"),
    "S-KEY_GRAVE": ord("~"),
    "KEY_SPACE": ord(" "),
    "KEY_MINUS": ord("-"),
    "S-KEY_MINUS": ord("_"),
    "KEY_EQUAL": ord("="),
    "S-KEY_EQUAL": ord("+"),
    "KEY_SEMICOLON": ord(";"),
    "S-KEY_SEMICOLON": ord(":"),
    "KEY_APOSTROPHE": ord("'"),
    "S-KEY_APOSTROPHE": ord('"'),
    "KEY_COMMA": ord(","),
    "S-KEY_COMMA": ord("<"),
    "KEY_DOT": ord("."),
    "S-KEY_DOT": ord(">"),
    "KEY_SLASH": ord("/"),
    "S-KEY_SLASH": ord("?"),
    "KEY_LEFTBRACE": ord("["),
    "S-KEY_LEFTBRACE": ord("{"),
    "KEY_RIGHTBRACE": ord("]"),
    "S-KEY_RIGHTBRACE": ord("}"),
    "KEY_BACKSLASH": ord("\\"),
    "S-KEY_BACKSLASH": ord("|"),
    "KEY_TAB": ord("\t"),
    "KEY_BACKSPACE": control_codes["DEL"],
    "KEY_ESC": control_codes["ESC"],
    "C-KEY_D": control_codes["EOT"],
    "KEY_ENTER": _alphabet.index("m") + 1,
    "KEY_RETURN": control_codes["LF"],
    "C-KEY_SPACE": control_codes["NUL"],
    "C-KEY_LEFTBRACE": control_codes["ESC"],
    "KEY_UP": [27, ord("["), ord("A")],
    "KEY_DOWN": [27, ord("["), ord("B")],
    "KEY_RIGHT": [27, ord("["), ord("C")],
    "KEY_LEFT": [27, ord("["), ord("D")],
    "KEY_PAGEUP": [27, ord("["), ord("V")],
    "KEY_PAGEDOWN": [27, ord("["), ord("U")],
}

for letter in _alphabet:
    _key_assoc["KEY_%s" % letter.upper()] = ord(letter)
    _key_assoc["S-KEY_%s" % letter.upper()] = ord(letter.upper())
    _key_assoc["C-KEY_%s" % letter.upper()] = _alphabet.index(letter) + 1

for number in "0123456789":
    _key_assoc["KEY_%s" % number] = ord(number)

_symbols = ")!@#$%^&*("
for i in range(len(_symbols)):
    _key_assoc["S-KEY_%s" % i] = ord(_symbols[i])

def keycode_to_code(keycode):
    try:
        return _key_assoc[keycode]
    except:
        return None

_buckies = {"KEY_RIGHTALT": "A",
            "KEY_CAPSLOCK": "C", # make caps lock a control key
           "KEY_LEFTALT": "A",
           "KEY_LEFTCTRL": "C",
           "KEY_RIGHTCTRL": "C",
           "KEY_LEFTSHIFT": "S",
           "KEY_RIGHTSHIFT": "S",
           "KEY_LEFTMETA": "M",
           "KEY_RIGHTMETA": "M",
           "KEY_COMPOSE": "P"}

UP=0
DOWN=1
HOLD=2

class KeyHandler(object):    
    def __init__(self, keyreader, receiver):
        self.keyreader = keyreader
        self.receiver = receiver
        self.alt = False
        self.buckies = []
    def bucky_set(self):
        """Return a dash-delimited alphabetized list of unique buckies that
        are currently on (except for ALT, which is handled
        differently), followed by a trailing dash, e.g. "S-M-C-".  If
        no buckies are on, return an empty string.

        """
        if self.buckies:
                return "-".join(sorted(set(self.buckies), reverse=True)) + "-"
        else:
            return ""
        
    def handle_bucky(self, keycode, keystate):

        if keycode in ["KEY_LEFTALT",
                       "KEY_RIGHTALT"]:
            self.alt = keystate in [DOWN, HOLD]
            return True
        
        # if it's not a bucky, get out
        try:
            abbrev = _buckies[keycode]
        except KeyError:
            return False

        # while it's down, keep a record of it
        if keystate == DOWN:
            self.buckies.append(abbrev)
        elif keystate == UP:
            bucky = _buckies[keycode]
            while bucky in self.buckies:
                self.buckies.remove(bucky)

        return True

    def maybe_send_alt(self):
        if self.alt:
            self.receiver(control_codes["ESC"])

    def handle_nonbucky(self, keycode, keystate):
        if keystate in [DOWN, HOLD]:
            alt_code = self.bucky_set() + keycode
            try:
                char = _key_assoc[alt_code]
            except KeyError:
                return False
            self.maybe_send_alt()
            if type(char) == list:
                for c in char:
                    self.receiver(c)
            else:
                self.receiver(char)
            return True
        else:
            return False    

    def handle_key(self, keycode, keystate):
        if self.handle_bucky(keycode, keystate):
            pass
        elif self.handle_nonbucky(keycode, keystate):
            pass
        else:
            if keycode == "KEY_F1":
                exit()
            elif keystate == DOWN:
                print(keycode, self.bucky_set())
    def run(self):
        self.keyreader.event_loop(self.handle_key)

if __name__ == "__main__":
    from key_events import ExclusiveKeyReader
    with ExclusiveKeyReader("/dev/input/event4") as kr:
        kh = KeyHandler(kr, print)
        kh.run()
