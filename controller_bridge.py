import time
import urllib.request
import urllib.error
import json

try:
    import pygame
except ImportError:
    print("pygame is required. Install it with: pip install pygame")
    raise SystemExit(1)

ROKOKO_API_KEY = "1234"
ROKOKO_BASE_URL = f"http://127.0.0.1:14053/v1/{ROKOKO_API_KEY}"

# PlayStation Triangle button index (typically 3 on DualShock/DualSense via pygame)
CALIBRATE_BUTTON = 3

DEBOUNCE_SECONDS = 5

CALIBRATE_PAYLOAD = json.dumps({
    "countdown_delay": 3,
    "skip_suit": False,
    "skip_gloves": False,
    "use_custom_pose": False,
    "pose": "straight-arms-down",
}).encode("utf-8")

RESPONSE_CODES = {
    0: "OK",
    1: "NO_CALIBRATEABLE_ACTORS",
    3: "CALIBRATION_ALREADY_ONGOING",
    6: "UNEXPECTED_ERROR",
}


def send_calibrate():
    url = f"{ROKOKO_BASE_URL}/calibrate"
    req = urllib.request.Request(
        url,
        data=CALIBRATE_PAYLOAD,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
            code = body.get("response_code")
            desc = body.get("description", "")
            status = RESPONSE_CODES.get(code, f"UNKNOWN ({code})")
            if code == 0:
                print(f"Calibration successful: {desc}")
            else:
                print(f"Calibration response: {status} — {desc}")
    except urllib.error.URLError as e:
        print(f"Error: Rokoko Studio is unreachable — {e.reason}")
    except Exception as e:
        print(f"Error sending calibration request: {e}")


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected. Connect a PlayStation controller and try again.")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Controller connected: {joystick.get_name()}")
    print(f"Triangle (button {CALIBRATE_BUTTON}) → Rokoko calibrate")
    print("Listening for button presses... (Ctrl+C to quit)\n")

    last_trigger_time = 0

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN and event.button == CALIBRATE_BUTTON:
                    now = time.time()
                    if now - last_trigger_time < DEBOUNCE_SECONDS:
                        print("Debounced — ignoring repeated press")
                        continue
                    last_trigger_time = now
                    print("Calibration triggered (3s countdown)...")
                    send_calibrate()
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
