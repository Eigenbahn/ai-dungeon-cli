import os
from typing import Dict
import argparse
import yaml


# -------------------------------------------------------------------------
# UTILS: DICT

def exists(cfg: Dict[str, str], key: str) -> str:
    return key in cfg and cfg[key]


# -------------------------------------------------------------------------
# CONF OBJECT

class Config:
    def __init__(self):
        self.prompt: str = "> "
        self.slow_typing_effect: bool = False

        self.auth_token: str = None
        self.email: str = None
        self.password: str = None

        self.character_name: str = None
        self.public_adventure_id: str = None

        self.debug: bool = False

    @staticmethod
    def merged(confs):
        default_conf = Config()
        conf = Config()
        for c in confs:
            for a in ['prompt', 'slow_typing_effect',
                      'auth_token', 'email', 'password',
                      'character_name', 'public_adventure_id',
                      'debug']:
                v = getattr(c, a)
                if getattr(default_conf, a) != v:
                    setattr(conf, a, v)
        return conf

    @staticmethod
    def loaded_from_cli_args():
        conf = Config()
        conf.load_from_cli_args()
        return conf

    def load_from_cli_args(self):
        parsed = Config.parse_cli_args()
        if hasattr(parsed, "prompt"):
            self.prompt = parsed.prompt
        if hasattr(parsed, "slow_typing"):
            self.slow_typing_effect = parsed.slow_typing
        if hasattr(parsed, "auth_token"):
            self.auth_token = parsed.auth_token
        if hasattr(parsed, "email"):
            self.email = parsed.email
        if hasattr(parsed, "password"):
            self.password = parsed.password
        if hasattr(parsed, "adventure"):
            self.public_adventure_id = parsed.adventure
        if hasattr(parsed, "name"):
            self.character_name = parsed.name
        if hasattr(parsed, "debug"):
            self.debug = parsed.debug

    @staticmethod
    def parse_cli_args():
        parser = argparse.ArgumentParser(description='ai-dungeon-cli is a command-line client to play.aidungeon.io')
        parser.add_argument("--prompt", type=str, required=False, default="> ",
                            help="text for user prompt")
        parser.add_argument("--slow-typing", action='store_const', const=True,
                            help="enable slow typing effect for story")

        parser.add_argument("--auth-token", type=str, required=False,
                            help="authentication token")
        parser.add_argument("--email", type=str, required=False,
                            help="email (for authentication)")
        parser.add_argument("--password", type=str, required=False,
                            help="password (for authentication)")

        parser.add_argument("--adventure", type=str, required=False,
                            help="public multi-user adventure id to connect to")
        parser.add_argument("--name", type=str, required=False,
                            help="character name for multi-user adventure")

        parser.add_argument("--debug", action='store_const', const=True,
                            help="enable debug")

        parsed = parser.parse_args()

        if parsed.adventure and not parsed.name:
            parser.error("--name needs to be provided when joining a multi-user adventure (--adventure argument)")

        return parsed

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

        if exists(cfg, "prompt"):
            self.prompt = cfg["prompt"]
        if exists(cfg, "slow_typing_effect"):
            self.slow_typing_effect = cfg["slow_typing_effect"]
        if exists(cfg, "auth_token"):
            self.auth_token = cfg["auth_token"]
        if exists(cfg, "email"):
            self.email = cfg["email"]
        if exists(cfg, "password"):
            self.password = cfg["password"]
