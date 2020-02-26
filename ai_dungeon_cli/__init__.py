#!/usr/bin/env python3

import os
import requests
import textwrap
import shutil
import yaml


class FailedConfiguration(Exception):
    """raise this when the yaml configuration phase failed"""


# Quit Session exception for easier error and exiting handling
class QuitSession(Exception):
    """raise this when the user typed /quit in order to leave the session"""


# CONFIG


def init_configuration_file():
    cfg_file = "/config.yml"
    cfg_file_paths = [
        os.path.dirname(os.path.realpath(__file__)) + cfg_file,
        os.getenv("HOME") + "/.config/ai-dungeon-cli" + cfg_file,
    ]

    did_read_cfg_file = False

    for file in cfg_file_paths:
        try:
            with open(file, 'r') as cfg_raw:
                cfg = yaml.load(cfg_raw, Loader=yaml.FullLoader)
                did_read_cfg_file = True
        except IOError:
            pass

    if not did_read_cfg_file:
        print("Missing config file at ", end="")
        print(*cfg_file_paths, sep=", ")
        exit(1)

    if not ("auth_token" in cfg and cfg["auth_token"]):
        print("Missing or empty 'auth_token' in config file")
        raise FailedConfiguration

    prompt = "> "
    if "prompt" in cfg and cfg["prompt"]:
        prompt = cfg["prompt"]

    return cfg["auth_token"], prompt


# SYSTEM FUNCTIONS


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


class AiDungeon:
    def __init__(self, auth_token, prompt):
        self.terminal_size = shutil.get_terminal_size((80, 20))
        self.terminal_width = self.terminal_size.columns
        self.prompt = prompt
        self.prompt_iteration = 0
        self.stop_session = False
        self.user_id = None
        self.session_id = None
        self.public_id = None
        self.story_configuration = {}
        self.session = requests.Session()
        self.session.headers.update(
            {
                # 'cookie': cookie,
                "X-Access-Token": auth_token,
            }
        )

    def print_sentences(self, text):
        print("\n".join(textwrap.wrap(text, self.terminal_width)))

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
                self.print_sentences("Please enter a valid selection.")
                print()
                continue
            break
        return choice

    def make_custom_config(self):

        self.print_sentences(
            "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
            "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
            "the kingdom. You enter the forest searching for the dragon and see'"
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
            return

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

    def init_story(self):

        print("Generating story... Please wait...\n")

        story_response = self.session.post(
            "https://api.aidungeon.io/sessions", json=self.story_configuration
        ).json()

        self.user_id = story_response["userId"]
        self.session_id = story_response["id"]
        self.public_id = story_response["publicId"]

        story_pitch = story_response["story"][0]["value"]

        self.print_sentences(story_pitch)
        print()

    def process_next_action(self):
        user_input = input(self.prompt)
        print()

        if user_input == "/quit":
            self.stop_session = True

        action_res = self.session.post(
            "https://api.aidungeon.io/sessions/" + str(self.session_id) + "/inputs",
            json={"text": user_input},
        ).json()

        action_res_str = action_res[self.prompt_iteration]["value"]
        self.print_sentences(action_res_str)
        print()

    def start_game(self):
        # Run until /quit is received inside the process_next_action func
        while not self.stop_session:
            self.prompt_iteration += 2
            self.process_next_action()


# MAIN

def main():

    try:
        # Loads the yaml configuration file
        auth_token, prompt = init_configuration_file()

        # Clears the console
        clear_console()

        # Displays the splash image accordingly
        display_splash()

        # Initialize the AiDungeon class with the given auth_token and prompt
        current_run = AiDungeon(auth_token, prompt)

        # Loads the current session configuration
        current_run.choose_config()

        # Initializes the story
        current_run.init_story()

        # Starts the game
        current_run.start_game()

    except FailedConfiguration:
        exit(1)

    except QuitSession:
        current_run.print_sentences("Bye Bye!")

    except ConnectionError:
        current_run.print_sentences("Lost connection to the Ai Dungeon servers")


if __name__ == "__main__":
    main()
