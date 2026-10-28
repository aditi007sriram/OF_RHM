import lgpio, time

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, 17)
lgpio.gpio_claim_output(h, 27)

# Yellow LED - single blink (rotation)
lgpio.gpio_write(h, 17, 1)
time.sleep(10)
lgpio.gpio_write(h, 17, 0)

time.sleep(0.5)

# Green/Red LED - 3 blinks (attack)
for _ in range(3):
    lgpio.gpio_write(h, 27, 1)
    time.sleep(0.2)
    lgpio.gpio_write(h, 27, 0)
    time.sleep(0.1)

lgpio.gpiochip_close(h)