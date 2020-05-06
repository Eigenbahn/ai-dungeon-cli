#!/usr/bin/env python3

import os
import sys
import requests
import textwrap
import shutil
import yaml
import random

from abc import ABC, abstractmethod

from typing import Callable, Dict

from time import sleep
from random import randint

# This changes the builtin input()
try:
    import readline
except ImportError:
    import pyreadline as readline

from pprint import pprint


# -------------------------------------------------------------------------
# CONF

DEBUG = False

# -------------------------------------------------------------------------
# EXCEPTIONS

class FailedConfiguration(Exception):
    """raise this when the yaml configuration phase failed"""

    def __init__(self, message):
        self.message = message

# Quit Session exception for easier error and exiting handling
class QuitSession(Exception):
    """raise this when the user typed /quit in order to leave the session"""


# -------------------------------------------------------------------------
# UTILS: DICT

def exists(cfg: Dict[str, str], key: str) -> str:
    return key in cfg and cfg[key]


# -------------------------------------------------------------------------
# UTILS: TERMINAL

class UserIo(ABC):
    def handle_user_input(self, prompt: str = '') -> str:
        pass

    def handle_basic_output(self, text: str):
        pass

    def handle_story_output(self, text: str):
        self.handle_basic_output(text)


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
            filename += "/opening-ascii.txt"
        else:
            filename += "/opening-utf8.txt"

        with open(filename, "r", encoding="utf8") as splash_image:
            print(splash_image.read())

    def clear(self):
        if os.name == "nt":
            _ = os.system("cls")
        else:
            _ = os.system("clear")


class TermIoSlowStory(TermIo):
    def __init__(self):
        sys.stdout = Unbuffered(sys.stdout)

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


# -------------------------------------------------------------------------
# CONF

class Config:
    def __init__(self):
        self.prompt: str = "> "
        self.slow_typing_effect: str = "> "

        self.user_name: str = None
        self.auth_token: str = None
        self.email: str = None
        self.password: str = None

    @staticmethod
    def loaded_from_file():
        conf = Config()
        conf.load_from_file()
        return conf

    def load_from_file(self):
        cfg_file = "/config.yml"
        cfg_file_paths = [
            os.path.dirname(os.path.realpath(__file__)) + cfg_file,
            os.path.expanduser("~") + "/.config/ai-dungeon-cli" + cfg_file,
        ]

        did_read_cfg_file = False

        for file in cfg_file_paths:
            try:
                with open(file, "r") as cfg_raw:
                    cfg = yaml.load(cfg_raw, Loader=yaml.FullLoader)
                    did_read_cfg_file = True
            except IOError:
                pass

        if not did_read_cfg_file:
            raise FailedConfiguration("Missing config file at " \
                                      + ", ".join(cfg_file_paths))

        if (not exists(cfg, "auth_token")) and (
                not (exists(cfg, "email")) and not (exists(cfg, "password"))
        ):
            raise FailedConfiguration("Missing or empty authentication configuration. "
            "Please register a token ('auth_token' key) or credentials ('email' / 'password')")

        if exists(cfg, "slow_typing_effect"):
            self.slow_typing_effect = cfg["slow_typing_effect"]
        if exists(cfg, "prompt"):
            self.prompt = cfg["prompt"]
        if exists(cfg, "auth_token"):
            self.auth_token = cfg["auth_token"]
        if exists(cfg, "email"):
            self.email = cfg["email"]
        if exists(cfg, "password"):
            self.password = cfg["password"]
            self.user_name = "John"
        if exists(cfg, "user_name"):
            self.user_name = cfg["user_name"]


# -------------------------------------------------------------------------
# GAME LOGIC

class AbstractAiDungeon(ABC):
    def __init__(self, conf: Config, user_io: UserIo):
        self.stop_session: bool = False
        self.user_id: str = None
        self.session_id: str = None
        self.public_id: str = None
        self.story_configuration: Dict[str, str] = {}
        self.session: requests.Session = requests.Session()

        self.conf = conf
        self.user_io = user_io

    def update_session_auth(self):
        self.session.headers.update({"X-Access-Token": self.conf.auth_token})

    def get_auth_token(self) -> str:
        return self.conf.auth_token

    def login(self):
        pass

    def choose_selection(self, allowed_values: Dict[str, str], k_or_v='v') -> str:

        if k_or_v == 'k':
            allowed_values = {v: k for k, v in allowed_values.items()}

        while True:
            choice = self.user_io.handle_user_input()
            choice = choice.strip()

            if choice == "/quit":
                raise QuitSession("/quit")

            elif choice in allowed_values.keys():
                return allowed_values[choice]
            elif choice in allowed_values.values():
                    return choice
            else:
                self.user_io.handle_basic_output("Please enter a valid selection.")
                continue


    def choose_config(self):
        pass

    # Initialize story
    def init_story(self):
        pass

    def resume_story(self, session_id: str):
        pass

    # Function for when the input typed was ordinary
    def process_regular_action(self, user_input: str):
        pass

    # Function for when /remember is typed
    def process_remember_action(self, user_input: str):
        pass

    # Function that is called each iteration to process user inputs
    def process_next_action(self):
        user_input = self.user_io.handle_user_input()

        if user_input == "/quit":
            self.stop_session = True

        else:
            if user_input.startswith("/remember"):
                self.process_remember_action(user_input[len("/remember "):])
            else:
                self.process_regular_action(user_input)

    def start_game(self):
        # Run until /quit is received inside the process_next_action func
        while not self.stop_session:
            self.process_next_action()


## --------------------------------

class AiDungeonV2(AbstractAiDungeon):
    def __init__(self, conf: Config, user_io: UserIo, api_dn='api.aidungeon.io', scenario_id=362833):
        self.scenario_id = scenario_id
        self.api_dn = api_dn
        self.story_pitch: str = None
        super().__init__(conf, user_io)

    def login(self):
        # TODO: use newer API URL
        request = self.session.post(
            # "https://" + self.api_dn + "/users",
            "https://api.aidungeon.io/users",
            json={"email": self.conf.email, "password": self.conf.password},
        )

        if request.status_code != requests.codes.ok:
            raise FailedConfiguration("Failed to log in using provided credentials. Check your config.")

        self.conf.auth_token = request.json()["accessToken"]

    def make_custom_config(self, scenario):
        self.user_io.handle_basic_output(
        "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
        "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
        "the kingdom. You enter the forest searching for the dragon and see'"
        )
        context = self.user_io.handle_user_input()

        self.story_configuration = scenario
        self.story_pitch = context


    def choose_config(self):
        # Get the configuration for this session
        r = self.session.get("https://" + self.api_dn + "/scenario/" + str(self.scenario_id) + "/options")
        r.raise_for_status()
        response = r.json()
        if DEBUG:
            pprint(response)

        print("Pick a setting...\n")

        mode_select_dict = {}
        for i, opts in enumerate(response, start=1):
            mode = opts['adventure']['title']
            print(str(i) + ") " + mode)
            mode_select_dict[str(i)] = mode
            mode_select_dict['0'] = '0' # secret mode
        selected_mode_i = self.choose_selection(mode_select_dict, 'k')
        selected_mode = mode_select_dict[selected_mode_i]
        selected_mode_opts = response[int(selected_mode_i) - 1]
        selected_mode_scenario_id = selected_mode_opts['adventure']['id']

        # If the custom option was selected load the custom configuration and don't continue this configuration
        if selected_mode == "custom":
            # NB: could have used 'adventure' instead of 'scenario'
            self.make_custom_config(selected_mode_opts['scenario'])
        elif selected_mode == "madlib":
            print('Not yet supported, sorry')
            exit(3)

        elif selected_mode == "archive":
            print('Not yet supported, sorry')
            exit(3)

            print(selected_mode_opts['scenario']['prompt'])
            print()
            rq = {
                "operationName": None,
                "variables": {
                    "id": selected_mode_opts['scenario']['id']
                },
                "query": "query ($id: String) {\n  user {\n    id\n    verifiedAt\n    gameSettings {\n      id\n      textSpeed\n      textColor\n      textSize\n      textFont\n      __typename\n    }\n    __typename\n  }\n  scenario(id: $id) {\n    id\n    title\n    description\n    prompt\n    memory\n    tags\n    nsfw\n    published\n    options {\n      id\n      title\n      __typename\n    }\n    __typename\n  }\n}\n"
            }
            if DEBUG:
                pprint(rq)
            r = self.session.post("https://" + self.api_dn + "/graphql", json=rq)
            r.raise_for_status()
            settings_response = r.json()
            settings = settings_response['data']['scenario']['options']
            if DEBUG:
                pprint(settings)
            setting_select_dict = {}
            for i, opts in enumerate(settings, start=1):
                setting = opts['title']
                print(str(i) + ") " + setting)
                setting_select_dict[str(i)] = setting
            selected_setting_i = self.choose_selection(setting_select_dict, 'k')
            selected_setting = setting_select_dict[selected_setting_i]
            selected_setting_opts = settings[int(selected_setting_i) - 1]

            rq = {
                "operationName": None,
                "variables": {
                    "id": selected_setting_opts['id']
                },
                "query": "query ($id: String) {\n  user {\n    id\n    verifiedAt\n    gameSettings {\n      id\n      textSpeed\n      textColor\n      textSize\n      textFont\n      __typename\n    }\n    __typename\n  }\n  scenario(id: $id) {\n    id\n    title\n    description\n    prompt\n    memory\n    tags\n    nsfw\n    published\n    options {\n      id\n      title\n      __typename\n    }\n    __typename\n  }\n}\n"
            }
            if DEBUG:
                pprint(rq)
            r = self.session.post("https://" + self.api_dn + "/graphql", json=rq)
            r.raise_for_status()
            characters_response = r.json()
            characters = characters_response['data']['scenario']['options']
            if DEBUG:
                pprint(settings)
            character_select_dict = {}
            for i, opts in enumerate(characters, start=1):
                character = opts['title']
                print(str(i) + ") " + character)
                character_select_dict[str(i)] = character
            selected_character_i = self.choose_selection(character_select_dict, 'k')
            selected_character = character_select_dict[selected_character_i]
            selected_character_opts = characters[int(selected_character_i) - 1]

            # {"operationName":null,"variables":{"id":"387253"},"query":"query ($id: String) {\n  user {\n    id\n    verifiedAt\n    gameSettings {\n      id\n      textSpeed\n      textColor\n      textSize\n      textFont\n      __typename\n    }\n    __typename\n  }\n  scenario(id: $id) {\n    id\n    title\n    description\n    prompt\n    memory\n    tags\n    nsfw\n    published\n    options {\n      id\n      title\n      __typename\n    }\n    __typename\n  }\n}\n"}

        else:
            print("Select a character...\n")

            r = self.session.get("https://" + self.api_dn + "/scenario/" + str(selected_mode_scenario_id) + "/options")
            r.raise_for_status()
            character_select_response = r.json()

            character_select_dict = {}
            for i, opts in enumerate(
                    character_select_response, start=1
            ):
                character = opts['adventure']['title']
                print(str(i) + ") " + character)
                character_select_dict[str(i)] = character
            selected_character_i = self.choose_selection(character_select_dict, 'k')
            selected_character = character_select_dict[selected_character_i]
            selected_opts = character_select_response[int(selected_character_i) - 1]['adventure']
            selected_prompt = selected_opts['content']
            selected_music_theme = selected_opts['musicTheme']

            print("Enter your character's name...\n")

            character_name = self.user_io.handle_user_input()

            if character_name == "/quit":
                raise QuitSession("/quit")

            self.story_configuration = {
                "title": selected_character,
                "musicTheme": selected_music_theme,
                "platform":"web"
            }
            self.story_pitch = selected_prompt.replace('${character.name}', character_name)

    # Initialize story
    def init_story(self):
        print("Generating story... Please wait...\n")

        r = self.session.post(
            "https://" + self.api_dn + "/user/adventure/", json=self.story_configuration
        )
        r.raise_for_status()
        session_response = r.json()
        self.user_id = session_response['userId']
        self.session_id = session_response['id']
        self.public_id = session_response["publicId"]

        story_init_payload = {
            "input": self.story_pitch,
            "newFormatting": True,
            "platform": "web"
        }
        r = self.session.post(
            "https://" + self.api_dn + "/user/adventure/" + str(self.session_id) + "/action/progress", json=story_init_payload
        )
        r.raise_for_status()
        if r.text != 'OK':
            # TODO: handle this
            pass
        r = self.session.get("https://" + self.api_dn + "/user/adventure/" + str(self.session_id))
        r.raise_for_status()
        story_response = r.json()
        story_elem = story_response['history'][0]
        story_pitch = story_elem['input'] + story_elem['output']
        self.user_io.handle_story_output(story_pitch)


    def find_action_type(self, user_input: str):
        user_input = user_input.strip()
        action = 'Do'
        if user_input.lower().startswith('/do '):
            user_input = user_input[len('/do '):]
            action = 'Do'
        if user_input.lower().startswith('/say '):
            user_input = user_input[len('/say '):]
            action = 'Say'
        if user_input.lower().startswith('/story '):
            user_input = user_input[len('/story '):]
            action = 'Story'
        elif user_input.lower().startswith('you say "') and user_input[-1] == '"':
            user_input = user_input[len('you say "'):-1]
            action = 'Say'
        elif user_input[0] == '"' and user_input[-1] == '"':
            user_input = user_input[1:-1]
            action = 'Say'
        return (action, user_input)


    # Function for when the input typed was ordinary
    def process_regular_action(self, user_input: str):

        (action, user_input) = self.find_action_type(user_input)

        rq = {
            "input": user_input,
            "inputType": action,
            "newFormatting": True,
            "platform": "web"
        }
        if DEBUG:
            pprint(rq)
        r = self.session.post(
            "https://" + self.api_dn + "/user/adventure/" + str(self.session_id) + "/action/progress",
            json=rq,
        )
        r.raise_for_status()
        if r.text != 'OK':
            # TODO: handle this
            pass
        r = self.session.get("https://" + self.api_dn + "/user/adventure/" + str(self.session_id))
        r.raise_for_status()
        story_response = r.json()
        story_elem = story_response['history'][-1]
        if DEBUG:
            pprint(story_elem)
        story_pitch = story_elem['output']
        self.user_io.handle_story_output(story_pitch)

    def process_remember_action(self, user_input: str):
        rq = {
            "input": user_input,
            "platform": "web"
        }
        if DEBUG:
            pprint(rq)
        r = self.session.post(
            "https://" + self.api_dn + "/user/adventure/" + str(self.session_id) + "/action/remember",
                json=rq,
            )
        r.raise_for_status()
        if r.text != 'OK':
            # TODO: handle this
            pass

    def process_next_action(self):
        user_input = self.user_io.handle_user_input()

        if user_input == "/quit":
            self.stop_session = True

        else:
            if user_input.startswith("/remember"):
                # pass
                self.process_remember_action(user_input[len("/remember "):])
            else:
                self.process_regular_action(user_input)


# -------------------------------------------------------------------------
# MAIN

def main():

    try:
        # Initialize the configuration from config file
        conf = Config.loaded_from_file()

        # Initialize the terminal I/O class
        if conf.slow_typing_effect:
            term_io = TermIo(conf.prompt)
        else:
            term_io = TermIoSlowStory(conf.prompt)

        # Initialize the AiDungeon class with the given auth_token and prompt
        # ai_dungeon = AiDungeon(conf, term_io)
        ai_dungeon = AiDungeonV2(conf, term_io, api_dn='ai-dungeon-api.herokuapp.com')
        # ai_dungeon = AiDungeonV2(conf, term_io)

        # Login if necessary
        if not ai_dungeon.get_auth_token():
            ai_dungeon.login()

        # Update the session authentication token
        ai_dungeon.update_session_auth()

        # Clears the console
        term_io.clear()

        # Displays the splash image accordingly
        if term_io.get_width() >= 80:
            term_io.display_splash()

        # Loads the current session configuration
        ai_dungeon.choose_config()

        # Initializes the story
        ai_dungeon.init_story()

        # Starts the game
        ai_dungeon.start_game()

    except FailedConfiguration as e:
        # NB: No UserIo initialized at this level
        # hence we fallback to a classic `print`
        print(e.message)
        exit(1)

    except QuitSession:
        term_io.handle_basic_output("Bye Bye!")

    except KeyboardInterrupt:
        term_io.handle_basic_output("Received Keyboard Interrupt. Bye Bye...")

    except requests.exceptions.TooManyRedirects:
        term_io.handle_basic_output("Exceded max allowed number of HTTP redirects, API backend has probably changed")
        exit(1)

    except requests.exceptions.HTTPError as err:
        term_io.handle_basic_output("Unexpected response from API backend:")
        term_io.handle_basic_output(err)
        exit(1)

    except ConnectionError:
        term_io.handle_basic_output("Lost connection to the Ai Dungeon servers")
        exit(1)

    except requests.exceptions.RequestException as err:
        term_io.handle_basic_output("Totally unexpected exception:")
        term_io.handle_basic_output(err)
        exit(1)


if __name__ == "__main__":
    main()
