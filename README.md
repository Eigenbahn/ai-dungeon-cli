# AI Dungeon CLI

This is basically a cli client to [play.aidungeon.io](https://play.aidungeon.io/).

This allows playing AI Dungeon 2 inside a terminal.

I primarily did this to play the game on a DEC VT320 hardware terminal for a more _faithful_ experience.

For more context, read the [accompanying blog post](https://www.eigenbahn.com/2020/02/22/ai-dungeon-cli).

![AI DUngeon on a VT320](https://www.eigenbahn.com/assets/img/ai-dungeon-vt320.jpg)


## Configuration

You need to first login in a web browser to [play.aidungeon.io](https://play.aidungeon.io/).

You'd then need to grab the _Authentication Token_ that gets retrieved in your browser [localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage).

The easiest way for many might be to open the developer tools (`F12`), do a few actions in AI Dungeon and retrieve it from the `X-Auth-Token` _Request Header_ of the _POST inputs_ requests.

Then create a file `config.yml` in the same folder as `ai-dungeon-cli` with the following content:

```yaml
auth_token: '<MY-AUTH-TOKEN>'
```

## Dependencies

You need python (>= 3.3) along with the `requests` library.


## Limitations and future improvements

Right now, the code is over-optimistic: we don't catch cleanly when the backend is down.

A better user experience could be achieved with the use of the [curses](https://docs.python.org/3/library/curses.html) library.

For now, only the `/quit` action is supported. I need to enable the others (`/revert`, `/alter`...).

It would also be nice to add support for browsing other players' stories (_Explore_ menu).


## Implementation details

We fallback to a pure ASCII version of the splash logo if we detect an incompatible locale / terminal type.


## Support

As you might have heard, hosting AI Dungeon costs a lot of money.

This cli client relies on the same infrastructure as the online version ([play.aidungeon.io](https://play.aidungeon.io/)).

So don't hesitate to [help support the hosting fees](https://aidungeon.io/) to keep the game up and running.
