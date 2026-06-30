#!/bin/bash
# Permite usar I2C, SPI, GPIO (gpiod), LEDs onboard y PWM/servo sin sudo.
# Corre esto una sola vez (requiere sudo) y reinicia después.
set -e

echo "Grupos i2c, spi, gpio..."
sudo groupadd -f spi
sudo groupadd -f gpio
sudo usermod -aG i2c,spi,gpio "$USER"

echo "Instalando herramientas gpiod..."
sudo apt install -y gpiod

echo "Reglas udev..."
sudo tee /etc/udev/rules.d/99-spidev.rules > /dev/null << 'EOF'
SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"
EOF

sudo tee /etc/udev/rules.d/99-gpio-pwm.rules > /dev/null << 'EOF'
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
SUBSYSTEM=="pwm", ACTION=="add", RUN+="/bin/chgrp -R gpio /sys%p", RUN+="/bin/chmod -R g+rw /sys%p"
SUBSYSTEM=="leds", ACTION=="add", RUN+="/bin/chgrp -R gpio /sys%p", RUN+="/bin/chmod -R g+rw /sys%p"
EOF

echo "Overlay PWM14 (servo, pin físico 7) y SPI0 (CS0+CS1) en orangepiEnv.txt..."
if grep -q '^overlays=' /boot/orangepiEnv.txt; then
  sudo sed -i 's/^overlays=.*/overlays=i2c2-m0 pwm14-m0 spi0-m2-cs0-cs1-spidev/' /boot/orangepiEnv.txt
else
  echo 'overlays=i2c2-m0 pwm14-m0 spi0-m2-cs0-cs1-spidev' | sudo tee -a /boot/orangepiEnv.txt > /dev/null
fi
grep "overlays=" /boot/orangepiEnv.txt

echo "Servicio systemd que auto-exporta y da permisos al canal PWM en cada arranque..."
sudo tee /etc/systemd/system/pwm-setup.service > /dev/null << 'EOF'
[Unit]
Description=Exporta y da permisos de grupo al canal PWM14 (servo) en cada arranque
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'test -d /sys/class/pwm/pwmchip2/pwm0 || echo 0 > /sys/class/pwm/pwmchip2/export; sleep 0.2; chgrp -R gpio /sys/class/pwm/pwmchip2; chmod -R g+rw /sys/class/pwm/pwmchip2'
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now pwm-setup.service

sudo udevadm control --reload-rules
sudo udevadm trigger

echo
echo "Listo. REINICIA (sudo reboot) para que los grupos nuevos y el overlay PWM14 apliquen."
echo "Nota: pwmchip2 corresponde a PWM14 en esta imagen (Orange Pi 5 Plus, kernel 5.10.110-rockchip-rk3588)."
