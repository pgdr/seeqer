from functools import cache
from collections import defaultdict
from dataclasses import dataclass
import json
from samplerate import resample

import tkinter as tk
import pygame

pygame.mixer.init()


with open("sounds.json", "r") as file:
    data = json.load(file)
SOUNDS = data["sounds"]

pygame.mixer.set_num_channels(len(SOUNDS) + 1)


@cache
def do_resample(fname, amount):
    snd_array = pygame.sndarray.array(pygame.mixer.Sound(fname))
    snd_resample = resample(snd_array, amount, "sinc_fastest").astype(snd_array.dtype)
    return pygame.sndarray.make_sound(snd_resample)


@dataclass
class Sound:
    channel: int
    fname: str
    sound: pygame.mixer.Sound
    slider = None
    volume = 1

    def resample(self, _):
        scale = 2 ** (1 / 12)
        value = -self.slider.get()
        amount = scale**value
        if value == 0:
            amount = 1
        self.sound = do_resample(self.fname, amount)
        self.sound.set_volume(self.volume)

    def play(self):
        pygame.mixer.Channel(self.channel).play(self.sound)

    def stop(self):
        self.sound.stop()

    def set_volume(self, volume):
        self.sound.set_volume(volume)
        self.volume = volume  # this is set to preserve volume when changing pitch


sounds = [
    Sound(idx, fname, pygame.mixer.Sound(fname)) for (idx, fname) in enumerate(SOUNDS)
]


WIDTH = 16
HEIGHT = len(SOUNDS)


@dataclass
class Timer:
    count: int = 0

    def increment(self):
        self.count += 1
        self.count = self.count % WIDTH
        for j in range(HEIGHT):
            c = GRID[j][self.count]
            if c.state:
                sounds[j].stop()
                sounds[j].play()
        for j in range(HEIGHT):
            BUTTONS[j][self.count - 1].config(highlightbackground="black")
            BUTTONS[j][self.count].config(highlightbackground="red")
        root.after(500 // 4, self.increment)


@dataclass
class Cell:
    state: bool = False
    velocity: float = 1
    shift: float = 0


GRID = [[Cell() for _ in range(WIDTH)] for _ in range(HEIGHT)]
BUTTONS = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]


def update_button(i, j):
    c = GRID[j][i]
    b = BUTTONS[j][i]
    if c.state:
        b.config(bg="yellow")
        b.config(text="on")
    else:
        b.config(bg="black")
        b.config(text="off")


def on_button_click(i, j):
    c = GRID[j][i]
    b = BUTTONS[j][i]
    c.state = not c.state
    if c.state:
        b.config(bg="yellow")
        b.config(text="on")
        sounds[j].play()
    else:
        b.config(bg="black")
        b.config(text="off")


def change_volume(value, j):
    sounds[j].set_volume(value / 100)


def fname_to_label(fname):
    fname = fname.rstrip(".wav")
    fname = fname.rstrip(".flac")
    while "/" in fname:
        idx = fname.find("/")
        fname = fname[idx + 1 :]
    return fname


root = tk.Tk()
root.title("Drum Machine")


def setup_grid():
    # Create a grid of buttons
    for j in range(HEIGHT):
        row = tk.Frame(root)  # Create a new frame for each row
        frame_left = tk.Frame(row)
        label = tk.Label(frame_left, text=fname_to_label(SOUNDS[j]), width=10)
        label.pack(pady=0)
        slider = tk.Scale(
            frame_left,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda value, j=j: change_volume(int(value), j),
            width=10,
            bg="black",
            fg="red",
            sliderrelief="flat",
        )
        slider.set(50)
        slider.pack(pady=0)
        pitch = tk.Scale(
            frame_left,
            from_=-12,
            to=12,
            showvalue=False,
            orient=tk.HORIZONTAL,
            width=10,
            bg="black",
            fg="red",
            sliderrelief="flat",
        )
        pitch.set(0)
        pitch.pack(pady=0)
        the_sound = sounds[j]
        the_sound.slider = pitch
        pitch.bind("<ButtonRelease-1>", the_sound.resample)

        frame_left.pack(side=tk.LEFT)
        for i in range(WIDTH):
            button = tk.Button(
                row,
                text="Off",
                command=lambda i=i, j=j: on_button_click(i, j),
                width=10,
                height=2,
            )
            BUTTONS[j][i] = button
            button.pack(side=tk.LEFT)  # Pack buttons to the left within the frame
        row.pack()  # Pack the row frame into the root window
    for j in range(HEIGHT):
        for i in range(WIDTH):
            update_button(i, j)


setup_grid()


def load_file(_):
    with open(".seeqer_save.db", "r") as fin:
        d = defaultdict(bool)
        for idx, line in enumerate(fin):
            for jdx, c in enumerate(line.strip()):
                print(idx, jdx, c)
                d[jdx, idx] = int(c)
    print(d)
    for j in range(HEIGHT):
        for i in range(WIDTH):
            GRID[j][i].state = d[i, j]
            if d[i, j]:
                print("ACTIVATE", idx, jdx)
            update_button(i, j)


def serialize(_):
    with open(".seeqer_save.db", "w") as fout:
        for j in range(HEIGHT):
            for i in range(WIDTH):
                c = GRID[j][i]
                print(1 if c.state else 0, end="", file=fout)
            print(file=fout)


def quit_app(_):
    root.destroy()


root.bind("<KeyPress-q>", quit_app)
root.bind("<KeyPress-s>", serialize)
root.bind("<KeyPress-l>", load_file)

timer = Timer()

timer.increment()  # Start the counter
root.mainloop()
