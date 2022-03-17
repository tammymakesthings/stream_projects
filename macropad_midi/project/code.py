# SPDX-FileCopyrightText: Copyright (c) 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

##########################################################################################
# TO-DO LIST:
# - MIDI stuff
#   - [X] Send a MIDI on event on a key press
#   - [X] Send a MIDI off event on a key release
#   - [X] Light up buttons while they're being pressed
#   - [X] Screen to display note and the encoder
#   - [X] Send a MIDI Pitch Bend  message with knob
#   - [ ] Send a MIDI CC message with encoder switch
# Other Stuff
#   - [X] Read the sensors
#   - [ ] Temperature value to pitch-bend
#   - [X] IMU sensor to MIDI messages
#   - [X] Redo UI with DisplayIO
#   - [ ] Redo UI and sensor code with asyncio
#   - [ ] Refactoring
#########################################################################################

try:
    from typing import Optional, Union
except ImportError:
    pass


# Setup Code
import time
import board
import math
from micropython import const

from adafruit_macropad import MacroPad
from rainbowio import colorwheel
import terminalio

import displayio
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_text import label

import adafruit_icm20x
import adafruit_bmp280

MIDI_NOTES: List[int, ...] = [57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68]
MIDI_NOTE_VELOCITY: int = 120

KEY_NONE: int = const(0)
KEY_PRESSED: int = const(1)
KEY_RELEASED: int = const(2)


##############################################################################
# Helper Routines
##############################################################################

def build_ui(display: displayio.Display = board.DISPLAY) -> List[
    displayio.Group, # Root group
    label.Label,     # Note label
    label.Label,     # Encoder label
    label.Label      # Switch label
    ]:

    """
    Build the MacroPad MIDI User Interface

    Args:
        display (displayio.Display, optional): The display object. 
        Defaults to board.DISPLAY.

    Returns:
        List[displayio.Group, label.Label, label.Label, label.Label]: The result list.
            [0]: displayio.Group  - The splash group
            [1]: label.Label - The note value label
            [2]: label.Label - The encoder value label
            [3]: label.Label - The encoder switch label
    """

    splash = displayio.Group()
    display.show(splash)

    title_group = displayio.Group()
    title_group_bg = RoundRect(0, 0, 128, 15, 5, fill=0xffffff)
    title_group.append(title_group_bg)
    title_label = label.Label(
        terminalio.FONT, 
        text="=| MacroPad MIDI |=",
        color=0x000000
    )
    title_label.x = 7
    title_label.y = 6
    title_group.append(title_label)

    note_group = displayio.Group()
    note_group.append(RoundRect(0, 23, 55, 12, 5, fill=0xffffff))
    note_caption_label = label.Label(
        terminalio.FONT, 
        text="Note:", 
        color=0x000000
    )
    note_caption_label.anchor_point = (1.0, 0.5)
    note_caption_label.anchored_position = (55, 28)
    note_group.append(note_caption_label)

    note_text_label = label.Label(
        terminalio.FONT, 
        text="ON C#3", 
        color=0xffffff
    )
    note_text_label.x = 65
    note_text_label.y = 28
    note_group.append(note_text_label)

    encoder_group = displayio.Group()
    encoder_group.append(RoundRect(0, 37, 55, 12, 5, fill=0xffffff))

    encoder_caption_label = label.Label(
        terminalio.FONT, 
        text="PBend:", 
        color=0x000000
    )
    encoder_caption_label.anchor_point = (1.0, 0.5)
    encoder_caption_label.anchored_position = (55, 41)
    encoder_group.append(encoder_caption_label)
    encoder_text_label = label.Label(
        terminalio.FONT,
        text="-10",
        color=0xffffff
    )
    encoder_text_label.x = 65
    encoder_text_label.y = 41
    encoder_group.append(encoder_text_label)

    encoder_switch_group = displayio.Group()
    encoder_group.append(RoundRect(0, 51, 55, 12, 5, fill=0xffffff))


    encoder_switch_caption_label = label.Label(
        terminalio.FONT, 
        text="EncSw:", 
        color=0x000000
    )
    encoder_switch_caption_label.anchor_point = (1.0, 0.5)
    encoder_switch_caption_label.anchored_position = (56, 56)
    encoder_switch_group.append(encoder_switch_caption_label)

    encoder_switch_text_label = label.Label(
        terminalio.FONT,
        text="Off",
        color=0xffffff
    )
    encoder_switch_text_label.x = 65
    encoder_switch_text_label.y = 56
    encoder_switch_group.append(encoder_switch_text_label)

    splash.append(title_group)
    splash.append(note_group)
    splash.append(encoder_group)
    splash.append(encoder_switch_group)

    return [splash, note_text_label, encoder_text_label, encoder_switch_text_label]

def handle_key_event(
    event_type: int, 
    key_number: int, 
    velocity: int = MIDI_NOTE_VELOCITY
    ) -> None:

    """
    Handle a keyboard event.

    Args:
        event_type (int): The event type. KEY_PRESSED, KEY_RELEASED, or KEY_NONE.
        key_number (int): The pressed key number (0-12)
        velocity (int): The pressed key velocity. Defaults to MIDI_NOTE_VELOCITY.
    """

    global key_event_description, macropad

    if event_type == KEY_PRESSED:
        key_event_description = "ON  {}".format(key)
        color_index = int(255 / 12) * key
        macropad.pixels[key] = colorwheel(color_index)
        macropad.midi.send(macropad.NoteOn(MIDI_NOTES[key], velocity))
        print("Sent MIDI Note ON message for note number {}".format(
            MIDI_NOTES[key]
            )
        )
    elif event_type == KEY_RELEASED:
        macropad.pixels.fill((0, 0, 0))
        key_event_description = "OFF {}".format(key)
        macropad.midi.send(macropad.NoteOff(MIDI_NOTES[key], 0))
        print("Sent MIDI Note OFF message for note number {}".format(
            MIDI_NOTES[key]
            )
        )
    else:
        key_event_description = "---"

def last_key_event_type() -> int:
    """
    Get the type of the last key event.

    This currently works by parsing the key event description. Should probably
    be refactored.

    Returns:
        int: The key event type (KEY_PRESSED, KEY_RELEASED, KEY_NONE),
    """

    global key_event_description
    if key_event_description and (len(key_event_description) > 3):
        if key_event_description[0:3].upper() == 'OFF':
            return KEY_RELEASED
        elif key_event_description[0:2].upper() == 'ON':
            return KEY_PRESSED
        else:
            return KEY_NONE
    
##############################################################################
# Global Variables
##############################################################################

macropad: MacroPad = MacroPad()

i2c_bus = board.I2C()   # uses board.SCL and board.SDA
imu_sensor = adafruit_icm20x.ICM20649(i2c_bus)
temp_sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c_bus)

splash: Optional[displayio.Group] = None
note_label: Optional[label.Label] = None
note_label: Optional[label.Label] = None
note_label: Optional[label.Label] = None

key_event_description: str = "---"

encoder_val: int = 0
encoder_sw: bool = False
pitch_bend: Union[int, float] = 0
last_note_time: float = 0

accel_x, accel_y, accel_z  = 0.0, 0.0, 0.0
gyro_x, gyro_y, gyro_z = 0.0, 0.0, 0.0

temp = 0.0
pressure = 0.0
altitude = 0.0

last_accel_x, last_accel_y, last_accel_z  = 0.0, 0.0, 0.0
last_gyro_x, last_gyro_y, last_gyro_z  = 0.0, 0.0, 0.0
note_velocity: int = 0

##############################################################################
# Application Setup
##############################################################################

last_encoder_position: int = macropad.encoder
splash, note_label, encoder_label, encoder_switch_label = \
    build_ui(board.DISPLAY)

##############################################################################
# Event Loop
##############################################################################

while True:

    last_accel_x, last_accel_y, last_accel_z = imu_sensor.acceleration
    last_gyro_x, last_gyro_y, last_gyro_z = last_gyro_values = imu_sensor.gyro

    temp = temp_sensor.temperature
    pressure = temp_sensor.pressure
    altitude = temp_sensor.altitude
    
    accel_x = (accel_x * 0.9) + (last_accel_x * 0.1)
    accel_y = (accel_y * 0.9) + (last_accel_y * 0.1)
    accel_z = (accel_z * 0.9) + (last_accel_z * 0.1)

    gyro_x = (gyro_x * 0.9) + (last_gyro_x * 0.1)
    gyro_y = (gyro_y * 0.9) + (last_gyro_y * 0.1)
    gyro_z = (gyro_z * 0.9) + (last_gyro_z * 0.1)

    note_velocity = math.fabs(accel_x) * 1000 + math.fabs(accel_y) * 1000
    note_velocity = int(note_velocity / 15.0)
    note_velocity = 127 - note_velocity

    if note_velocity < 0:
        note_velocity = 0
    if note_velocity > 127:
        note_velocity = 127

    while macropad.keys.events:
        key_event = macropad.keys.events.get()
        if key_event:
            key = key_event.key_number
            last_note_time = time.monotonic()

            if key_event.pressed:
                handle_key_event(KEY_PRESSED, key)
            elif key_event.released:
                handle_key_event(KEY_RELEASED, key)

    if (time.monotonic() > last_note_time + 0.75) and \
        (last_key_event_type() == KEY_RELEASED):
        key_event_description = "---"
    
    encoder_val = macropad.encoder
    if encoder_val is not last_encoder_position:
        encoder_change = encoder_val - last_encoder_position
        last_encoder_position = encoder_change
        pitch_bend = min(max(pitch_bend + encoder_change, 0), 15)
        print("Sending MIDI pitch bend = {}".format(pitch_bend * 1024))
        macropad.midi.send(macropad.PitchBend(pitch_bend * 1024))

    encoder_sw = macropad.encoder_switch

    note_label.text = key_event_description
    encoder_label.text = str(pitch_bend * 1024)
    encoder_switch_label.text = "* ON *" if encoder_sw else "OFF"
