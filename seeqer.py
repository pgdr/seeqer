import sys
from functools import cache
from collections import defaultdict
from dataclasses import dataclass
import json
from samplerate import resample
import multiprocessing
import random
import tkinter as tk
from tkinter import font
import pygame

GOD = None


class God:

    def __init__(self):
        self.BPM = 120
        self.global_bpm_slider = None
        self.VOLUME = 100
        self.global_volume_slider = None
        self.PATTERN = 1
        self.pattern_label = None
        self.height = 2
        self.width = 16
        self.grid = None
        self.buttons = None
        self.timer = None

        try:
            with open("sounds.txt", "r") as fin:
                self.SOUNDS = [line.strip() for line in fin if line.strip()]
        except FileNotFoundError:
            exit("sounds.txt must contain a list of sound files, one per line")


@cache
def do_resample(fname, amount):
    snd_array = pygame.sndarray.array(pygame.mixer.Sound(fname))
    snd_resample = resample(snd_array, amount, "sinc_fastest").astype(snd_array.dtype)
    return pygame.sndarray.make_sound(snd_resample)


# preprocessing samples
def _preprocess_sounds():
    scale = 2 ** (1 / 12)
    for fname in GOD.SOUNDS:
        for value in range(-12, 13):
            amount = scale**value
            if value == 0:
                amount = 1
            print("processing", fname, value, end="...")
            do_resample(fname, amount)
            print("done")


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
    envelope_start = 0
    envelope_maxtime = None

    def resample(self, _):
        scale = 2 ** (1 / 12)
        value = -self.pitch_slider.get()
        amount = scale**value
        if value == 0:
            amount = 1
        self.sound = do_resample(self.fname, amount)
        self.sound.set_volume(self.volume * GOD.VOLUME / 100)

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
        if self.envelope_maxtime is None:
            self.envelope_maxtime = round(self.sound.get_length() * 1000)
        pygame.mixer.Channel(self.channel).play(
            self.sound, maxtime=self.envelope_maxtime, fade_ms=self.envelope_start
        )

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
        self.sound.set_volume(self.volume_ * GOD.VOLUME / 100)
        if self.volume_slider.get() != self.volume_:
            self.volume_slider.set(self.volume_ * 100)


def change_bpm(bpm):
    GOD.BPM = bpm
    if GOD.global_bpm_slider.get() != bpm:
        GOD.global_bpm_slider.set(bpm)


def change_global_volume(volume):
    GOD.VOLUME = volume
    for sound in GOD.sounds:
        sound.volume = None
    if GOD.global_volume_slider.get() != volume:
        GOD.global_volume_slider.set(volume)


def do_play(sound):
    # sound.stop()
    sound.fadeout(5)
    sound.play()


def bpm_to_ms():
    return 60000 // (4 * GOD.BPM)


@dataclass
class Timer:
    count: int = 0
    run: bool = True

    def _schedule(self, when, what, args=None):
        if not self.run:
            return
        if args is None:  # TODO should use sentinel
            GOD.root.after(when, what)
            return
        GOD.root.after(when, what, args)

    def toggle(self):
        self.run = not self.run

    def increment(self):
        self._schedule(bpm_to_ms(), self.increment)
        self.count += 1
        self.count = self.count % GOD.width
        for j in range(GOD.height):
            c = GOD.grid[j][(self.count + 2) % GOD.width]
            if c.state:
                eps = round(random.gauss(0, GOD.sounds[j].timing / 8))
                self._schedule(bpm_to_ms() + eps, do_play, GOD.sounds[j])
        for j in range(GOD.height):
            GOD.buttons[j][self.count - 1].config(highlightbackground="black")
            GOD.buttons[j][self.count].config(highlightbackground="red")


def toggle_run(_):
    GOD.timer.toggle()
    if GOD.timer.run:
        GOD.timer.increment()


@dataclass
class Cell:
    state: bool = False
    velocity: float = 1
    shift: float = 0


def update_button(i, j):
    c = GOD.grid[j][i]
    b = GOD.buttons[j][i]
    if c.state:
        b.config(bg="yellow")
        b.config(text="")
    else:
        b.config(bg="black")
        b.config(text="")


def on_button_click(i, j):
    c = GOD.grid[j][i]
    b = GOD.buttons[j][i]
    c.state = not c.state
    if c.state:
        b.config(bg="yellow")
        b.config(text="")
        GOD.sounds[j].play()
    else:
        b.config(bg="black")
        b.config(text="")


def change_volume(value, j):
    GOD.sounds[j].volume = value / 100


def pattern(shift):
    GOD.PATTERN = max(GOD.PATTERN + shift, 1)
    GOD.pattern_label.config(text=f"{GOD.PATTERN}")


def pattern_left():
    pattern(-1)


def pattern_right():
    pattern(1)


def fname_to_label(fname):
    fname = fname.rstrip(".wav")
    fname = fname.rstrip(".flac")
    while "/" in fname:
        idx = fname.find("/")
        fname = fname[idx + 1 :]
    label = [e for e in fname if e.isalpha()]
    return "".join(label)[:12]  # 12 ought to be enough


def setup_grid(god):
    # Create a grid of buttons
    for j in range(god.height):
        row = tk.Frame(god.root)  # Create a new frame for each row
        the_sound = god.sounds[j]
        frame_left = tk.Frame(row)
        label = tk.Label(frame_left, text=fname_to_label(god.SOUNDS[j]), width=10)
        label.pack(pady=0)

        tiny_font = font.Font(size=6)

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
        for i in range(god.width):
            button = tk.Button(
                row,
                text="",
                command=lambda i=i, j=j: on_button_click(i, j),
                width=3,
                height=2,
            )
            god.buttons[j][i] = button
            button.pack(side=tk.LEFT)  # Pack buttons to the left within the frame
        row.pack()  # Pack the row frame into the root window
    for j in range(god.height):
        for i in range(god.width):
            update_button(i, j)

    # ADD GLOBAL PARAMS
    row = tk.Frame(god.root)  # Create a new frame for each row
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
    god.global_bpm_slider = bpmslider
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
    god.global_volume_slider = volslider
    volslider.set(100)
    volslider.pack(pady=0)

    left_arrow = tk.Button(frame_left, text="←", command=pattern_left)
    left_arrow.pack(side=tk.LEFT)

    pattern_label = tk.Label(frame_left, text="1", width=1, font=("Arial", 14))
    pattern_label.pack(side=tk.LEFT, padx=5)
    god.pattern_label = pattern_label

    right_arrow = tk.Button(frame_left, text="→", command=pattern_right)
    right_arrow.pack(side=tk.LEFT)

    frame_left.pack()
    row.pack()


def load_file(_):
    with open(".seeqer_save.json", "r") as fin:
        d = json.load(fin)
        change_global_volume(d["volume"])
        change_bpm(d["bpm"])
        for idx, sound in enumerate(GOD.sounds):
            s = d["sounds"][sound.fname]
            sound.timing = s["timing"]
            sound.volume = s["volume"]
            sound.pitch = s["pitch"]
    for j in range(GOD.height):
        sound = d["sounds"][GOD.sounds[j].fname]
        for i in range(GOD.width):
            try:
                GOD.grid[j][i].state = sound["pattern"][i]
            except IndexError:
                GOD.grid[j][i].state = False
            update_button(i, j)
    GOD.root.update_idletasks()


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
    global PATTERN
    if PATTERN == 1:
        with open(".seeqer_save.json", "w") as fout:
            json.dump(data, fout)
    else:
        with open(f".seeqer_save.json{PATTERN}", "w") as fout:
            json.dump(data, fout)


def quit_app(_):
    GOD.root.destroy()


def clear(_):
    for j in range(GOD.height):
        for i in range(GOD.width):
            GOD.grid[j][i].state = False
            update_button(i, j)


def key_press(j):
    j = j - 1

    def toggle_button(_):
        i = GOD.timer.count
        c = GOD.grid[j][i]
        c.state = not c.state
        update_button(i, j)

    return toggle_button


def main():
    pygame.mixer.init()
    god = God()
    global GOD
    GOD = god
    pygame.mixer.set_num_channels(len(god.SOUNDS) + 1)
    god.sounds = [
        Sound(idx, fname, pygame.mixer.Sound(fname))
        for (idx, fname) in enumerate(god.SOUNDS)
    ]

    multiprocessing.set_start_method("fork")
    god.heavy_process = multiprocessing.Process(target=_preprocess_sounds)
    god.heavy_process.start()

    god.width = 16
    if len(sys.argv) == 2:
        god.width = int(sys.argv[1])
    god.height = len(god.SOUNDS)
    god.timer = Timer()
    god.grid = [[Cell() for _ in range(god.width)] for _ in range(god.height)]
    god.buttons = [[None for _ in range(god.width)] for _ in range(god.height)]

    root = tk.Tk()
    root.title("Drum Machine")

    god.root = root

    setup_grid(god)

    root.bind("<KeyPress-q>", quit_app)
    root.bind("<KeyPress-s>", serialize)
    root.bind("<KeyPress-l>", load_file)
    root.bind("<KeyPress-c>", clear)
    root.bind("<KeyPress-space>", toggle_run)

    for i in range(1, 10):
        root.bind(f"<KeyPress-{i}>", key_press(i))
    root.bind(f"<KeyPress-{0}>", key_press(10))

    god.timer.increment()  # Start the counter
    root.mainloop()


if __name__ == "__main__":
    main()
