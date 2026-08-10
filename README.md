# Moba Vibration Tool

A Windows utility for fine-grained vibration control on Mobapad controllers.

<img width="437" height="394" alt="screenshot2" src="https://github.com/user-attachments/assets/ae9f51ac-e0c5-41a9-8761-519db094967e" />
---

## Why This Tool Exists

The official Mobapad application only provides three vibration presets:

- Low
- Medium
- High

During daily use, even the **Low** setting still felt too strong.

Because of this, a reverse engineering effort was started to better understand how vibration configuration is stored and transmitted to the controller firmware.

During that process, it was discovered that the official application is only exposing a few presets, while the controller firmware actually accepts custom vibration values.

This led to the creation of **Mobapad Vibration Tool**, allowing users to configure much softer vibration levels than those available in the official application.

---

## Reverse Engineering Findings

The controller firmware stores vibration configuration using internal motor parameters.

The official application writes values equivalent to:

### LOW

```text
25
```

### MEDIUM

```text
38
```

### HIGH

```text
204
```

However, testing revealed that the firmware accepts a much wider range of values.

Examples that were successfully tested:

```text
13
15
20
25
38
50
100
204
```

---

## Why The Minimum Value Is 13

Although the firmware accepts values lower than 13, experiments showed that the vibration motors no longer produce a noticeable response at very low values.

For this reason, the application uses:

```text
13
```

as the minimum practical vibration level.

And:

```text
204
```

as the maximum value used by the official application.

Current range:

```text
13 - 204
```

---

## Features

### Read Current Vibration

Read the currently configured vibration level stored in the controller.

### Apply Custom Vibration Levels

Set any vibration level within the supported range:

```text
13 - 204
```

### Disable Vibration

Turn vibration completely off.

```text
OFF
```

### Independent Left and Right Controller Support

Configure:

- Left controller
- Right controller

independently.

### Automatic Detection

The application automatically discovers compatible controllers using Bluetooth Low Energy (BLE).

---

## Supported Controllers

Currently supported:

- Mobapad-S1
- Mobapad-M6 (needs testing)
- Mobapad-M12 (needs testing)

---

## Interface

The application provides:

- Controller selection
- Current vibration level reading
- Custom vibration level slider
- OFF button

## Requirements

- Windows
- Bluetooth LE support
- Mobapad controller

---

## How to use

Extract and run .exe in a bluetooth enabled windows computer.

---

## Disclaimer

This project is not affiliated with, endorsed by, or supported by Mobapad.

Use at your own risk.

---

## License

MIT

## Support the Project

If this tool helped you and you'd like to support future development, consider buying me a coffee:

☕ https://buymeacoffee.com/KickAssBR

Thanks for your support! `