import asyncio
from gql import gql, Client, WebsocketsTransport

from impl.utils.debug_print import debug_print, debug_pprint


# -------------------------------------------------------------------------
# API CLIENT

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


    def join_multi_adventure(self, public_adventure_id):
        debug_print("join multi-user adventure")
        result = self._execute_query('''
        mutation ($adventurePlayPublicId: String) {  addUserToAdventure(adventurePlayPublicId: $adventurePlayPublicId)}
        ''',
                                     {"adventurePlayPublicId": public_adventure_id})
        debug_print(result)
        return result['addUserToAdventure']


    def get_characters(self, scenario_id):
        prompt = ''
        characters = {}

        debug_print("query settings singleplayer (variant #1)")
        result = self._execute_query('''
        query ($id: String) {  user {    id    username    __typename  }  content(id: $id) {    id    userId    contentType    contentId    prompt    gameState    options {      id      title      __typename    }    playPublicId    __typename  }}
        ''',
                                     {"id": scenario_id})
        debug_print(result)
        prompt = result['content']['prompt']
        characters = self.normalize_options(result['content']['options'])

        # debug_print("query settings singleplayer (variant #2)")
        # result = self._execute_query('''
        # query ($id: String) {  content(id: $id) {    id    contentType    contentId    title    description    prompt    memory    tags    nsfw    published    createdAt    updatedAt    deletedAt    options {      id      title      __typename    }    __typename  }}
        # ''',
        #                              {"id": scenario_id})
        # debug_print(result)
        # prompt = result['content']['prompt']
        # characters = self.normalize_options(result['content']['options'])

        return [prompt, characters]


    def get_story_template_for_scenario(self, scenario_id):

        debug_print("query get story for scenario")
        result = self._execute_query('''
        query ($id: String) {  user {    id    username    __typename  }  content(id: $id) {    id    userId    contentType    contentId    prompt    gameState    options {      id      title      __typename    }    playPublicId    __typename  }}
        ''',
                                     {"id": scenario_id})
        debug_print(result)
        return result['content']['prompt']

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


    def make_story_pitch(self, story_pitch_template, character_name):
        return story_pitch_template.replace('${character.name}', character_name)


    def init_custom_story_pitch(self, adventure_id, user_input):

        debug_print("send custom settings story pitch")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  sendAction(input: $input) {    id    actionLoading    memory    died    gameState    newQuests {      id      text      completed      active      __typename    }    actions {      id      text      __typename    }    __typename  }}
        ''',
                                     {
                                         "input": {
                                             "type": "story",
                                             "text": user_input,
                                             "id": adventure_id}})
        debug_print(result)
        return ''.join([a['text'] for a in result['sendAction']['actions']])


    def create_adventure(self, scenario_id, story_pitch):
        debug_print("create adventure")
        result = self._execute_query('''
        mutation ($id: String, $prompt: String) {  createAdventureFromScenarioId(id: $id, prompt: $prompt) {    id    contentType    contentId    title    description    musicTheme    tags    nsfw    published    createdAt    updatedAt    deletedAt    publicId    historyList    __typename  }}
        ''',
                                     {
                                         "id": scenario_id,
                                         "prompt": story_pitch
                                     })
        debug_print(result)
        adventure_id = result['createAdventureFromScenarioId']['id']
        story_pitch = None
        if 'historyList' in result['createAdventureFromScenarioId']:
            # NB: not present when story_pitch is None, as is the case for a custom scenario
            story_pitch = self.initial_story_from_history_list(result['createAdventureFromScenarioId']['historyList'])
        return [adventure_id, story_pitch]


    def init_story_multi_adventure(self, public_adventure_id):
        debug_print("get story multi-user adventure")
        result = self._execute_query('''
        query ($id: String, $playPublicId: String) {  content(id: $id, playPublicId: $playPublicId) {    id    actions {      id      text      __typename    }    quests    newQuests {      id      text      completed      active      __typename    }    playPublicId    userId    __typename  }}
        ''',
                                     {"playPublicId": public_adventure_id})
        debug_print(result)
        entries = []
        for entry in result['content']['actions']:
            if entry['__typename'] != 'Action':
                continue
            entry = entry['text']
            if entry.startswith("\n>"):
                entry = "\n" + entry + "\n" # mo' spacing please
            entries.append(entry)
        return ''.join(entries)


    def init_story(self, scenario_id, story_pitch):
        adventure_id, story_pitch = self.create_adventure(scenario_id, story_pitch)

        debug_print("get created adventure ids")
        result = self._execute_query('''
        query ($id: String, $playPublicId: String) {  content(id: $id, playPublicId: $playPublicId) {    id    historyList    quests    playPublicId    userId    __typename  }}
        ''',
                                     {
                                         "id": adventure_id,
                                     })
        debug_print(result)
        quests = result['content']['quests']
        public_id = result['content']['playPublicId']
        # story_pitch = self.initial_story_from_history_list(result['content']['historyList'])

        return [adventure_id, public_id, story_pitch, quests]



    def perform_remember_action(self, user_input, adventure_id):
        debug_print("remember something")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  updateMemory(input: $input) {    id    memory    __typename  }}
        ''',
                                     {
                                         "input":
                                         {
                                             "text": user_input,
                                             "type":"remember",
                                             "id": adventure_id
                                         }
                                     })
        debug_print(result)


    def perform_regular_action(self, adventure_id, action, user_input, character_name = None):

        story_continuation = ""

        debug_print("send regular action")
        result = self._execute_query('''
        mutation ($input: ContentActionInput) {  sendAction(input: $input) {    id    actionLoading    memory    died    gameState    __typename  }}
        ''',
                                     {
                                         "input": {
                                             "type": action,
                                             "text": user_input,
                                             "id": adventure_id,
                                             "characterName": character_name
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
                                         "id": adventure_id
                                     })
        debug_print(result)
        story_continuation = result['content']['actions'][-1]['text']

        return story_continuation
