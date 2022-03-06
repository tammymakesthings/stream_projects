# SPDX-FileCopyrightText: Copyright (c) 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

##########################################################################################
# TO-DO LIST:
# - MIDI stuff
#   - [ ] Send a MIDI on event on a key press
#   - [ ] Send a MIDI off event on a key release
#   - [ ] Light up buttons while they're being pressed
#   - [ ] Screen to display note and the encoder
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

# Helper Routines


def update_display(
    display_text: macropad.display_text,
    midi_note: str,
    encoder_val: int,
    encoder_sw: bool,
) -> None:
    display_text[0].text = "Note     : {}".format(midi_note)

    if encoder_sw:
        display_text[1].text = "[Encoder]: {}".format(encoder_val)
    else:
        display_text[1].text = "Encoder  : {}".format(encoder_val)

    display_text[2].text = ""
    display_text.show()


# Global Variables/Setup

macropad = MacroPad()
macropad.display.auto_refresh = False

text_lines = macropad.display_text("MIDI Controller")


# Event Loop
key_event_description = "---"
encoder_val = 0
encoder_sw = False

while True:
    while macropad.keys.events:
        key_event = macropad.keys.events.get()
        if key_event:
            key = key_event.key_number

            if key_event.pressed:
                key_event_description = "PRESS: {}".format(key)
            if key_event.released:
                key_event_description = "RELEASE: {}".format(key)
        else:
            key_event_description = "---"
        encoder_val = macropad.encoder
        encoder_sw = macropad.encoder_switch
        update_display(text_lines, key_event_description, encoder_val, encoder_sw)
