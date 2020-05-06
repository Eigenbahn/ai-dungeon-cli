# AI Dungeon CLI

This is basically a cli client to [play.aidungeon.io](https://play.aidungeon.io/).

This allows playing AI Dungeon 2 inside a terminal.

I primarily did this to play the game on a DEC VT320 hardware terminal for a more _faithful_ experience.

For more context, read the [accompanying blog post](https://www.eigenbahn.com/2020/02/22/ai-dungeon-cli).

![AI DUngeon on a VT320](https://www.eigenbahn.com/assets/img/ai-dungeon-vt320.jpg)


## Installation

#### pip

[![PyPI version fury.io](https://badge.fury.io/py/ai-dungeon-cli.svg)](https://pypi.python.org/project/ai-dungeon-cli/)

    $ python3 -m pip install ai-dungeon-cli


Of for unstable release from the source code:

    $ python3 -m pip install .


#### Arch Linux

[![AUR version](https://img.shields.io/aur/version/ai-dungeon-cli?logo=arch-linux)](https://aur.archlinux.org/packages/ai-dungeon-cli)

Package is on [AUR](https://aur.archlinux.org/packages/ai-dungeon-cli-git/).

Using [trizen](https://github.com/trizen/trizen):

    $ trizen -S ai-dungeon-cli-git

Old school way:

    $ git clone https://aur.archlinux.org/ai-dungeon-cli-git.git
    $ cd ai-dungeon-cli-git
    $ makepkg -si


## Running

In any case, you first need to create a configuration file.

#### Installed

    $ ai-dungeon-cli

#### From source

With a conda env (assuming you're using [anaconda](https://www.anaconda.com/)):

    $ cd ai-dungeon-cli
    $ conda env create
    $ conda activate ai-dungeon-cli-env
    $ ./ai_dungeon_cli/__init__.py

With a viltualenv:

    $ cd ai-dungeon-cli
    $ virtualenv -p $(command -v python3) ai-dungeon-cli-venv
    $ source ai-dungeon-cli-venv/bin/activate
    $ python3 -m pip install -r requirements.txt
    $ ./ai_dungeon_cli/__init__.py

Please note that all those examples use a virtual env in order to not mess up with the main Python env on your system.


## Configuration

Create a file `config.yml` either:

 - in the same folder in your home folder: `$HOME/.config/ai-dungeon-cli/config.yml`
 - in the same folder as the sources: `./ai-dungeon-cli/ai_dungeon_cli/config.yml`


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

The default user prompt is `'> '`.

You can customize it with e.g. :

```yaml
prompt: 'me: '
```


#### Slow Typing Animation

By default, responses are printed to the screen instantly.

To enable a fun "slow" typing animation, use:

```yaml
slow_typing_effect: True
```


## Dependencies

Please have a look at [requirements.txt](./requirements.txt).


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


## Contributors & acknowledgements

 Major contributions:
 - Idan Gur [@idangur](https://github.com/idangur): OOP rewrite of game logic
 - Alberto Oporto Ames [@otreblan](https://github.com/otreblan): packaging, submission to AUR
 - [@jgb95](https://github.com/jgb95): slow typing effect

 Minor contributions:
 - Robert Davis [@bdavs](https://github.com/bdavs): pip requirements
 - [@Jezza](https://github.com/Jezza): suggested login using creds

Code for slow typing effect inspired by [this message](https://mail.python.org/pipermail/tutor/2003-November/026645.html) from [Magnus Lycka](https://github.com/magnus-lycka) on the [Python Tutor mailing list](https://mail.python.org/mailman/listinfo/tutor).


## Similar projects

[SoptikHa2/aidungeon2-cli](https://github.com/SoptikHa2/aidungeon2-cli) is a very similar project, written in Rust.
