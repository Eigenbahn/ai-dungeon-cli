#!/usr/bin/env python3

import os
import requests
import textwrap
import shutil
import yaml

from typing import Callable, Dict

# This changes the builtin input()
try:
    import readline
except ImportError:
    import pyreadline as readline

# from pprint import pprint


# -------------------------------------------------------------------------
# EXCEPTIONS

class FailedConfiguration(Exception):
    """raise this when the yaml configuration phase failed"""


# Quit Session exception for easier error and exiting handling
class QuitSession(Exception):
    """raise this when the user typed /quit in order to leave the session"""


# -------------------------------------------------------------------------
# UTILS: DICT

def exists(cfg: Dict[str, str], key: str) -> str:
    return key in cfg and cfg[key]


# -------------------------------------------------------------------------
# UTILS: TERMINAL

terminal_size = shutil.get_terminal_size((80, 20))
terminal_width = terminal_size.columns


def clear_console():
    if os.name == "nt":
        _ = os.system("cls")
    else:
        _ = os.system("clear")


def display_splash():
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


def set_input_handler(method: Callable[[str], str]):
    global input_handler
    input_handler = method


def set_print_handler(method: Callable[[str], None]):
    global print_handler
    print_handler = method


def get_user_input_term(prompt: str = '') -> str:
    user_input = input(prompt)
    print()
    return user_input


def print_output_term(text: str):
    print("\n".join(textwrap.wrap(text, terminal_width)))
    print()


input_handler = get_user_input_term
print_handler = print_output_term


# -------------------------------------------------------------------------
# GAME LOGIC

class AiDungeon:
    def __init__(self):

        # Variables initialization
        self.prompt: str = "> "
        self.auth_token: str = None
        self.email: str = None
        self.password: str = None
        self.prompt_iteration: int = None
        self.stop_session: bool = False
        self.user_id: str = None
        self.session_id: str = None
        self.public_id: str = None
        self.story_configuration: Dict[str, str] = {}
        self.session: requests.Session = requests.Session()

        # Start class configuration
        self.load_configuration_file()

    def update_session_auth(self):
        self.session.headers.update({"X-Access-Token": self.auth_token})

    def load_configuration_file(self):
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
            print("Missing config file at ", end="")
            print(*cfg_file_paths, sep=", ")
            raise FailedConfiguration

        if (not exists(cfg, "auth_token")) and (
            not (exists(cfg, "email")) and not (exists(cfg, "password"))
        ):
            print_handler(
                "Missing or empty authentication configuration. "
                "Please register a token ('auth_token' key) or credentials ('email' / 'password')"
            )
            raise FailedConfiguration

        if exists(cfg, "prompt"):
            self.prompt = cfg["prompt"]
        if exists(cfg, "auth_token"):
            self.auth_token = cfg["auth_token"]
        if exists(cfg, "email"):
            self.email = cfg["email"]
        if exists(cfg, "password"):
            self.password = cfg["password"]

    def get_auth_token(self) -> str:
        return self.auth_token

    def login(self):
        request = self.session.post(
            "https://api.aidungeon.io/users",
            json={"email": self.email, "password": self.password},
        )

        if request.status_code != requests.codes.ok:
            print_handler(
                "Failed to log in using provided credentials. Check your config."
            )
            raise FailedConfiguration

        self.auth_token = request.json()["accessToken"]

    def choose_selection(self, allowed_values: Dict[str, str]) -> str:
        while True:
            choice = input_handler(self.prompt)

            choice = choice.strip()

            if choice == "/quit":
                raise QuitSession("/quit")

            elif choice in allowed_values.keys():
                choice = allowed_values[choice]
            elif choice in allowed_values.values():
                pass
            else:
                print_handler("Please enter a valid selection.")
                continue
            break
        return choice

    def make_custom_config(self):
        print_handler(
            "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
            "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
            "the kingdom. You enter the forest searching for the dragon and see'"
        )

        context = input_handler(self.prompt)

        if context == "/quit":
            raise QuitSession("/quit")

        self.story_configuration = {
            "storyMode": "custom",
            "characterType": None,
            "name": None,
            "customPrompt": context,
            "promptId": None,
        }

    def choose_config(self):
        # Get the configuration for this session
        response = self.session.get("https://api.aidungeon.io/sessions/*/config").json()

        print("Pick a setting...\n")

        mode_select_dict = {}
        for i, (mode, opts) in enumerate(response["modes"].items(), start=1):
            print(str(i) + ") " + mode)
            mode_select_dict[str(i)] = mode
        selected_mode = self.choose_selection(mode_select_dict)

        if selected_mode == "/quit":
            raise QuitSession("/quit")

        # If the custom option was selected load the custom configuration and don't continue this configuration
        if selected_mode == "custom":
            self.make_custom_config()

        else:
            print("Select a character...\n")

            character_select_dict = {}
            for i, (character, opts) in enumerate(
                response["modes"][selected_mode]["characters"].items(), start=1
            ):
                print(str(i) + ") " + character)
                character_select_dict[str(i)] = character
            selected_character = self.choose_selection(character_select_dict)

            if selected_character == "/quit":
                raise QuitSession("/quit")

            print("Enter your character's name...\n")

            character_name = input_handler(self.prompt)

            if character_name == "/quit":
                raise QuitSession("/quit")

            self.story_configuration = {
                "storyMode": selected_mode,
                "characterType": selected_character,
                "name": character_name,
                "customPrompt": None,
                "promptId": None,
            }

    # Initialize story
    def init_story(self):
        print("Generating story... Please wait...\n")

        story_response = self.session.post(
            "https://api.aidungeon.io/sessions", json=self.story_configuration
        ).json()

        self.prompt_iteration = 2
        self.user_id = story_response["userId"]
        self.session_id = story_response["id"]
        self.public_id = story_response["publicId"]

        story_pitch = story_response["story"][0]["value"]

        print_handler(story_pitch)

    # Function for when the input typed was ordinary
    def process_regular_action(self, user_input: str):
        action_res = self.session.post(
            "https://api.aidungeon.io/sessions/" + str(self.session_id) + "/inputs",
            json={"text": user_input},
        ).json()
        action_res_str = action_res[self.prompt_iteration]["value"]
        print_handler(action_res_str)

    # Function for when /remember is typed
    def process_remember_action(self, user_input: str):
        self.session.patch(
            "https://api.aidungeon.io/sessions/" + str(self.session_id),
            json={"context": user_input},
        )

    # Function that is called each iteration to process user inputs
    def process_next_action(self):
        user_input = input_handler(self.prompt)

        if user_input == "/quit":
            self.stop_session = True

        else:
            if user_input.startswith("/remember"):
                self.process_remember_action(user_input[len("/remember "):])
            else:
                self.process_regular_action(user_input)
                self.prompt_iteration += 2

    def start_game(self):
        # Run until /quit is received inside the process_next_action func
        while not self.stop_session:
            self.process_next_action()


# -------------------------------------------------------------------------
# MAIN

def main():

    try:
        # Initialize the AiDungeon class with the given auth_token and prompt
        ai_dungeon = AiDungeon()

        # Login if necessary
        if not ai_dungeon.get_auth_token():
            ai_dungeon.login()

        # Update the session authentication token
        ai_dungeon.update_session_auth()

        # Clears the console
        clear_console()

        # Displays the splash image accordingly
        if terminal_width >= 80:
            display_splash()

        # Loads the current session configuration
        ai_dungeon.choose_config()

        # Initializes the story
        ai_dungeon.init_story()

        # Starts the game
        ai_dungeon.start_game()

    except FailedConfiguration:
        exit(1)

    except QuitSession:
        print_handler("Bye Bye!")

    except KeyboardInterrupt:
        print_handler("Received Keyboard Interrupt. Bye Bye...")

    except ConnectionError:
        print_handler("Lost connection to the Ai Dungeon servers")


if __name__ == "__main__":
    main()
