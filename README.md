# seeqer

A simple drum machine written in Python/tkinter.

1. The drumkit in this repo are from [Muldjordkit](https://drumgizmo.org/wiki/doku.php?id=kits:muldjordkit).
2. The other sounds are from [Free Wave Samples](https://freewavesamples.com).


# Install

Run `pip install -r requirements.txt` which installs

```
pygame
numpy
samplerate
```

# Usage

Start with `python seeqer.py [WIDTH=16]`

If you want something else than 4 measures, start with e.g. `python seeqer.py 32`

## Keybindings

* `space` pause/start
* `s` save pattern
* `l` load pattern
* `c` clear pattern
* `1` toggle instrument 1
* `2` toggle instrument 2
* ...
