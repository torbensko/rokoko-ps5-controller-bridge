# Rokoko Controller Bridge

Triggers Rokoko Studio suit calibration from a PlayStation controller button during motion capture sessions in iClone 8.

iClone handles most controller inputs (Record, Stop, etc.) through its own Hotkey Manager. This script runs alongside it to cover what iClone can't do natively — sending calibration commands to Rokoko Studio via its HTTP API. Both can read from the same controller simultaneously on Windows.

## Setup

**Requirements:** Python 3, a PlayStation controller (USB or Bluetooth), and Rokoko Studio with the Command API enabled.

Install the dependency:

```
pip install pygame
```

## Usage

```
python controller_bridge.py
```

Press **Triangle** to trigger a calibration with a 3-second countdown. The script debounces presses (5-second cooldown) to prevent accidental double-triggers.

Make sure there is no button overlap between this script and iClone's hotkey mappings.

## Configuration

These constants at the top of `controller_bridge.py` can be adjusted:

| Constant | Default | Description |
|---|---|---|
| `ROKOKO_API_KEY` | `"1234"` | Rokoko Studio Command API key |
| `CALIBRATE_BUTTON` | `3` (Triangle) | PlayStation button index to listen for |
| `DEBOUNCE_SECONDS` | `5` | Cooldown between accepted presses |

If Triangle isn't registering correctly, press buttons while the script is running — pygame will report the button index, which you can use to update `CALIBRATE_BUTTON`.
