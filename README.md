
---

# 📱 Mobile Automation Toolkit (Python + ADB)

This repository provides a Python-based automation framework to interact with Android devices using the Android Debug Bridge (ADB). It enables automated control over Android devices for testing, diagnostics, or personal productivity scripts.

---

## 🔧 Features

* ✅ Connect to Android devices via USB or Wi-Fi
* 📲 Open, close, and list installed apps
* 🌐 Get network status and toggle Wi-Fi, Bluetooth, and Mobile Data
* 📸 Take device screenshots
* 🔋 Monitor battery and device information
* 📞 Make phone calls
* 🧠 Automate inputs: send text, tap screen, unlock device
* 🛠 Built-in logging and error handling for robustness

---

## 🗂 Project Structure

```
mobile.py                 # Main automation class using ADB commands
assets/
  └─ platform-tools/      # Optional local ADB tools directory (e.g., adb.exe)
auto/assets/
  └─ mobile_apps.json     # JSON config mapping app names to package names
```

---

## 📦 Requirements

* Python 3.7+
* ADB installed and accessible via system PATH or provided in `assets/platform-tools/`
* Android device with USB debugging enabled
* Required Python modules: `subprocess`, `json`, `os`, `re`, `sqlite3`, `logging`, `time`, `typing`, `pathlib`

---

## 🔌 Setup Instructions

1. **Clone the repository**

```bash
git clone https://github.com/chanduj8351/Mobile-Automation.git
cd Mobile-Automation
```

2. **(Optional)** Update `mobile_apps.json` with your desired app names and package identifiers:

```json
{
  "YouTube": "com.google.android.youtube",
  "WhatsApp": "com.whatsapp"
}
```

3. **Ensure ADB is installed:**

Install via [official platform-tools](https://developer.android.com/studio/releases/platform-tools), or let the script use `assets/platform-tools/adb.exe`.

---

## 🚀 Usage

Run the script directly to perform sample actions like unlocking the phone:

```bash
python mobile.py
```

### Common Methods Available

```python
device = AndroidDevice()

device.connect_device()             # Connect device
device.get_installed_apps()        # List installed packages
device.open_app("YouTube")         # Launch an app
device.close_app("WhatsApp")       # Force-stop app
device.take_screenshot("snap.png") # Save screenshot
device.make_call("+1234567890")    # Make a phone call
device.get_battery_status()        # Get battery info
device.toggle_wifi(True)           # Enable Wi-Fi
device.unlock_device()             # Unlock the device
```

---

## 🧪 Example

```python
if __name__ == "__main__":
    device = AndroidDevice()
    status = device.unlock_device()
    print("Unlock status:", status)
```

---

## 📋 Error Handling

Custom `AndroidDeviceError` is raised for most ADB-related failures. Logs are automatically printed with timestamps using Python's built-in `logging`.

---

## 🙌 Contributions

Feel free to contribute by creating issues or pull requests. Feature suggestions and bug reports are welcome!

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

