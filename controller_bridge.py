import os
import time
import urllib.request
import urllib.error
import json

try:
    import pygame
except ImportError:
    print("pygame is required. Install it with: pip install pygame")
    raise SystemExit(1)

ICLONE_ENABLED = False

if ICLONE_ENABLED:
    try:
        import pyautogui
    except ImportError:
        print("pyautogui is required. Install it with: pip install pyautogui")
        raise SystemExit(1)

ROKOKO_API_KEY = "1234"
ROKOKO_BASE_URL = f"http://127.0.0.1:14053/v1/{ROKOKO_API_KEY}"

# PlayStation button indices (typical DualShock/DualSense mapping via pygame)
CALIBRATE_BUTTON = 3  # Triangle
RECORD_BUTTON = 0     # Cross (X)
STOP_BUTTON = 1       # Circle

DEBOUNCE_SECONDS = 5

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORD_BUTTON_IMAGE = os.path.join(SCRIPT_DIR, "record_button.png")

RESPONSE_CODES = {
    0: "OK",
    1: "NO_CALIBRATEABLE_ACTORS",
    3: "CALIBRATION_ALREADY_ONGOING",
    4: "RECORDING_ALREADY_STARTED",
    5: "RECORDING_NOT_STARTED",
    6: "UNEXPECTED_ERROR",
}


def rokoko_api(command, payload=None):
    url = f"{ROKOKO_BASE_URL}/{command}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
            code = body.get("response_code")
            desc = body.get("description", "")
            status = RESPONSE_CODES.get(code, f"UNKNOWN ({code})")
            return code, status, desc
    except urllib.error.URLError as e:
        print(f"Error: Rokoko Studio is unreachable — {e.reason}")
        return None, None, None
    except Exception as e:
        print(f"Error sending {command} request: {e}")
        return None, None, None


def send_calibrate():
    code, status, desc = rokoko_api("calibrate", {
        "countdown_delay": 3,
        "skip_suit": False,
        "skip_gloves": False,
        "use_custom_pose": False,
        "pose": "straight-arms-down",
    })
    if code is None:
        return
    if code == 0:
        print(f"Calibration successful: {desc}")
    else:
        print(f"Calibration response: {status} — {desc}")


def rokoko_start_recording():
    code, status, desc = rokoko_api("recording/start", {"filename": ""})
    if code is None:
        return
    if code == 0:
        print(f"Rokoko recording started: {desc}")
    else:
        print(f"Rokoko recording start response: {status} — {desc}")


def rokoko_stop_recording():
    code, status, desc = rokoko_api("recording/stop", {"back_to_live": True})
    if code is None:
        return
    if code == 0:
        print(f"Rokoko recording stopped: {desc}")
    else:
        print(f"Rokoko recording stop response: {status} — {desc}")


def click_record():
    try:
        location = pyautogui.locateCenterOnScreen(RECORD_BUTTON_IMAGE, confidence=0.8)
    except pyautogui.ImageNotFoundException:
        location = None

    if location is None:
        print("Error: Record button not found on screen — is Motion LIVE open?")
        return

    pyautogui.click(location)
    time.sleep(0.1)
    pyautogui.press("space")
    print("Record button clicked")


def main():
    if ICLONE_ENABLED and not os.path.exists(RECORD_BUTTON_IMAGE):
        print(f"Error: Template image not found at {RECORD_BUTTON_IMAGE}")
        return

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected. Connect a PlayStation controller and try again.")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Controller connected: {joystick.get_name()}")
    print(f"Triangle (button {CALIBRATE_BUTTON}) → Rokoko calibrate")
    record_label = "Start recording (iClone + Rokoko)" if ICLONE_ENABLED else "Start Rokoko recording"
    stop_label = "Stop recording (iClone + Rokoko)" if ICLONE_ENABLED else "Stop Rokoko recording"
    print(f"Cross    (button {RECORD_BUTTON}) → {record_label}")
    print(f"Circle   (button {STOP_BUTTON}) → {stop_label}")
    print("Listening for button presses... (Ctrl+C to quit)\n")

    last_calibrate_time = 0
    last_record_time = 0
    last_stop_time = 0

    try:
        while True:
            for event in pygame.event.get():
                if event.type != pygame.JOYBUTTONDOWN:
                    continue
                now = time.time()

                if event.button == CALIBRATE_BUTTON:
                    if now - last_calibrate_time < DEBOUNCE_SECONDS:
                        print("Debounced — ignoring repeated press")
                        continue
                    last_calibrate_time = now
                    print("Calibration triggered (3s countdown)...")
                    send_calibrate()

                elif event.button == RECORD_BUTTON:
                    if now - last_record_time < DEBOUNCE_SECONDS:
                        print("Debounced — ignoring repeated press")
                        continue
                    last_record_time = now
                    rokoko_start_recording()
                    if ICLONE_ENABLED:
                        click_record()

                elif event.button == STOP_BUTTON:
                    if now - last_stop_time < DEBOUNCE_SECONDS:
                        print("Debounced — ignoring repeated press")
                        continue
                    last_stop_time = now
                    rokoko_stop_recording()
                    if ICLONE_ENABLED:
                        pyautogui.press("space")
                        print("iClone stop recording (spacebar pressed)")

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
