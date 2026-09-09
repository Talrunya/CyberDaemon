# CyberDaemon

### Linux control software for the CORSAIR HS80 MAX Wireless

CyberDaemon is a native Linux control suite for the **CORSAIR HS80 MAX Wireless** headset.

The project was created to provide Linux users with a real alternative to the Windows-only control software and to give the HS80 MAX proper integration with the Linux desktop.

> ⚠️ **BETA SOFTWARE**
>
> CyberDaemon is currently in beta. It has been tested on Arch Linux / CachyOS, but other distributions and hardware configurations may behave differently.
>
> Feedback, bug reports and testing are very welcome.

---

## Features

### 🎧 Headset

- CORSAIR HS80 MAX Wireless support
- USB HID communication
- Battery status
- Firmware information
- Microphone mute status
- Hardware status monitoring
- Receiver communication

### 🎚 Equalizer

- Native PipeWire integration
- Real-time EQ control
- Preset support
- Custom EQ settings
- Dynamic headset sink detection
- EQ status monitoring

### 🔊 7.1 Surround

- PipeWire-based surround processing
- HeSuVi / HRIR support
- Automatic audio graph handling
- Surround enable / disable from CyberDaemon
- Designed to work without relying on Windows-only software

### 🎤 Sidetone

- Hardware sidetone control
- Adjustable sidetone level
- Direct HID communication with the headset
- Profile integration

### 💡 RGB Lighting

- RGB control for the headset
- Brightness control
- Color selection
- Preset colors
- Custom RGB colors
- Lighting effects
- Profile integration

### 👤 Profiles

Profiles can store headset settings including:

- Equalizer
- Lighting
- Sidetone
- Surround configuration

Profiles are stored in the user's configuration directory:

```text
~/.config/CyberDaemon/profiles.json



⚙️ Settings
Headset auto power-off timer
Firmware information
Firmware update checking
System integration
🖥 System Integration
Linux system tray
Start with the desktop
Minimize to tray
Profile switching
Tray notifications
Installation
AppImage

The easiest way to test CyberDaemon is the AppImage provided with the beta release.

Download the latest AppImage from the GitHub Releases page.

Make it executable:

chmod +x CyberDaemon-0.1.0-beta-x86_64.AppImage

Then start it:

./CyberDaemon-0.1.0-beta-x86_64.AppImage

CyberDaemon can run in the system tray and can be configured to start automatically with the desktop.

Requirements

CyberDaemon is designed for Linux.

Required
Linux
Python is not required when using the AppImage
CORSAIR HS80 MAX Wireless
USB access to the headset receiver
Audio features

For Equalizer and Surround functionality:

PipeWire
wpctl
pw-cli

For 7.1 surround processing:

HeSuVi-compatible HRIR data

The exact availability of PipeWire tools can vary between Linux distributions.

Supported Hardware

Currently the main target is:

CORSAIR HS80 MAX Wireless

Other CORSAIR devices are currently not guaranteed to work.

Development

CyberDaemon is written in Python using:

Python
PySide6
hidapi
PipeWire
Qt

The project is developed primarily on Arch Linux / CachyOS.

Clone the repository:

git clone https://github.com/Talrunya/CyberDaemon.git
cd CyberDaemon

Install the Python dependencies:

python -m pip install -r requirements.txt

Run CyberDaemon:

python app.py
Building the AppImage

The repository contains the Python AppImage build script:

build_appimage.py

The build process creates the CyberDaemon AppImage including the required Python runtime and Qt components.

The generated AppImage is intended to be distributed through GitHub Releases rather than committed to the repository.

Configuration

User-specific configuration is stored outside the project directory.

Profiles:

~/.config/CyberDaemon/profiles.json

Autostart:

~/.config/autostart/cyberdaemon.desktop

This keeps user configuration separate from the application itself.

Beta Testing

This project is currently being developed as an open beta.

If you have a CORSAIR HS80 MAX Wireless and use Linux, please test it and report anything that does not work.

Useful information when reporting a problem:

Linux distribution
Desktop environment
PipeWire version
CyberDaemon version
What headset/receiver state was active
Steps to reproduce the problem
Relevant error messages

Please do not post private information, authentication tokens or personal configuration files.

Known Limitations

CyberDaemon is still beta software.

Some functionality may depend on:

Linux distribution
PipeWire configuration
USB/HID permissions
Desktop environment
HeSuVi/HRIR configuration
CORSAIR firmware versions

Firmware update functionality is still under development.

Feedback

Bug reports and suggestions are welcome.

If something does not work, please open a GitHub Issue and describe what happened.

The goal of the beta is to get CyberDaemon running reliably on as many Linux systems as possible.

Project

CyberDaemon // HS80 MAX

Linux control software for the CORSAIR HS80 MAX Wireless.

Version: 0.1.0-beta

Status: 🟣 Public Beta
