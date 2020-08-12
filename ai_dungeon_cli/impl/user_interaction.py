import os
from abc import ABC, abstractmethod
import textwrap
import shutil

from time import sleep
from random import randint

# NB: import doesn't appear to be used but in fact overrides definition for
# the input() method
try:
    import readline
except ImportError:
    import pyreadline as readline


# -------------------------------------------------------------------------
# ABSTRACT

class UserIo(ABC):
    def handle_user_input(self, prompt: str = '') -> str:
        pass

    def handle_basic_output(self, text: str):
        pass

    def handle_story_output(self, text: str):
        self.handle_basic_output(text)


# -------------------------------------------------------------------------
# IMPLEM: BASIC

class TermIo(UserIo):
    def __init__(self, prompt: str = ''):
        self.prompt = prompt

    def handle_user_input(self) -> str:
        user_input = input(self.prompt)
        print()
        return user_input

    def handle_basic_output(self, text: str):
        print("\n".join(textwrap.wrap(text, self.get_width())))
        print()

    # def handle_story_output(self, text: str):
    #     self.handle_basic_output(text)

    def get_width(self):
        terminal_size = shutil.get_terminal_size((80, 20))
        return terminal_size.columns

    def display_splash(self):
        filename = os.path.dirname(os.path.realpath(__file__))
        locale = None
        term = None
        if "LC_ALL" in os.environ:
            locale = os.environ["LC_ALL"]
        if "TERM" in os.environ:
            term = os.environ["TERM"]

        if locale == "C" or (term and term.startswith("vt")):
            filename += "/../res/opening-ascii.txt"
        else:
            filename += "/../res/opening-utf8.txt"

        with open(filename, "r", encoding="utf8") as splash_image:
            print(splash_image.read())

    def clear(self):
        if os.name == "nt":
            _ = os.system("cls")
        else:
            _ = os.system("clear")


# -------------------------------------------------------------------------
# IMPLEM: SLOW TYPING EFFECT

class TermIoSlowStory(TermIo):
    def __init__(self, prompt: str = ''):
        sys.stdout = Unbuffered(sys.stdout)
        super().__init__(prompt)

    def handle_story_output(self, text: str):
        for line in textwrap.wrap(text, self.get_width()):
            for letter in line:
                print(letter, end='')
                sleep(randint(2, 10)*0.005)
                print()
                print()


# allow unbuffered output for slow typing effect
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)
