import pygame
import sys
from collections import defaultdict

pygame.init()

SCREEN_WIDTH = 840
SCREEN_HEIGHT = 420
BUTTON_WIDTH = SCREEN_WIDTH // 16
BUTTON_HEIGHT = SCREEN_HEIGHT // 4

TRACKS = ["kick", "snare", "hihat", "ride"]

# Load sound tracks
sounds = {track: pygame.mixer.Sound(f"{track}.flac") for track in TRACKS}

GRID_ROWS = len(TRACKS)
GRID_COLS = 16

BUTTON_COLOR = (100, 100, 250)
HOVER_COLOR = (150, 150, 255)
TEXT_COLOR = (255, 255, 255)
HIGHLIGHT_COLOR = (255, 0, 0)  # Color for highlighted button

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Drum sequencer")

font = pygame.font.Font(None, 24)

bpm = 240  # Beats per minute
time_per_beat = 60 / bpm  # Time per beat in seconds
current_beat = -1  # Current beat index
last_time = pygame.time.get_ticks()  # Track time

buttons = defaultdict(bool)
for col in range(GRID_COLS):
    buttons[(0, col)] = not (col % 8)
    buttons[(1, col)] = not ((4 + col) % 8)
    buttons[(2, col)] = not (col % 2)
    buttons[(3, col)] = col == 0


def draw_buttons():
    # Draw a red highlight rectangle for the current beat column
    highlight_col = current_beat % GRID_COLS
    highlight_rect = pygame.Rect(
        highlight_col * BUTTON_WIDTH, 0, BUTTON_WIDTH, SCREEN_HEIGHT
    )

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            button_rect = pygame.Rect(
                col * BUTTON_WIDTH, row * BUTTON_HEIGHT, BUTTON_WIDTH, BUTTON_HEIGHT
            )
            mouse_pos = pygame.mouse.get_pos()
            is_hovered = button_rect.collidepoint(mouse_pos)

            # Set button color based on its state
            if buttons[(row, col)]:
                color = (255, 255, 0)  # Yellow for active buttons
            else:
                color = (0, 0, 0)  # Black for inactive buttons

            pygame.draw.rect(screen, color, button_rect)

    pygame.draw.rect(screen, HIGHLIGHT_COLOR, highlight_rect, 3)  # Draw red outline


def main():
    global current_beat, last_time
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_pos = pygame.mouse.get_pos()
                    col = mouse_pos[0] // BUTTON_WIDTH
                    row = mouse_pos[1] // BUTTON_HEIGHT
                    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                        buttons[(row, col)] = not buttons[
                            (row, col)
                        ]  # Toggle button state

        # Check elapsed time to advance the current beat
        current_time = pygame.time.get_ticks()
        if (current_time - last_time) / 1000 >= time_per_beat:
            current_beat += 1
            current_beat = current_beat % GRID_COLS
            last_time = current_time

            # Play the sound for the current beat
            for row in range(GRID_ROWS):
                if buttons[(row, current_beat % GRID_COLS)]:
                    sounds[TRACKS[row]].stop()
                    sounds[TRACKS[row]].play()  # Play sound if button is active

        screen.fill((0, 0, 0))  # Clear the screen
        draw_buttons()  # Draw the buttons
        pygame.display.flip()  # Update the display


if __name__ == "__main__":
    main()
