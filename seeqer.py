from functools import cache
from collections import defaultdict
from dataclasses import dataclass
import json
from samplerate import resample
from multiprocessing import Process
import random
import tkinter as tk
from tkinter import font
import pygame

pygame.mixer.init()

with open("sounds.json", "r") as file:
    data = json.load(file)
SOUNDS = data["sounds"]

pygame.mixer.set_num_channels(len(SOUNDS) + 1)

BPM = 120
_GLOBAL_BPM_SLIDER = None
VOLUME = 100
_GLOBAL_VOLUME_SLIDER = None


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
    pitch_slider = None
    volume_ = 1
    volume_slider = None
    timing_ = 0  # randomized offset (stdev)
    timing_slider = None

    def resample(self, _):
        scale = 2 ** (1 / 12)
        value = -self.pitch_slider.get()
        amount = scale**value
        if value == 0:
            amount = 1
        self.sound = do_resample(self.fname, amount)
        self.sound.set_volume(self.volume * VOLUME / 100)

    @property
    def timing(self):
        return self.timing_

    @timing.setter
    def timing(self, value):
        self.timing_ = value
        if self.timing_slider.get() != value:
            self.timing_slider.set(value)

    def update_timing(self, _):
        self.timing = self.timing_slider.get()

    def play(self):
        pygame.mixer.Channel(self.channel).play(self.sound)

    @property
    def pitch(self):
        return self.pitch_slider.get()

    @pitch.setter
    def pitch(self, value):
        if self.pitch_slider:
            self.pitch_slider.set(value)
            self.resample(None)

    def stop(self):
        self.sound.stop()

    def fadeout(self, ms):
        self.sound.fadeout(ms)

    @property
    def volume(self):
        return self.volume_

    @volume.setter
    def volume(self, vol=None):
        if vol is not None:
            self.volume_ = vol
        self.sound.set_volume(self.volume_ * VOLUME / 100)
        if self.volume_slider.get() != self.volume_:
            self.volume_slider.set(self.volume_ * 100)


sounds = [
    Sound(idx, fname, pygame.mixer.Sound(fname)) for (idx, fname) in enumerate(SOUNDS)
]


WIDTH = 16
HEIGHT = len(SOUNDS)


def change_bpm(bpm):
    global BPM
    global _GLOBAL_BPM_SLIDER
    BPM = bpm
    if _GLOBAL_BPM_SLIDER.get() != bpm:
        _GLOBAL_BPM_SLIDER.set(bpm)


def change_global_volume(volume):
    global VOLUME
    global _GLOBAL_VOLUM_SLIDER
    VOLUME = volume
    for sound in sounds:
        sound.volume = None
    if _GLOBAL_VOLUME_SLIDER.get() != volume:
        _GLOBAL_VOLUME_SLIDER.set(volume)


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
                eps = round(random.gauss(0, sounds[j].timing / 10))
                root.after(bpm_to_ms() + eps, do_play, sounds[j])
        for j in range(HEIGHT):
            BUTTONS[j][self.count - 1].config(highlightbackground="black")
            BUTTONS[j][self.count].config(highlightbackground="red")


TIMER = Timer()


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
    sounds[j].volume = value / 100


def fname_to_label(fname):
    fname = fname.rstrip(".wav")
    fname = fname.rstrip(".flac")
    while "/" in fname:
        idx = fname.find("/")
        fname = fname[idx + 1 :]
    return fname


root = tk.Tk()
root.title("Drum Machine")
tiny_font = font.Font(size=6)


def setup_grid():
    # Create a grid of buttons
    for j in range(HEIGHT):
        row = tk.Frame(root)  # Create a new frame for each row
        the_sound = sounds[j]
        frame_left = tk.Frame(row)
        label = tk.Label(frame_left, text=fname_to_label(SOUNDS[j]), width=10)
        label.pack(pady=0)

        frame_vol = tk.Frame(frame_left)
        tk.Label(frame_vol, text="V", font=tiny_font).pack(side=tk.LEFT)
        vol_slider = tk.Scale(
            frame_vol,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda value, j=j: change_volume(int(value), j),
            width=5,
            background="red",
            troughcolor="black",
            borderwidth=0,
            sliderrelief="flat",
        )
        vol_slider.set(50)
        vol_slider.pack(pady=0)
        frame_vol.pack()
        the_sound.volume_slider = vol_slider

        frame_pitch = tk.Frame(frame_left)
        tk.Label(frame_pitch, text="P", font=tiny_font).pack(side=tk.LEFT)
        pitch = tk.Scale(
            frame_pitch,
            from_=-12,
            to=12,
            showvalue=False,
            orient=tk.HORIZONTAL,
            width=5,
            background="red",
            troughcolor="black",
            borderwidth=0,
            sliderrelief="flat",
        )
        pitch.set(0)
        pitch.pack(pady=0)
        the_sound.pitch_slider = pitch
        pitch.bind("<ButtonRelease-1>", the_sound.resample)
        frame_pitch.pack()

        frame_time = tk.Frame(frame_left)
        tk.Label(frame_time, text="T", font=tiny_font).pack(side=tk.LEFT)
        timing = tk.Scale(
            frame_time,
            from_=0,
            to=100,
            showvalue=False,
            orient=tk.HORIZONTAL,
            width=5,
            background="red",
            troughcolor="black",
            borderwidth=0,
            sliderrelief="flat",
        )
        timing.set(0)
        timing.pack(pady=0)
        the_sound.timing_slider = timing
        timing.bind("<ButtonRelease-1>", the_sound.update_timing)
        frame_time.pack()

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
    global _GLOBAL_BPM_SLIDER
    _GLOBAL_BPM_SLIDER = bpmslider
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
    global _GLOBAL_VOLUME_SLIDER
    _GLOBAL_VOLUME_SLIDER = volslider
    volslider.set(100)
    volslider.pack(pady=0)
    frame_left.pack()
    row.pack()


setup_grid()


def load_file(_):
    with open(".seeqer_save.json", "r") as fin:
        d = json.load(fin)
        change_global_volume(d["volume"])
        change_bpm(d["bpm"])
        for idx, sound in enumerate(sounds):
            s = d["sounds"][sound.fname]
            sound.timing = s["timing"]
            sound.volume = s["volume"]
            sound.pitch = s["pitch"]
    for j in range(HEIGHT):
        sound = d["sounds"][sounds[j].fname]
        for i in range(WIDTH):
            GRID[j][i].state = sound["pattern"][i]
            update_button(i, j)
    root.update_idletasks()


def serialize(_):
    k = {}
    for idx, sound in enumerate(sounds):
        row = GRID[idx]
        k[sound.fname] = {
            "pattern": [c.state for c in row],
            "timing": sound.timing,
            "volume": sound.volume,
            "pitch": sound.pitch,
        }
    data = {"sounds": k, "bpm": BPM, "volume": VOLUME}
    with open(".seeqer_save.json", "w") as fout:
        json.dump(data, fout)


def quit_app(_):
    root.destroy()


def clear(_):
    for j in range(HEIGHT):
        for i in range(WIDTH):
            GRID[j][i].state = False
            update_button(i, j)


def key_press(j):
    print("press", j)
    j = j - 1

    def toggle_button(_):
        i = TIMER.count
        print("toggle button", j, "@", i)
        c = GRID[j][i]
        c.state = not c.state
        update_button(i, j)

    return toggle_button


root.bind("<KeyPress-q>", quit_app)
root.bind("<KeyPress-s>", serialize)
root.bind("<KeyPress-l>", load_file)
root.bind("<KeyPress-c>", clear)

for i in range(1, 10):
    root.bind(f"<KeyPress-{i}>", key_press(i))
root.bind(f"<KeyPress-{0}>", key_press(10))


TIMER.increment()  # Start the counter
root.mainloop()
