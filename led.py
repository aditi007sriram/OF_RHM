import atexit
import time

PIN_MUTATION = 17   # yellow LED — fires on every scheduled IP rotation
PIN_ATTACK   = 27   # red LED   — fires 3x when a scan is detected

# Pi 5 uses lgpio; Pi 4 and earlier use RPi.GPIO.
# If neither is available (e.g. running on a laptop) we just print to stdout.
_gpio = None

try:
    import lgpio
    _h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(_h, PIN_MUTATION)
    lgpio.gpio_claim_output(_h, PIN_ATTACK)
    _gpio = 'lgpio'
except Exception:
    try:
        import RPi.GPIO as _RPiGPIO
        _RPiGPIO.setmode(_RPiGPIO.BCM)
        _RPiGPIO.setup(PIN_MUTATION, _RPiGPIO.OUT, initial=_RPiGPIO.LOW)
        _RPiGPIO.setup(PIN_ATTACK,   _RPiGPIO.OUT, initial=_RPiGPIO.LOW)
        _gpio = 'rpigpio'
    except Exception:
        pass   # not on a Pi — LED calls become no-ops


def _set(pin, high):
    if _gpio == 'lgpio':
        lgpio.gpio_write(_h, pin, 1 if high else 0)
    elif _gpio == 'rpigpio':
        _RPiGPIO.output(pin, _RPiGPIO.HIGH if high else _RPiGPIO.LOW)


def _blink(pin, times, on_ms, off_ms):
    for _ in range(times):
        _set(pin, True)
        time.sleep(on_ms / 1000)
        _set(pin, False)
        time.sleep(off_ms / 1000)


def pulse_mutation():
    """Single 600 ms blink on yellow LED — scheduled IP rotation."""
    if _gpio:
        _blink(PIN_MUTATION, times=1, on_ms=600, off_ms=0)
    else:
        print("\033[93m[LED] MUTATION — yellow pulse\033[0m")


def pulse_attack():
    """Three rapid blinks on red LED — scan detected, emergency rotation."""
    if _gpio:
        _blink(PIN_ATTACK, times=3, on_ms=200, off_ms=100)
    else:
        print("\033[91m[LED] ATTACK DETECTED — red x3\033[0m")


def cleanup():
    if _gpio == 'lgpio':
        lgpio.gpio_write(_h, PIN_MUTATION, 0)
        lgpio.gpio_write(_h, PIN_ATTACK, 0)
        lgpio.gpiochip_close(_h)
    elif _gpio == 'rpigpio':
        _RPiGPIO.cleanup()


atexit.register(cleanup)
