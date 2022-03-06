# SPDX-FileCopyrightText: Copyright (c) 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

##########################################################################################
# TO-DO LIST:
# - MIDI stuff
#   - [ ] Send a MIDI on event on a key press
#   - [ ] Send a MIDI off event on a key release
#   - [X] Light up buttons while they're being pressed
#   - [X] Screen to display note and the encoder
#   - [ ] Send a MIDI CC message with knob
#   - [ ] Send a MIDI CC message with encoder switch
# Other Stuff
#   - [ ] Read the sensor
#   - [ ] Sensor value to pitch-bend
#########################################################################################

try:
    from typing import Optional
except ImportError:
    pass


# Setup Code
from adafruit_macropad import MacroPad
from rainbowio import colorwheel

MIDI_NOTES = [57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68]
MIDI_NOTE_VELOCITY = 120

# Helper Routines


# Global Variables/Setup

macropad = MacroPad()

text_lines = macropad.display_text(title="=|MIDI Controller|=")
key_event_description = "---"
encoder_val = 0
encoder_sw = False

# Event Loop

while True:
    while macropad.keys.events:
        key_event = macropad.keys.events.get()
        if key_event:
            key = key_event.key_number

            if key_event.pressed:
                key_event_description = "PRESS: {}".format(key)
                color_index = int(255 / 12) * key
                macropad.pixels[key] = colorwheel(color_index)
                macropad.midi.send(macropad.NoteOn(MIDI_NOTES[key], MIDI_NOTE_VELOCITY))
                print(
                    "Sent MIDI Note ON message for note number {}".format(
                        MIDI_NOTES[key]
                    )
                )

            if key_event.released:
                macropad.pixels.fill((0, 0, 0))
                key_event_description = "RELEASE: {}".format(key)
                macropad.midi.send(macropad.NoteOff(MIDI_NOTES[key], 0))
                print(
                    "Sent MIDI Note OFF message for note number {}".format(
                        MIDI_NOTES[key]
                    )
                )
        else:
            key_event_description = "---"
    encoder_val = macropad.encoder
    encoder_sw = macropad.encoder_switch

    #    text_lines[0].text = "Note     : {}".format(midi_note)
    text_lines[0].text = key_event_description
    if encoder_sw:
        text_lines[1].text = "*Encoder*: {}".format(encoder_val)
    else:
        text_lines[1].text = "-Encoder-: {}".format(encoder_val)
    text_lines[2].text = ""
    text_lines.show()
