from functools import cache
from collections import defaultdict
from dataclasses import dataclass
import json
from samplerate import resample
from multiprocessing import Process
import random
import tkinter as tk
import pygame

pygame.mixer.init()


with open("sounds.json", "r") as file:
    data = json.load(file)
SOUNDS = data["sounds"]

pygame.mixer.set_num_channels(len(SOUNDS) + 1)

BPM = 120
VOLUME = 100


@cache
def do_resample(fname, amount):
    snd_array = pygame.sndarray.array(pygame.mixer.Sound(fname))
    snd_resample = resample(snd_array, amount, "sinc_fastest").astype(snd_array.dtype)
    return pygame.sndarray.make_sound(snd_resample)


# preprocessing samples
def _preprocess_sounds():
    scale = 2 ** (1 / 12)
    for fname in SOUNDS:
        for value in range(-12, 13):
            amount = scale**value
            if value == 0:
                amount = 1
            print("processing", fname, value, end="...")
            do_resample(fname, amount)
            print("done")


heavy_process = Process(target=_preprocess_sounds)
heavy_process.start()


@dataclass
class Sound:
    channel: int
    fname: str
    sound: pygame.mixer.Sound
    slider = None
    slider_timing = None
    volume = 1
    timing = 0  # randomized offset (stdev)

    def resample(self, _):
        scale = 2 ** (1 / 12)
        value = -self.slider.get()
        amount = scale**value
        if value == 0:
            amount = 1
        self.sound = do_resample(self.fname, amount)
        self.sound.set_volume(self.volume * VOLUME / 100)

    def update_timing(self, _):
        self.timing = self.slider_timing.get()

    def play(self):
        pygame.mixer.Channel(self.channel).play(self.sound)

    def stop(self):
        self.sound.stop()

    def fadeout(self, ms):
        self.sound.fadeout(ms)

    def set_volume(self, volume=None):
        if volume is not None:
            self.volume = volume  # this is set to preserve volume when changing pitch
        self.sound.set_volume(self.volume * VOLUME / 100)


sounds = [
    Sound(idx, fname, pygame.mixer.Sound(fname)) for (idx, fname) in enumerate(SOUNDS)
]


WIDTH = 16
HEIGHT = len(SOUNDS)


def change_bpm(bpm):
    global BPM
    BPM = bpm


def change_global_volume(volume):
    global VOLUME
    VOLUME = volume
    for sound in sounds:
        sound.set_volume()


def do_play(sound):
    # sound.stop()
    sound.fadeout(5)
    sound.play()


def bpm_to_ms():
    return 60000 // (4 * BPM)


@dataclass
class Timer:
    count: int = 0

    def increment(self):
        root.after(bpm_to_ms(), self.increment)
        self.count += 1
        self.count = self.count % WIDTH
        for j in range(HEIGHT):
            c = GRID[j][(self.count + 2) % WIDTH]
            if c.state:
                eps = round(random.gauss(0, sounds[j].timing/10))
                print(eps)
                root.after(bpm_to_ms() + eps, do_play, sounds[j])
        for j in range(HEIGHT):
            BUTTONS[j][self.count - 1].config(highlightbackground="black")
            BUTTONS[j][self.count].config(highlightbackground="red")


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
        b.config(text="")
    else:
        b.config(bg="black")
        b.config(text="")


def on_button_click(i, j):
    c = GRID[j][i]
    b = BUTTONS[j][i]
    c.state = not c.state
    if c.state:
        b.config(bg="yellow")
        b.config(text="")
        sounds[j].play()
    else:
        b.config(bg="black")
        b.config(text="")


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
            background="red",
            troughcolor="black",
            borderwidth=0,
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
            background="red",
            troughcolor="black",
            borderwidth=0,
            sliderrelief="flat",
        )
        pitch.set(0)
        pitch.pack(pady=0)
        the_sound = sounds[j]
        the_sound.slider = pitch
        pitch.bind("<ButtonRelease-1>", the_sound.resample)

        timing = tk.Scale(
            frame_left,
            from_=0,
            to=100,
            showvalue=False,
            orient=tk.HORIZONTAL,
            width=10,
            background="red",
            troughcolor="black",
            borderwidth=0,
            sliderrelief="flat",
        )
        timing.set(0)
        timing.pack(pady=0)
        the_sound.slider_timing = timing
        timing.bind("<ButtonRelease-1>", the_sound.update_timing)

        frame_left.pack(side=tk.LEFT)
        for i in range(WIDTH):
            button = tk.Button(
                row,
                text="",
                command=lambda i=i, j=j: on_button_click(i, j),
                width=5,
                height=2,
            )
            BUTTONS[j][i] = button
            button.pack(side=tk.LEFT)  # Pack buttons to the left within the frame
        row.pack()  # Pack the row frame into the root window
    for j in range(HEIGHT):
        for i in range(WIDTH):
            update_button(i, j)

    # ADD GLOBAL PARAMS
    row = tk.Frame(root)  # Create a new frame for each row
    frame_left = tk.Frame(row)
    label = tk.Label(frame_left, text="BPM", width=10)
    label.pack(pady=0)
    bpmslider = tk.Scale(
        frame_left,
        from_=40,
        to=240,
        orient=tk.HORIZONTAL,
        command=lambda value: change_bpm(int(value)),
        width=10,
        background="red",
        troughcolor="black",
        borderwidth=0,
        sliderrelief="flat",
    )
    bpmslider.set(120)
    bpmslider.pack(pady=0)

    vollabel = tk.Label(frame_left, text="volume", width=10)
    vollabel.pack(pady=0)

    volslider = tk.Scale(
        frame_left,
        from_=0,
        to=120,
        orient=tk.HORIZONTAL,
        command=lambda value: change_global_volume(int(value)),
        width=10,
        background="red",
        troughcolor="black",
        borderwidth=0,
        sliderrelief="flat",
    )
    volslider.set(100)
    volslider.pack(pady=0)
    frame_left.pack()
    row.pack()


setup_grid()


def load_file(_):
    with open(".seeqer_save.db", "r") as fin:
        d = defaultdict(bool)
        for idx, line in enumerate(fin):
            for jdx, c in enumerate(line.strip()):
                d[jdx, idx] = int(c)
    for j in range(HEIGHT):
        for i in range(WIDTH):
            GRID[j][i].state = d[i, j]
            if d[i, j]:
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


def clear(_):
    for j in range(HEIGHT):
        for i in range(WIDTH):
            GRID[j][i].state = False
            update_button(i, j)


root.bind("<KeyPress-q>", quit_app)
root.bind("<KeyPress-s>", serialize)
root.bind("<KeyPress-l>", load_file)
root.bind("<KeyPress-c>", clear)

timer = Timer()

timer.increment()  # Start the counter
root.mainloop()
