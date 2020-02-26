# AI Dungeon CLI

This is basically a cli client to [play.aidungeon.io](https://play.aidungeon.io/).

This allows playing AI Dungeon 2 inside a terminal.

I primarily did this to play the game on a DEC VT320 hardware terminal for a more _faithful_ experience.

For more context, read the [accompanying blog post](https://www.eigenbahn.com/2020/02/22/ai-dungeon-cli).

![AI DUngeon on a VT320](https://www.eigenbahn.com/assets/img/ai-dungeon-vt320.jpg)


## Running

After cloning the repo and making a configuration file `config.yml` in the project folder, just:

    $ ./ai-dungeon-cli


## Configuration

Then create a file `config.yml` in the same folder as script `ai-dungeon-cli`.

#### Authentication (mandatory)

ai-dungeon-cli supports 2 ways to configure user authentication.

Either precise a couple of credentials in conf:

```yaml
email: '<MY-USER-EMAIL>'
password: '<MY-USER-PASSWORD>'
```

Or sniff a _Authentication Token_ and use it directly:

```yaml
auth_token: '<MY-AUTH-TOKEN>'
```

To get this token, you need to first login in a web browser to [play.aidungeon.io](https://play.aidungeon.io/).

Then you can find the token either in your browser [localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) or in `X-Auth-Token` _Request Header_ of the _POST inputs_ requests made while playing.

Either way, developer tools (`F12`) is your friend.


#### Prompt

The default user prompt is `> `.

You can customize it with e.g. :

```yaml
prompt: 'me: '
```


## Dependencies

You need python (>= 3.3) along with the `requests` and `pyyaml` libraries.

You can install the pip libraries by running the following from this project's folder:

```bash
python3 -m pip install -r requirements.txt
```


## Limitations and future improvements

Right now, the code is over-optimistic: we don't catch cleanly when the backend is down.

A better user experience could be achieved with the use of the [curses](https://docs.python.org/3/library/curses.html) library.

For now, only the `/quit` and `remember` actions are supported. I need to enable the others (`/revert`, `/alter`...).

It would also be nice to add support for browsing other players' stories (_Explore_ menu).


## Implementation details

We fallback to a pure ASCII version of the splash logo if we detect an incompatible locale / terminal type.


## Support

As you might have heard, hosting AI Dungeon costs a lot of money.

This cli client relies on the same infrastructure as the online version ([play.aidungeon.io](https://play.aidungeon.io/)).

So don't hesitate to [help support the hosting fees](https://aidungeon.io/) to keep the game up and running.


## Author

Jordan Besly [@p3r7](https://github.com/p3r7) ([blog](https://www.eigenbahn.com/)).


## Contributors

 - [@Jezza](https://github.com/Jezza)
 - Robert Davis [@bdavs](https://github.com/bdavs)
