#!/usr/bin/env python3

import os
import requests
import textwrap
import shutil
import yaml
from pprint import pprint


# -------------------------------------------------------------------------
# EXCEPTIONS

class FailedConfiguration(Exception):
    """raise this when the yaml configuration phase failed"""


# Quit Session exception for easier error and exiting handling
class QuitSession(Exception):
    """raise this when the user typed /quit in order to leave the session"""


# -------------------------------------------------------------------------
# UTILS: DICT

def exists(cfg, key):
    return key in cfg and cfg[key]


# -------------------------------------------------------------------------
# UTILS: TERMINAL

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

    with open(filename, "r") as splash_image:
        print(splash_image.read())


def print_sentences(text, term_width):
    print("\n".join(textwrap.wrap(text, term_width)))


# -------------------------------------------------------------------------
# GAME LOGIC

class AiDungeon:
    def __init__(self):
        self.terminal_size = shutil.get_terminal_size((80, 20))
        self.terminal_width = self.terminal_size.columns

        # Variables initialization
        self.prompt = "> "
        self.auth_token = None
        self.email = None
        self.password = None
        self.prompt_iteration = 2
        self.stop_session = False
        self.user_id = None
        self.session_id = None
        self.public_id = None
        self.story_configuration = {}
        self.session = requests.Session()

        # Start class configuration
        self.load_configuration_file()

    def update_session_auth(self):
        self.session.headers.update(
            {
                "X-Access-Token": self.auth_token,
            }
        )

    def load_configuration_file(self):
        cfg_file = "/config.yml"
        cfg_file_paths = [
            os.path.dirname(os.path.realpath(__file__)) + cfg_file,
            os.getenv("HOME") + "/.config/ai-dungeon-cli" + cfg_file,
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
            print_sentences(
                "Missing or empty authentication configuration. "
                "Please register a token ('auth_token' key) or credentials ('email' / 'password')",
                self.terminal_width
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

    def get_auth_token(self):
        return self.auth_token

    def get_terminal_width(self):
        return self.terminal_width

    def login(self):
        request = self.session.post(
            "https://api.aidungeon.io/users",
            json={"email": self.email, "password": self.password},
        )

        if request.status_code != requests.codes.ok:
            print_sentences(
                "Failed to log in using provided credentials. Check your config.",
                self.terminal_width
            )
            raise FailedConfiguration

        self.auth_token = request.json()["accessToken"]

        self.update_session_auth()

    def choose_selection(self, allowed_values):
        while True:
            choice = input(self.prompt)
            print()

            choice = choice.strip()

            if choice == "/quit":
                raise QuitSession("/quit")

            elif choice in allowed_values.keys():
                choice = allowed_values[choice]
            elif choice in allowed_values.values():
                pass
            else:
                print_sentences("Please enter a valid selection.", self.terminal_width)
                print()
                continue
            break
        return choice


    def make_custom_config(self):
        print_sentences(
            "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
            "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
            "the kingdom. You enter the forest searching for the dragon and see'",
            self.terminal_width
        )
        print()

        context = input(self.prompt)
        print()

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
        print()
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
            print()
            selected_character = self.choose_selection(character_select_dict)

            if selected_character == "/quit":
                raise QuitSession("/quit")

            print("Enter your character's name...\n")

            character_name = input(self.prompt)
            print()

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

        self.user_id = story_response["userId"]
        self.session_id = story_response["id"]
        self.public_id = story_response["publicId"]

        story_pitch = story_response["story"][0]["value"]

        print_sentences(story_pitch, self.terminal_width)
        print()

    # Function for when the input typed was ordinary
    def process_regular_action(self, user_input):
        action_res = self.session.post(
            "https://api.aidungeon.io/sessions/" + str(self.session_id) + "/inputs",
            json={"text": user_input},
        ).json()
        action_res_str = action_res[self.prompt_iteration]["value"]
        print_sentences(action_res_str, self.terminal_width)
        print()

    # Function for when /remember is typed
    def process_remember_action(self, user_input):
        action_res = self.session.patch(
            "https://api.aidungeon.io/sessions/" + str(self.session_id),
            json={"context": user_input},
        ).json()

    # Function that is called each iteration to process user inputs
    def process_next_action(self):
        user_input = input(self.prompt)
        print()

        if user_input == "/quit":
            self.stop_session = True

        else:
            if user_input.startswith("/remember"):
                self.process_remember_action(user_input[len("/remember ") :])
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
        if ai_dungeon.terminal_width >= 80:
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
        print_sentences("Bye Bye!", ai_dungeon.get_terminal_width())

    except KeyboardInterrupt:
        print_sentences("Received Keyboard Interrupt. Bye Bye...",
                        ai_dungeon.get_terminal_width())

    except ConnectionError:
        print_sentences("Lost connection to the Ai Dungeon servers",
                        ai_dungeon.get_terminal_width())


if __name__ == "__main__":
    main()
