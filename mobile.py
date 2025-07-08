import subprocess
import json
import os
import re
from time import sleep
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AndroidDeviceError(Exception):
    """Custom exception for Android device operations"""
    pass

class AndroidDevice:
    def __init__(self, adb_path: Optional[str] = None, mobile_apps_path: Optional[str] = None):
        """
        Initialize AndroidDevice with configurable paths
        
        Args:
            adb_path: Path to ADB executable
            mobile_apps_path: Path to mobile apps JSON file
        """
        self.adb_path = adb_path or self._get_default_adb_path()
        self.mobile_apps_path = mobile_apps_path or self._get_default_apps_path()
        self.device_id: Optional[str] = None
        self.installed_apps_cache: Dict[str, str] = {}
        
        # Load mobile apps configuration
        self._load_mobile_apps()
        
        # Initialize device connection
        self._initialize_device()
    
    def _get_default_adb_path(self) -> str:
        """Get default ADB path with cross-platform support"""
        if os.name == 'nt':  # Windows
            return os.path.join(os.getcwd(), 'assets', 'platform-tools', 'adb.exe')
        else:  # Unix-like systems
            return 'adb'  # Assume it's in PATH
    
    def _get_default_apps_path(self) -> str:
        """Get default mobile apps JSON path"""
        return os.path.join(os.getcwd(), 'auto', 'assets', 'mobile_apps.json')
    
    def _load_mobile_apps(self) -> None:
        """Load mobile apps configuration from JSON file"""
        try:
            if os.path.exists(self.mobile_apps_path):
                with open(self.mobile_apps_path, 'r', encoding='utf-8') as f:
                    self.installed_apps_cache = json.load(f)
                logger.info(f"Loaded {len(self.installed_apps_cache)} app configurations")
            else:
                logger.warning(f"Mobile apps file not found: {self.mobile_apps_path}")
                self.installed_apps_cache = {}
        except Exception as e:
            logger.error(f"Error loading mobile apps configuration: {e}")
            self.installed_apps_cache = {}
    
    def _initialize_device(self) -> None:
        """Initialize device connection"""
        try:
            self.device_id = self.get_device_id()
            if self.device_id:
                logger.info(f"Connected to device: {self.device_id}")
            else:
                logger.warning("No device connected")
        except Exception as e:
            logger.error(f"Error initializing device: {e}")
    
    def _run_adb_command(self, command: List[str], capture_output: bool = True, 
                        check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
        """
        Run ADB command with error handling and timeout
        
        Args:
            command: ADB command as list of strings
            capture_output: Whether to capture output
            check: Whether to raise exception on non-zero exit code
            timeout: Command timeout in seconds
        
        Returns:
            CompletedProcess object
        """
        full_command = [self.adb_path] + command
        try:
            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            raise AndroidDeviceError(f"Command timed out after {timeout} seconds: {' '.join(full_command)}")
        except subprocess.CalledProcessError as e:
            raise AndroidDeviceError(f"ADB command failed: {e}")
        except FileNotFoundError:
            raise AndroidDeviceError(f"ADB executable not found: {self.adb_path}")
    
    def get_device_id(self) -> Optional[str]:
        """Get the connected device ID with improved error handling"""
        try:
            result = self._run_adb_command(['devices'])
            lines = result.stdout.strip().split('\n')
            
            # Find devices that are online
            for line in lines[1:]:  # Skip header
                if '\tdevice' in line:
                    return line.split('\t')[0]
            
            logger.warning("No online devices found")
            return None
        except Exception as e:
            logger.error(f"Error getting device ID: {e}")
            return None
    
    def connect_device(self, ip_address = "192.168.110.241"):
        """Connect to the device via USB or Wi-Fi."""
        try:
            if ip_address:
                subprocess.call([self.adb_path, 'kill-server'])
                sleep(0.3)
                subprocess.call([self.adb_path,'start-server'])
                sleep(0.3)
                subprocess.call([self.adb_path, 'tcpip', '5555'])
                sleep(0.3)
                subprocess.call([self.adb_path, 'connect', ip_address])
                self.device_id = ip_address
                return True
            
            else:
                self.device_id = self.get_device_id()
                return False
            #print(f"Connected to device: {self.device_id}")
        except Exception as e:
            return f"Error connecting to device: {e}"
    
    def disconnect_device(self) -> bool:
        """Disconnect the device with improved error handling"""
        try:
            self._run_adb_command(['disconnect'])
            self.device_id = None
            logger.info("Device disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting device: {e}")
            return False
    
    def get_installed_apps(self) -> List[str]:
        """Retrieve list of installed apps with caching"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            result = self._run_adb_command(['-s', self.device_id, 'shell', 'pm', 'list', 'packages'])
            apps = [line.strip().replace('package:', '') for line in result.stdout.splitlines() if line.strip()]
            
            logger.info(f"Found {len(apps)} installed apps")
            return apps
        except Exception as e:
            logger.error(f"Error retrieving installed apps: {e}")
            return []
    
    def open_app(self, app_name: str) -> Optional[int]:
        """
        Open app with improved error handling and validation
        
        Args:
            app_name: App name from configuration
        
        Returns:
            Elapsed time in milliseconds if successful, None otherwise
        """
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            if app_name not in self.installed_apps_cache:
                raise AndroidDeviceError(f"App '{app_name}' not found in configuration")
            
            package_name = self.installed_apps_cache[app_name]
            
            result = self._run_adb_command([
                '-s', self.device_id, 'shell', 'monkey', '-p', package_name.lower(),
                '-c', 'android.intent.category.LAUNCHER', '1'
            ])
            
            # Extract elapsed time
            match = re.search(r"elapsed time=(\d+)ms", result.stdout)
            if match:
                elapsed_time = int(match.group(1))
                logger.info(f"App '{app_name}' opened successfully in {elapsed_time}ms")
                return True
            else:
                logger.info(f"App '{app_name}' opened successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error opening app '{app_name}': {e}")
            return False
    
    def close_app(self, app_name: str) -> bool:
        """Close app with improved error handling"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            if app_name not in self.installed_apps_cache:
                raise AndroidDeviceError(f"App '{app_name}' not found in configuration")
            
            package_name = self.installed_apps_cache[app_name]
            self._run_adb_command(['-s', self.device_id, 'shell', 'am', 'force-stop', package_name])
            
            logger.info(f"Closed app: {app_name}")
            return True
        except Exception as e:
            logger.error(f"Error closing app '{app_name}': {e}")
            return False
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status information"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            # Check connectivity
            try:
                result = self._run_adb_command(['-s', self.device_id, 'shell', 'ping', '-c', '1', '8.8.8.8'])
                internet_connected = result.returncode == 0
            except:
                internet_connected = False
            
            # Get network info
            network_info = self._run_adb_command(['-s', self.device_id, 'shell', 'dumpsys', 'connectivity'])
            
            status = {
                'internet_connected': internet_connected,
                'wifi_enabled': 'Wi-Fi' in network_info.stdout and 'CONNECTED' in network_info.stdout,
                'mobile_data_enabled': 'mobile' in network_info.stdout.lower() and 'CONNECTED' in network_info.stdout,
                'raw_info': network_info.stdout
            }
            
            return status
        except Exception as e:
            logger.error(f"Error checking network status: {e}")
            return {'error': str(e)}
    
    def toggle_wifi(self, enable: bool = True) -> bool:
        """Toggle WiFi with clearer parameter naming"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            action = 'enable' if enable else 'disable'
            self._run_adb_command(['-s', self.device_id, 'shell', 'svc', 'wifi', action])
            
            logger.info(f"Wi-Fi {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error toggling Wi-Fi: {e}")
            return False
    
    def toggle_bluetooth(self, enable: bool = True) -> bool:
        """Toggle Bluetooth with clearer parameter naming"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            action = 'enable' if enable else 'disable'
            self._run_adb_command(['-s', self.device_id, 'shell', 'svc', 'bluetooth', action])
            
            logger.info(f"Bluetooth {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error toggling Bluetooth: {e}")
            return False
    
    def toggle_mobile_data(self, enable: bool = True) -> bool:
        """Toggle mobile data with clearer parameter naming"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            action = 'enable' if enable else 'disable'
            self._run_adb_command(['-s', self.device_id, 'shell', 'svc', 'data', action])
            
            logger.info(f"Mobile data {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error toggling mobile data: {e}")
            return False
    
    def take_screenshot(self, file_path: str = "screenshot.png", local_path: Optional[str] = None) -> bool:
        """
        Take screenshot with improved path handling
        
        Args:
            file_path: Remote file path on device
            local_path: Local file path (defaults to current directory)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            remote_path = f"/sdcard/{file_path}"
            local_file = local_path or file_path
            
            # Take screenshot
            self._run_adb_command(['-s', self.device_id, 'shell', 'screencap', '-p', remote_path])
            
            # Pull screenshot to local device
            self._run_adb_command(['-s', self.device_id, 'pull', remote_path, local_file])
            
            # Clean up remote file
            self._run_adb_command(['-s', self.device_id, 'shell', 'rm', remote_path], check=False)
            
            logger.info(f"Screenshot saved to: {local_file}")
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
    
    def make_call(self, phone_number: str) -> bool:
        """Make a phone call with validation"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            # Basic phone number validation
            if not re.match(r'^[\d\+\-\(\)\s]+$', phone_number):
                raise AndroidDeviceError("Invalid phone number format")
            
            logger.info(f"Dialing {phone_number}...")
            
            # Open dialer
            self._run_adb_command([
                '-s', self.device_id, 'shell', 'am', 'start',
                '-a', 'android.intent.action.CALL',
                '-d', f'tel:{phone_number}'
            ])
            
            logger.info(f"Call initiated to {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error making call: {e}")
            return False
    
    def get_battery_status(self) -> Dict[str, Any]:
        """Get comprehensive battery status information"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            result = self._run_adb_command(['-s', self.device_id, 'shell', 'dumpsys', 'battery'])
            battery_info = result.stdout
            
            # Parse battery information
            status = {}
            for line in battery_info.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'level':
                        status['battery_level'] = int(value)
                    elif key == 'voltage':
                        status['voltage_mv'] = int(value)
                    elif key == 'temperature':
                        status['temperature_celsius'] = int(value) / 10
                    elif key in ['usb_powered', 'ac_powered', 'wireless_powered']:
                        status[key] = value.lower() == 'true'
                    elif key == 'status':
                        status['charging_status'] = value
            
            # Determine overall charging state
            status['is_charging'] = any([
                status.get('usb_powered', False),
                status.get('ac_powered', False),
                status.get('wireless_powered', False)
            ])
            
            return status
        except Exception as e:
            logger.error(f"Error getting battery status: {e}")
            return {'error': str(e)}
    
    def get_device_info(self) -> Dict[str, str]:
        """Get comprehensive device information"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            info = {}
            
            # Get various device properties
            properties = [
                ('brand', 'ro.product.brand'),
                ('model', 'ro.product.model'),
                ('version', 'ro.build.version.release'),
                ('sdk', 'ro.build.version.sdk'),
                ('manufacturer', 'ro.product.manufacturer'),
                ('serial', 'ro.serialno')
            ]
            
            for key, prop in properties:
                try:
                    result = self._run_adb_command(['-s', self.device_id, 'shell', 'getprop', prop])
                    info[key] = result.stdout.strip()
                except:
                    info[key] = 'Unknown'
            
            return info
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {'error': str(e)}
    
    def send_text(self, text: str) -> bool:
        """Send text input to device"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            # Escape special characters
            escaped_text = text.replace(' ', '%s').replace('&', '\\&')
            
            self._run_adb_command(['-s', self.device_id, 'shell', 'input', 'text', escaped_text])
            logger.info(f"Sent text: {text}")
            return True
        except Exception as e:
            logger.error(f"Error sending text: {e}")
            return False
    
    def send_keyevent(self, keycode: int) -> bool:
        """Send keyevent to device"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            self._run_adb_command(['-s', self.device_id, 'shell', 'input', 'keyevent', str(keycode)])
            logger.info(f"Sent keyevent: {keycode}")
            return True
        except Exception as e:
            logger.error(f"Error sending keyevent: {e}")
            return False
    
    def tap_screen(self, x: int, y: int) -> bool:
        """Tap screen at coordinates"""
        try:
            if not self.device_id:
                raise AndroidDeviceError("No device connected")
            
            self._run_adb_command(['-s', self.device_id, 'shell', 'input', 'tap', str(x), str(y)])
            logger.info(f"Tapped screen at ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Error tapping screen: {e}")
            return False
        
    def unlock_device(self):
        try:
            self.send_keyevent(26)
            sleep(0.9)
            self._run_adb_command(['-s', self.device_id, 'shell', 'input', 'swipe', '400 1000 500 300'])
            sleep(0.6)
            self.send_text('3803')
            return True

        except:
            return f"Error in Unlock the device" 
    

# Example usage and testing
if __name__ == "__main__":
    device = AndroidDevice()
    i = device.unlock_device()
    print(i)
    
