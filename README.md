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
