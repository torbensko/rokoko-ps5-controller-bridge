# Rokoko Controller Bridge

A background script that listens for PlayStation controller button presses and triggers Rokoko Studio Command API calls via HTTP.

## Context

This is used alongside iClone 8's Motion LIVE plugin for motion capture recording sessions. iClone natively supports gamepad input via its Hotkey Manager, so some buttons are mapped directly in iClone (e.g. Record/Stop). This script handles the remaining buttons that need to trigger Rokoko Studio actions — primarily calibration.

The script and iClone can read from the same controller simultaneously on Windows since gamepad input is not exclusively captured.

**Important: Ensure no button overlap between this script and iClone's hotkey mappings.**

## Requirements

- Python 3 on Windows
- PlayStation controller connected via USB or Bluetooth
- Rokoko Studio running with Command API enabled

## Rokoko Studio Command API

- **Endpoint**: `http://127.0.0.1:14053/v1/{api_key}/{command}`
- **Default API key**: `1234`
- **Protocol**: HTTP POST with JSON body

### Calibrate

```
POST http://127.0.0.1:14053/v1/1234/calibrate
Content-Type: application/json

{
  "countdown_delay": 3,
  "skip_suit": false,
  "skip_gloves": false,
  "use_custom_pose": false,
  "pose": "straight-arms-down"
}
```

Pose options: `tpose`, `straight-arms-down`, `straight-arms-forward`

### Response format

```json
{
  "description": "string",
  "response_code": 0
}
```

Response codes: 0 = OK, 1 = NO_CALIBRATEABLE_ACTORS, 3 = CALIBRATION_ALREADY_ONGOING, 6 = UNEXPECTED_ERROR

## Button Mapping

Map one PlayStation controller button (e.g. Triangle) to trigger the calibrate command. Include a 3-second countdown delay in the API call to give time to get into the calibration pose.

Leave all other buttons unmapped in the script — they'll be handled by iClone's Hotkey Manager.

## Behaviour

- Run as a background process
- Listen for the mapped button press
- Debounce to prevent accidental double-triggers (e.g. ignore presses within 5 seconds of the last trigger)
- Log each action to the console (e.g. "Calibration triggered", "Calibration successful")
- Print an error if Rokoko Studio is unreachable
