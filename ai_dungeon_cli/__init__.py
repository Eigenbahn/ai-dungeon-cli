#!/usr/bin/env python3

import os
import sys
import asyncio
from gql import gql, Client, WebsocketsTransport
import requests

from abc import ABC, abstractmethod

from typing import Dict

from pprint import pprint

# NB: this is hackish but seems necessary when downloaded from pypi
main_path = os.path.dirname(os.path.realpath(__file__))
module_path = os.path.abspath(main_path)
if module_path not in sys.path:
    sys.path.append(module_path)

from impl.utils.debug_print import activate_debug, debug_print, debug_pprint
from impl.api.client import AiDungeonApiClient
from impl.conf import Config
from impl.user_interaction import UserIo, TermIo, TermIoSlowStory


# -------------------------------------------------------------------------
# EXCEPTIONS

# Quit Session exception for easier error and exiting handling
class QuitSession(Exception):
    """raise this when the user typed /quit in order to leave the session"""


# -------------------------------------------------------------------------
# GAME LOGIC

class AbstractAiDungeonGame(ABC):
    def __init__(self, api: AiDungeonApiClient, conf: Config, user_io: UserIo):
        self.stop_session: bool = False

        self.user_id: str = None
        self.session_id: str = None

        self.scenario_id: str = '' # REVIEW: maybe call it setting_id ?
        self.character_name: str = ''
        self.adventure_id: str = ''
        self.public_id: str = None

        self.story_pitch_template: str = ''
        self.story_pitch: str = ''
        self.quests: str = ''

        self.setting_name: str = None
        self.is_multiplayer: bool = False
        self.story_configuration: Dict[str, str] = {}
        self.session: requests.Session = requests.Session()

        self.api = api
        self.conf = conf
        self.user_io = user_io

    def update_session_auth(self):
        self.session.headers.update({"X-Access-Token": self.conf.auth_token})

    def get_auth_token(self) -> str:
        return self.conf.auth_token

    def get_credentials(self):
        if self.conf.email and self.conf.password:
            return [self.conf.email, self.conf.password]

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


    def make_user_choose_config(self):
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

class AiDungeonGame(AbstractAiDungeonGame):
    def __init__(self, api: AiDungeonApiClient, conf: Config, user_io: UserIo):
        super().__init__(api, conf, user_io)


    def login(self):
        auth_token = self.get_auth_token()

        if auth_token:
            self.api.update_session_access_token(auth_token)
        else:
            creds = self.get_credentials()
            if creds:
                email, password = creds
                self.api.user_login(email, password)
            else:
                self.api.anonymous_login()


    def _choose_character_name(self):
        print("Enter your character's name...\n")

        character_name = self.user_io.handle_user_input()

        if character_name == "/quit":
            raise QuitSession("/quit")

        self.character_name = character_name # TODO: create a setter instead


    def join_multiplayer(self):
        self.is_multiplayer = True
        self.character_name = self.conf.character_name
        self.adventure_id = self.api.join_multi_adventure(self.conf.public_adventure_id)


    def make_user_choose_config(self):
        # self.api.perform_init_handshake()

        ## SETTING SELECTION

        prompt, settings = self.api.get_options(self.api.single_player_mode_id)

        print(prompt + "\n")

        setting_select_dict = {}
        for i, setting in settings.items():
            setting_id, setting_name = setting
            print(str(i) + ") " + setting_name)
            setting_select_dict[str(i)] = setting_name
            # setting_select_dict['0'] = '0' # secret mode
        selected_i = self.choose_selection(setting_select_dict, 'k')
        setting_id, self.setting_name = settings[selected_i]
        self.scenario_id = setting_id

        if self.setting_name == "custom":
            return
        elif self.setting_name == "archive":
            while True:
                prompt, options = self.api.get_options(self.scenario_id)

                if options is None:
                    self.story_pitch_template = prompt
                    self._choose_character_name()
                    self.story_pitch = self.api.make_story_pitch(self.story_pitch_template,
                                                                self.character_name)
                    return

                print(prompt + "\n")

                select_dict = {}
                for i, option in options.items():
                    option_id, option_name = option
                    print(str(i) + ") " + option_name)
                    select_dict[str(i)] = option_name
                    # setting_select_dict['0'] = '0' # secret mode
                selected_i = self.choose_selection(select_dict, 'k')
                option_id, option_name = options[selected_i]
                self.scenario_id = option_id


        ## CHARACTER SELECTION

        prompt, characters = self.api.get_characters(self.scenario_id)

        print(prompt + "\n")

        character_select_dict = {}
        for i, character in characters.items():
            character_id, character_type = character
            print(str(i) + ") " + character_type)
            character_select_dict[str(i)] = character_type
        selected_i = self.choose_selection(character_select_dict, 'k')
        character_id, character_type = characters[selected_i]
        self.scenario_id = character_id # TODO: create a setter instead

        self._choose_character_name()

        ## PITCH

        self.story_pitch_template = self.api.get_story_template_for_scenario(self.scenario_id)
        self.story_pitch = self.api.make_story_pitch(self.story_pitch_template,
                                                     self.character_name)


    # Initialize story
    def init_story(self):
        if self.is_multiplayer:
            self.api.init_story_multi_adventure(self.conf.public_adventure_id)
        elif self.setting_name == "custom":
            self.init_story_custom()
        else:
            print("Generating story... Please wait...\n")
            self.adventure_id, self.public_id, self.story_pitch, self.quests = self.api.init_story(self.scenario_id,
                                                                                self.story_pitch)

        self.user_io.handle_story_output(self.story_pitch)


    def init_story_custom(self):
        self.user_io.handle_basic_output(
            "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
            "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
            "the kingdom. You enter the forest searching for the dragon and see'"
        )
        user_story_pitch = self.user_io.handle_user_input()

        self.story_pitch = None
        self.adventure_id, _ = self.api.create_adventure(self.scenario_id, self.story_pitch)
        self.story_pitch = self.api.init_custom_story_pitch(self.adventure_id, user_story_pitch)


    def find_action_type(self, user_input: str):
        user_input = user_input.strip()
        action = 'do'
        if user_input == '':
            return (action, user_input)
        elif user_input.lower().startswith('/do '):
            user_input = user_input[len('/do '):]
            action = 'do'
        elif user_input.lower().startswith('/say '):
            user_input = user_input[len('/say '):]
            action = 'say'
        elif user_input.lower().startswith('/story '):
            user_input = user_input[len('/story '):]
            action = 'story'
        elif user_input.lower().startswith('you say "') and user_input[-1] == '"':
            user_input = user_input[len('you say "'):-1]
            action = 'say'
        elif user_input[0] == '"' and user_input[-1] == '"':
            user_input = user_input[1:-1]
            action = 'say'
        return (action, user_input)


    # Function for when the input typed was ordinary
    def process_regular_action(self, user_input: str):

        (action, user_input) = self.find_action_type(user_input)

        resp = self.api.perform_regular_action(self.adventure_id, action, user_input, self.character_name)

        self.user_io.handle_story_output(resp)

    def process_remember_action(self, user_input: str):
        self.api.perform_remember_action(user_input, self.adventure_id)

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
        file_conf = Config.loaded_from_file()
        cli_args_conf = Config.loaded_from_cli_args()
        conf = Config.merged([file_conf, cli_args_conf])

        if conf.debug:
            activate_debug()

        # Initialize the terminal I/O class
        if conf.slow_typing_effect:
            term_io = TermIoSlowStory(conf.prompt)
        else:
            term_io = TermIo(conf.prompt)

        api_client = AiDungeonApiClient()

        # Initialize the game logic class with the given auth_token and prompt
        ai_dungeon = AiDungeonGame(api_client, conf, term_io)

        # Clears the console
        term_io.clear()

        # Login
        ai_dungeon.login()

        # Displays the splash image accordingly
        if term_io.get_width() >= 80:
            term_io.display_splash()

        # Loads the current session configuration
        if conf.public_adventure_id:
            ai_dungeon.join_multiplayer()
        else:
            ai_dungeon.make_user_choose_config()

        # Initializes the story
        ai_dungeon.init_story()

        # Starts the game
        ai_dungeon.start_game()

    except QuitSession:
        term_io.handle_basic_output("Bye Bye!")

    except EOFError:
        term_io.handle_basic_output("Received Keyboard Interrupt. Bye Bye...")

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
