# Rokoko Controller Bridge

Maps PlayStation controller buttons to actions during motion capture sessions in iClone 8 with Rokoko Studio.

iClone's Hotkey Manager handles most controller inputs, but some actions aren't exposed as hotkeys. This script runs alongside iClone to fill the gaps — triggering Rokoko calibration via its HTTP API and clicking the Motion LIVE Record button via screen automation. Both can read from the same controller simultaneously on Windows.

## Setup

**Requirements:** Python 3, a PlayStation controller (USB or Bluetooth), and Rokoko Studio with the Command API enabled.

Install dependencies:

```
pip install pygame pyautogui opencv-python
```

## Usage

```
python controller_bridge.py
```

| Button | Action |
|---|---|
| **Triangle** | Rokoko calibration (3-second countdown) |
| **Cross (X)** | Click Motion LIVE Record button |

All presses are debounced with a 5-second cooldown to prevent accidental double-triggers. Make sure there is no button overlap between this script and iClone's hotkey mappings.

## Configuration

These constants at the top of `controller_bridge.py` can be adjusted:

| Constant | Default | Description |
|---|---|---|
| `ROKOKO_API_KEY` | `"1234"` | Rokoko Studio Command API key |
| `CALIBRATE_BUTTON` | `3` (Triangle) | Button for Rokoko calibration |
| `RECORD_BUTTON` | `0` (Cross) | Button for Motion LIVE Record click |
| `DEBOUNCE_SECONDS` | `5` | Cooldown between accepted presses |

If buttons aren't mapping correctly, press them while the script is running — pygame will report the button index, which you can use to update the constants.

The Record action works by locating `record_button.png` on screen and clicking it. If the Motion LIVE panel isn't visible, the click will be skipped with an error message.
