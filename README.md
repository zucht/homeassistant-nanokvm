# Sipeed NanoKVM Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This integration allows you to control and monitor your [Sipeed NanoKVM](https://github.com/sipeed/NanoKVM) device from Home Assistant.

## Features

- Monitor device status (power LED, HDD LED, etc.)
- Control virtual devices (network, disk)
- Toggle system settings (SSH, mDNS)
- Push hardware buttons (power, reset)
- Paste text via HID keyboard simulation
- Control OLED display settings
- Monitor and control mounted images

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL `https://github.com/Wouter0100/homeassistant-nanokvm`
   - Select "Integration" as the category
   - Click "Add"
3. Search for "Sipeed NanoKVM" in HACS and install it
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/Wouter0100/homeassistant-nanokvm/releases)
2. Extract the `nanokvm` folder from the archive
3. Copy the folder to your Home Assistant's `custom_components` directory
4. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Sipeed NanoKVM"
4. Enter your NanoKVM's IP address or hostname, username, and password

## Entities

### Binary Sensors

- **Power LED**: Shows the state of the power LED
- **HDD LED**: Shows the state of the HDD LED (Alpha hardware only)
- **Virtual Network Device**: Shows if the virtual network device is enabled
- **Virtual Disk Device**: Shows if the virtual disk device is enabled
- **SSH Enabled**: Shows if SSH is enabled
- **mDNS Enabled**: Shows if mDNS is enabled
- **OLED Present**: Shows if an OLED display is present
- **WiFi Supported**: Shows if WiFi is supported
- **WiFi Connected**: Shows if WiFi is connected
- **CD-ROM Mode**: Shows if the mounted image is in CD-ROM mode

### Sensors

- **HID Mode**: Shows the current HID mode
- **OLED Sleep Timeout**: Shows the OLED sleep timeout in seconds
- **Hardware Version**: Shows the hardware version
- **Application Version**: Shows the application version
- **Mounted Image**: Shows the currently mounted image

### Switches

- **SSH**: Toggle SSH on/off
- **mDNS**: Toggle mDNS on/off
- **Virtual Network**: Toggle virtual network device on/off
- **Virtual Disk**: Toggle virtual disk device on/off

### Buttons

- **Power Button**: Push the power button
- **Reset Button**: Push the reset button
- **Reboot System**: Reboot the NanoKVM device
- **Reset HDMI**: Reset the HDMI connection (PCIe version only)
- **Reset HID**: Reset the HID subsystem
- **Update Application**: Update the NanoKVM application

## Services

- **nanokvm.push_button**: Simulate pushing a hardware button
- **nanokvm.paste_text**: Paste text via HID keyboard simulation
- **nanokvm.reboot**: Reboot the NanoKVM device
- **nanokvm.reset_hdmi**: Reset the HDMI connection
- **nanokvm.reset_hid**: Reset the HID subsystem
- **nanokvm.wake_on_lan**: Send a Wake-on-LAN packet

## Example Automations

### Push Power Button When Home Assistant Starts

```yaml
automation:
  - alias: "Push NanoKVM Power Button on HA Start"
    trigger:
      - platform: homeassistant
        event: start
    action:
      - service: nanokvm.push_button
        data:
          button_type: power
          duration: 100
```

### Paste Text on Schedule

```yaml
automation:
  - alias: "Paste Login Credentials Daily"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: nanokvm.paste_text
        data:
          text: "username\npassword\n"
```

## Troubleshooting

- If you can't connect to your NanoKVM device, make sure the IP address/hostname is correct and that the device is reachable from your Home Assistant instance.
- If authentication fails, verify your username and password.
- If entities are missing, try restarting Home Assistant.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Sipeed](https://sipeed.com/) for creating the NanoKVM device
- [puddly](https://github.com/puddly) for creating the python-nanokvm library
