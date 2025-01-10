from dataclasses import dataclass
from samplerate import resample

import tkinter as tk
import pygame

pygame.mixer.init()

SOUNDS = [
    "kick.flac",
    "snare.flac",
    "hihat.flac",
    "ride.flac",
    "tom1.flac",
    "tom2.flac",
    "tom3.flac",
    "tom4.flac",
    #
    "am7.wav",
    "bass.wav",
    "wetbass.wav",
    "blue.wav",
    "piano.wav",
    "ultra.wav",
]

pygame.mixer.set_num_channels(len(SOUNDS) + 1)


@dataclass
class Sound:
    channel: int
    fname: str
    sound: pygame.mixer.Sound
    slider = None

    def resample(self, _):
        value = self.slider.get() / 100
        print("resample", value)

        snd_array = pygame.sndarray.array(pygame.mixer.Sound(self.fname))
        snd_resample = resample(snd_array, value, "sinc_fastest").astype(
            snd_array.dtype
        )
        old = self.sound
        self.sound = pygame.sndarray.make_sound(snd_resample)
        self.sound.play()
        del old

    def play(self):
        pygame.mixer.Channel(self.channel).play(self.sound)

    def stop(self):
        self.sound.stop()

    def set_volume(self, volume):
        self.sound.set_volume(volume)


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
    else:
        b.config(bg="black")
        b.config(text="off")
    sounds[j].play()


def change_volume(value, j):
    sounds[j].set_volume(value / 100)


root = tk.Tk()
root.title("Drum Machine")


def setup_grid():
    # Create a grid of buttons
    for j in range(HEIGHT):
        frame = tk.Frame(root)  # Create a new frame for each row
        frame_left = tk.Frame(frame)
        label = tk.Label(frame_left, text=SOUNDS[j], width=10)
        slider = tk.Scale(
            frame_left,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda value, j=j: change_volume(int(value), j),
        )
        slider.set(80)
        slider.pack(side=tk.LEFT)
        pitch = tk.Scale(
            frame_left, from_=0, to=200, showvalue=False, orient=tk.HORIZONTAL
        )
        pitch.set(100)
        pitch.pack(side=tk.LEFT)
        the_sound = sounds[j]
        the_sound.slider = pitch
        pitch.bind("<ButtonRelease-1>", the_sound.resample)

        label.pack(side=tk.LEFT)
        frame_left.pack(side=tk.LEFT)
        for i in range(WIDTH):
            button = tk.Button(
                frame,
                text="Off",
                command=lambda i=i, j=j: on_button_click(i, j),
                width=10,
                height=2,
            )
            BUTTONS[j][i] = button
            button.pack(side=tk.LEFT)  # Pack buttons to the left within the frame
        frame.pack()  # Pack the frame into the root window
    for j in range(HEIGHT):
        for i in range(WIDTH):
            update_button(i, j)


setup_grid()

timer = Timer()

timer.increment()  # Start the counter
root.mainloop()
