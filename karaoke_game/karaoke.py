import sys
import math
import pyglet
from pyglet import shapes, resource
from pyglet.window import key
from utils import read_midi
from audio import MicPitch

window_width = 1400
window_height = 1200
playLineX = 250
pixels_per_second = 100
note_height = 70
margin_note_rows = 3

SPRING_K = 600.0                    
DAMPING = 2.0 * math.sqrt(SPRING_K) 
TARGET_ALPHA = 0.2                  

egg_velocity_y = 0.0

midi_file_path = sys.argv[1] if len(sys.argv) > 1 else "freude.mid"
midi_notes = read_midi(midi_file_path)

lowest_note = min(n[2] for n in midi_notes)
highest_note = max(n[2] for n in midi_notes)
bottom_note_number = lowest_note - margin_note_rows
top_note_number = highest_note + margin_note_rows

def y_position_for_note(midi_number):
    return 100 + (midi_number - bottom_note_number) * (note_height + 3)

def seconds_to_pixels(seconds_value):
    return seconds_value * pixels_per_second

resource.path = ['.']
resource.reindex()

background_image = resource.image('boardbackground.png')
snake_body_image = resource.image('snakebody.png')
snake_head_image = resource.image('snakehead.png')
egg_image = resource.image('coin.png')

window = pyglet.window.Window(window_width, window_height, "Karaoke Game")
main_batch = pyglet.graphics.Batch()

background_tiles = []
for tx in range(0, window_width, background_image.width):
    for ty in range(0, window_height, background_image.height):
        background_tiles.append(pyglet.sprite.Sprite(background_image, x=tx, y=ty))

low_note_zone = shapes.Rectangle(
    0, 0, window_width,
    y_position_for_note(lowest_note),
    color=(180, 60, 60), batch=main_batch
)

high_note_zone = shapes.Rectangle(
    0,
    y_position_for_note(highest_note + 1),
    window_width,
    window_height - y_position_for_note(highest_note + 1),
    color=(180, 60, 60), batch=main_batch
)

play_line = shapes.Rectangle(playLineX - 1, 0, 2, window_height, color=(255, 60, 60), batch=main_batch)

egg_sprite = pyglet.sprite.Sprite(
    egg_image,
    x=playLineX - egg_image.width // 2,
    y=y_position_for_note(lowest_note) + (note_height - egg_image.height) // 2,
    batch=main_batch
)
last_target_y = egg_sprite.y

score_label = pyglet.text.Label(
    "Score: 0.0",
    x=window_width - 10,
    y=window_height - 10,
    anchor_x="right",
    anchor_y="top",
    font_name="Arial",
    font_size=18,
    batch=main_batch
)

bars = []
for start, duration, midi_val in midi_notes:
    w = seconds_to_pixels(duration)
    x0 = window_width + start * pixels_per_second
    y0 = y_position_for_note(midi_val)
    segs = int((w + snake_body_image.width - 1) // snake_body_image.width)
    body = []
    for i in range(segs):
        body.append(pyglet.sprite.Sprite(
            snake_body_image,
            x=x0 + i * snake_body_image.width,
            y=y0 + (note_height - snake_body_image.height)//2,
            batch=main_batch
        ))
    head = pyglet.sprite.Sprite(
        snake_head_image,
        x=x0,
        y=y0 + (note_height - snake_head_image.height)//2,
        batch=main_batch
    )
    bars.append({
        "body": body,
        "head": head,
        "start": start,
        "duration": duration,
        "midi": midi_val,
        "pressed": False
    })

mic = MicPitch()
current_song_time = 0.0
current_score = 0.0

time_to_playline = (window_width - playLineX) / pixels_per_second
song_end_time = max(b["start"] + b["duration"] for b in bars) + time_to_playline

loop_delay = 2.0
end_timestamp = None
is_song_ended = False

def clamp_number(v, lo, hi):
    if v < lo: return lo
    if v > hi: return hi
    return v

def reset_loop():
    global current_song_time, current_score, end_timestamp, is_song_ended
    global egg_velocity_y, last_target_y
    current_song_time = 0.0
    current_score = 0.0
    score_label.text = "Score: 0.0"
    end_timestamp = None
    is_song_ended = False
    egg_velocity_y = 0.0
    last_target_y = y_position_for_note(lowest_note) + (note_height - egg_image.height) // 2
    for b in bars:
        b["pressed"] = False

def update_every_frame(dt):
    global current_song_time, current_score, is_song_ended, end_timestamp
    global egg_velocity_y, last_target_y
    current_song_time += dt

    if is_song_ended:
        if current_song_time - end_timestamp >= loop_delay:
            reset_loop()
        return

    # move bars
    for b in bars:
        nx = window_width + (b["start"] - current_song_time) * pixels_per_second
        for i, spr in enumerate(b["body"]):
            spr.x = nx + i * snake_body_image.width
        b["head"].x = nx

    if mic._smoothed_midi_estimate is not None:
        raw_tgt = clamp_number(
            y_position_for_note(mic._smoothed_midi_estimate),
            y_position_for_note(bottom_note_number),
            y_position_for_note(top_note_number) - note_height
        )
        last_target_y += TARGET_ALPHA * (raw_tgt - last_target_y)

        diff = last_target_y - egg_sprite.y
        accel = SPRING_K * diff - DAMPING * egg_velocity_y
        egg_velocity_y += accel * dt
        egg_sprite.y += egg_velocity_y * dt
        egg_sprite.y = clamp_number(
            egg_sprite.y,
            y_position_for_note(bottom_note_number),
            y_position_for_note(top_note_number) - note_height
        )

    # detect collision
    active_bar = None
    if mic._smoothed_midi_estimate is not None:
        for b in bars:
            bar_y = y_position_for_note(b["midi"]) + (note_height - snake_body_image.height)//2
            bar_h = snake_body_image.height
            bar_x0 = b["body"][0].x
            bar_x1 = b["body"][-1].x + snake_body_image.width
            egg_x0 = egg_sprite.x
            egg_x1 = egg_x0 + egg_image.width
            egg_y0 = egg_sprite.y
            egg_y1 = egg_y0 + egg_image.height

            if (egg_x1 >= bar_x0 and egg_x0 <= bar_x1 and
                egg_y1 >= bar_y and egg_y0 <= bar_y + bar_h and
                abs(mic._smoothed_midi_estimate - b["midi"]) <= 1):
                active_bar = b
                break

    for b in bars:
        if b is active_bar:
            b["pressed"] = True
        else:
            b["pressed"] = False
    
    if active_bar:
        current_score += dt
        score_label.text = f"Score: {current_score:.1f}"

    for b in bars:
        col = (255, 100, 100) if b["pressed"] else (255, 255, 255)
        for spr in b["body"]:
            spr.color = col
        b["head"].color = col

    if current_song_time > song_end_time:
        is_song_ended = True
        end_timestamp = current_song_time

@window.event
def on_draw():
    window.clear()
    for t in background_tiles:
        t.draw()
    main_batch.draw()

@window.event
def on_key_press(symbol, _):
    if symbol == key.ESCAPE:
        mic.close()
        pyglet.app.exit()

pyglet.clock.schedule_interval(update_every_frame, 1/60)
pyglet.app.run()
