#!/usr/bin/env python3

import os
import sys
import asyncio
from gql import gql, Client, WebsocketsTransport
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

# DEBUG = False
DEBUG = True

def debug_print(msg):
    if DEBUG:
        print(msg)

def debug_pprint(msg):
    if DEBUG:
        print(msg)


# -------------------------------------------------------------------------
# API CLIENT ABSCTRACTION

class AiDungeonApiClient:
    def __init__(self):
        self.url: str = 'wss://api.aidungeon.io/subscriptions'
        self.websocket = WebsocketsTransport(url=self.url)
        self.gql_client = Client(transport=self.websocket,
                                 # fetch_schema_from_transport=True,
        )
        self.account_id: str = ''
        self.access_token: str = ''

        self.single_player_mode_id: str = 'scenario:458612'
        self.scenario_id: str = '' # REVIEW: maybe call it setting_id ?
        self.character_name: str = ''
        self.story_pitch_template: str = ''
        self.story_pitch: str = ''
        self.adventure_id: str = ''
        self.public_id: str = ''
        self.quests: str = ''


    async def _execute_query_pseudo_async(self, query, params={}):
        async with Client(
                transport=self.websocket,
                # fetch_schema_from_transport=True,
        ) as session:
            return await session.execute(gql(query), variable_values=params)


    def _execute_query(self, query, params=None):
        return self.gql_client.execute(gql(query), variable_values=params)


    def update_session_access_token(self, access_token):
        self.websocket = WebsocketsTransport(
            url=self.url,
            init_payload={'token': access_token})
        self.gql_client = Client(transport=self.websocket,
                                 # fetch_schema_from_transport=True,
        )


    def user_login(self, email, password):
        debug_print("user login")
        result = self._execute_query('''
        mutation ($email: String, $password: String, $anonymousId: String) {  login(email: $email, password: $password, anonymousId: $anonymousId) {    id    accessToken    __typename  }}
        ''',
                                     {
                                         "email": email ,
                                         "password": password
                                     }
        )
        debug_print(result)
        self.account_id = result['login']['id']
        self.access_token = result['login']['accessToken']
        self.update_session_access_token(self.access_token)


    def anonymous_login(self):
        debug_print("anonymous login")
        result = self._execute_query('''
        mutation {  createAnonymousAccount {    id    accessToken    __typename  }}
        ''')
        debug_print(result)
        self.account_id = result['createAnonymousAccount']['id']
        self.access_token = result['createAnonymousAccount']['accessToken']
        self.update_session_access_token(self.access_token)



    def perform_init_handshake(self):
        # debug_print("query user details")
        # result = self._execute_query('''
        # {  user {    id    isDeveloper    hasPremium    lastAdventure {      id      mode      __typename    }    newProductUpdates {      id      title      description      createdAt      __typename    }    __typename  }}
        # ''')
        # debug_print(result)


        debug_print("add device token")
        result = self._execute_query('''
        mutation ($token: String, $platform: String) {  addDeviceToken(token: $token, platform: $platform)}
        ''',
                                     { 'token': 'web',
                                       'platform': 'web' })
        debug_print(result)


        debug_print("send event start premium")
        result = self._execute_query('''
        mutation ($input: EventInput) {  sendEvent(input: $input)}
        ''',
                                     {
                                         "input": {
                                             "eventName":"start_premium_v5",
                                             "variation":"dont",
                                             # "variation":"show",
                                             "platform":"web"
                                         }
                                     })
        debug_print(result)


    @staticmethod
    def normalize_options(raw_settings_list):
        settings_dict = {}
        for i, opts in enumerate(raw_settings_list, start=1):
            setting_id = opts['id']
            setting_name = opts['title']
            settings_dict[str(i)] = [setting_id, setting_name]
        return settings_dict


    def get_options(self, scenario_id):
        prompt = ''
        options = None

        debug_print("query options (variant #1)")
        result = self._execute_query('''
        query ($id: String) {  user {    id    username    __typename  }  content(id: $id) {    id    userId    contentType    contentId    prompt    gameState    options {      id      title      __typename    }    playPublicId    __typename  }}
        ''',
                                     {"id": scenario_id})
        debug_print(result)
        prompt = result['content']['prompt']
        if result['content']['options']:
            options = self.normalize_options(result['content']['options'])

        # debug_print("query options (variant #2)")
        # result = self._execute_query('''
        # query ($id: String) {  content(id: $id) {    id    contentType    contentId    title    description    prompt    memory    tags    nsfw    published    createdAt    updatedAt    deletedAt    options {      id      title      __typename    }    __typename  }}
        # ''',
        #                              {"id": scenario_id})
        # debug_print(result)
        # prompt = result['content']['prompt']
        # options = self.normalize_options(result['content']['options'])

        return [prompt, options]


    def get_settings_single_player(self):
        return self.get_options(self.single_player_mode_id)


    def get_characters(self):
        prompt = ''
        characters = {}

        debug_print("query settings singleplayer (variant #1)")
        result = self._execute_query('''
        query ($id: String) {  user {    id    username    __typename  }  content(id: $id) {    id    userId    contentType    contentId    prompt    gameState    options {      id      title      __typename    }    playPublicId    __typename  }}
        ''',
                                     {"id": self.scenario_id})
        debug_print(result)
        prompt = result['content']['prompt']
        characters = self.normalize_options(result['content']['options'])

        # debug_print("query settings singleplayer (variant #2)")
        # result = self._execute_query('''
        # query ($id: String) {  content(id: $id) {    id    contentType    contentId    title    description    prompt    memory    tags    nsfw    published    createdAt    updatedAt    deletedAt    options {      id      title      __typename    }    __typename  }}
        # ''',
        #                              {"id": self.scenario_id})
        # debug_print(result)
        # prompt = result['content']['prompt']
        # characters = self.normalize_options(result['content']['options'])

        return [prompt, characters]


    def get_story_for_scenario(self):

        debug_print("query get story for scenario")
        result = self._execute_query('''
        query ($id: String) {  user {    id    username    __typename  }  content(id: $id) {    id    userId    contentType    contentId    prompt    gameState    options {      id      title      __typename    }    playPublicId    __typename  }}
        ''',
                                     {"id": self.scenario_id})
        debug_print(result)
        self.story_pitch_template = result['content']['prompt']

        # debug_print("query get story for scenario #2")
        # result = self._execute_query('''
        # query ($id: String) {  content(id: $id) {    id    contentType    contentId    title    description    prompt    memory    tags    nsfw    published    createdAt    updatedAt    deletedAt    options {      id      title      __typename    }    __typename  }}
        # ''',
        #                              {"id": self.scenario_id})
        # debug_print(result)



    @staticmethod
    def initial_story_from_history_list(history_list):
        pitch = ''
        for entry in history_list:
            if not entry['type'] in ['story', 'continue']:
                break
            pitch += entry['text']
        return pitch


    def set_story_pitch(self):
        self.story_pitch = self.story_pitch_template.replace('${character.name}', self.character_name)


    def init_custom_story_pitch(self, user_input):

        debug_print("send custom settings story pitch")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  sendAction(input: $input) {    id    actionLoading    memory    died    gameState    newQuests {      id      text      completed      active      __typename    }    actions {      id      text      __typename    }    __typename  }}
        ''',
                                     {
                                         "input": {
                                             "type": "story",
                                             "text": user_input,
                                             "id": self.adventure_id}})
        debug_print(result)
        self.story_pitch = ''.join([a['text'] for a in result['sendAction']['actions']])


    def _create_adventure(self, scenario_id):
        debug_print("create adventure")
        result = self._execute_query('''
        mutation ($id: String, $prompt: String) {  createAdventureFromScenarioId(id: $id, prompt: $prompt) {    id    contentType    contentId    title    description    musicTheme    tags    nsfw    published    createdAt    updatedAt    deletedAt    publicId    historyList    __typename  }}
        ''',
                                     {
                                         "id": scenario_id,
                                         "prompt": self.story_pitch
                                     })
        debug_print(result)
        self.adventure_id = result['createAdventureFromScenarioId']['id']
        if 'historyList' in result['createAdventureFromScenarioId']:
            # NB: not present when self.story_pitch is None, as is the case for a custom scenario
            self.story_pitch = self.initial_story_from_history_list(result['createAdventureFromScenarioId']['historyList'])


    def init_story(self):

        self._create_adventure(self.scenario_id)

        debug_print("get created adventure ids")
        result = self._execute_query('''
        query ($id: String, $playPublicId: String) {  content(id: $id, playPublicId: $playPublicId) {    id    historyList    quests    playPublicId    userId    __typename  }}
        ''',
                                     {
                                         "id": self.adventure_id,
                                     })
        debug_print(result)
        self.quests = result['content']['quests']
        self.public_id = result['content']['playPublicId']
        # self.story_pitch = self.initial_story_from_history_list(result['content']['historyList'])


    def perform_remember_action(self, user_input):
        debug_print("remember something")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  updateMemory(input: $input) {    id    memory    __typename  }}
        ''',
                                     {
                                         "input":
                                         {
                                             "text": user_input,
                                             "type":"remember",
                                             "id": self.adventure_id
                                         }
                                     })
        debug_print(result)


    def perform_regular_action(self, action, user_input):

        story_continuation = ""


        debug_print("send regular action")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  sendAction(input: $input) {    id    actionLoading    memory    died    gameState    __typename  }}
        ''',
                                     {
                                         "input": {
                                             "type": action,
                                             "text": user_input,
                                             "id": self.adventure_id
                                         }
                                     })
        debug_print(result)


        debug_print("get story continuation")
        result = self._execute_query('''
        query ($id: String, $playPublicId: String) {
            content(id: $id, playPublicId: $playPublicId) {
                id
                actions {
                    id
                    text
                }
            }
        }
        ''',
                                     {
                                         "id": self.adventure_id
                                     })
        debug_print(result)
        story_continuation = result['content']['actions'][-1]['text']

        return story_continuation


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

        cfg = {}
        for file in cfg_file_paths:
            try:
                with open(file, "r") as cfg_raw:
                    cfg = yaml.load(cfg_raw, Loader=yaml.FullLoader)
                    did_read_cfg_file = True
            except IOError:
                pass

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

class AbstractAiDungeonGame(ABC):
    def __init__(self, api: AiDungeonApiClient, conf: Config, user_io: UserIo):
        self.stop_session: bool = False
        self.user_id: str = None
        self.session_id: str = None
        self.public_id: str = None
        self.setting_name: str = None
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

        self.api.character_name = character_name # TODO: create a setter instead


    def choose_config(self):
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
        self.api.scenario_id = setting_id # TODO: create a setter instead

        if self.setting_name == "custom":
            return
        elif self.setting_name == "archive":
            while True:
                prompt, options = self.api.get_options(self.api.scenario_id)

                if options is None:
                    self.api.story_pitch_template = prompt
                    self._choose_character_name()
                    self.api.set_story_pitch()
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
                self.api.scenario_id = option_id # TODO: create a setter instead


        ## CHARACTER SELECTION

        prompt, characters = self.api.get_characters()

        print(prompt + "\n")

        character_select_dict = {}
        for i, character in characters.items():
            character_id, character_type = character
            print(str(i) + ") " + character_type)
            character_select_dict[str(i)] = character_type
        selected_i = self.choose_selection(character_select_dict, 'k')
        character_id, character_type = characters[selected_i]
        self.api.scenario_id = character_id # TODO: create a setter instead

        self._choose_character_name()

        ## PITCH

        self.api.get_story_for_scenario()
        self.api.set_story_pitch()


    # Initialize story
    def init_story(self):
        if self.setting_name == "custom":
            self.init_story_custom()
        else:
            print("Generating story... Please wait...\n")
            self.api.init_story()

        self.user_io.handle_story_output(self.api.story_pitch)


    def init_story_custom(self):
        self.user_io.handle_basic_output(
            "Enter a prompt that describes who you are and the first couple sentences of where you start out ex: "
            "'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been terrorizing "
            "the kingdom. You enter the forest searching for the dragon and see'"
        )
        user_story_pitch = self.user_io.handle_user_input()

        self.api.story_pitch = None
        self.api._create_adventure(self.api.scenario_id)
        self.api.init_custom_story_pitch(user_story_pitch)


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

        resp = self.api.perform_regular_action(action, user_input)

        self.user_io.handle_story_output(resp)

    def process_remember_action(self, user_input: str):
        self.api.perform_remember_action(user_input)

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
        ai_dungeon.choose_config()

        # Initializes the story
        ai_dungeon.init_story()

        # exit()

        # Starts the game
        ai_dungeon.start_game()

    except FailedConfiguration as e:
        # NB: No UserIo initialized at this level
        # hence we fallback to a classic `print`
        print(e.message)
        exit(1)

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
