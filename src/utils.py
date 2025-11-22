import cv2
import subprocess
import os
import platform
import sounddevice as sd
import soundfile as sf
import requests
from pydub import AudioSegment
from datetime import datetime
from PIL import Image
import mss

xi_api_key = os.environ.get('ELEVEN_LABS_API_KEY')

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

def take_picture():
    cap = cv2.VideoCapture(0)
    ramp_frames = 30 
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None

    for i in range(ramp_frames):
        ret, frame = cap.read()

    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    else:
        print("Error: Could not read frame.")
        return None

def get_number_of_screens():
    """Get the number of screens (cross-platform)"""
    if IS_MACOS:
        try:
            from AppKit import NSScreen
            return len(NSScreen.screens())
        except ImportError:
            print("Warning: AppKit not available, using MSS fallback")
    
    # Use MSS for Windows, Linux, or macOS fallback
    with mss.mss() as sct:
        return len(sct.monitors) - 1  # Subtract 1 because monitor[0] is all monitors combined

def take_screenshot_active_window():
    """
    Takes a screenshot of only the active/focused window.
    Returns a list with one dictionary containing the filepath and timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_filepath = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "screenshots",
        f"active_window_{timestamp}.png"
    )
    
    if IS_WINDOWS:
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            
            # Get the active window handle
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                print("Warning: No active window found, falling back to full screen")
                return take_screenshots()
            
            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Skip very small windows (likely system windows)
            if width < 50 or height < 50:
                print("Warning: Active window too small, falling back to full screen")
                return take_screenshots()
            
            # Use PrintWindow API - more reliable for capturing window contents
            # PrintWindow can capture windows even when covered or minimized
            try:
                # Get desktop DC for creating compatible bitmap
                desktop_dc = win32gui.GetDC(0)
                img_dc = win32ui.CreateDCFromHandle(desktop_dc)
                mem_dc = img_dc.CreateCompatibleDC()
                
                # Create bitmap
                screenshot = win32ui.CreateBitmap()
                screenshot.CreateCompatibleBitmap(img_dc, width, height)
                mem_dc.SelectObject(screenshot)
                
                # Use PrintWindow to capture the window (PW_CLIENTONLY = 1 captures client area only)
                # PW_RENDERFULLCONTENT = 0x2 captures full content even when minimized
                result = win32gui.PrintWindow(hwnd, mem_dc.GetSafeHdc(), 3)  # 3 = PW_CLIENTONLY | PW_RENDERFULLCONTENT
                
                if result:
                    # Convert to PIL Image
                    bmpstr = screenshot.GetBitmapBits(True)
                    img = Image.frombuffer(
                        'RGB',
                        (width, height),
                        bmpstr, 'raw', 'BGRX', 0, 1
                    )
                    
                    # Get client area dimensions if needed
                    client_rect = win32gui.GetClientRect(hwnd)
                    client_width = client_rect[2]
                    client_height = client_rect[3]
                    
                    # Crop to client area if it's significantly different
                    if client_width < width - 20 and client_height < height - 50:
                        # Calculate border offsets
                        border_x = (width - client_width) // 2
                        border_y = (height - client_height) - border_x
                        if border_y < 0:
                            border_y = height - client_height
                        
                        # Crop to client area
                        img = img.crop((border_x, border_y, border_x + client_width, border_y + client_height))
                    
                    img.save(save_filepath)
                    
                    # Clean up
                    win32gui.DeleteObject(screenshot.GetHandle())
                    mem_dc.DeleteDC()
                    img_dc.DeleteDC()
                    win32gui.ReleaseDC(0, desktop_dc)
                    
                    return [{"filepath": save_filepath, "timestamp": timestamp}]
                else:
                    raise Exception("PrintWindow returned False")
                    
            except Exception as e:
                # Fallback: Use MSS to capture the window region
                try:
                    # Get window rect in screen coordinates
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    
                    # Use MSS to capture this specific region
                    with mss.mss() as sct:
                        monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                        screenshot = sct.grab(monitor)
                        
                        # Convert to PIL Image and save
                        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                        img.save(save_filepath)
                        
                        return [{"filepath": save_filepath, "timestamp": timestamp}]
                except Exception as e2:
                    raise Exception(f"Both PrintWindow and MSS failed: {e}, {e2}")
                
        except ImportError:
            print("Warning: win32gui not available. Install pywin32 with: pip install pywin32")
            print("Falling back to full screen capture")
            return take_screenshots()
        except Exception as e:
            print(f"Warning: Error capturing active window: {e}")
            print("Falling back to full screen capture")
            return take_screenshots()
    
    elif IS_MACOS:
        try:
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGWindowListExcludeDesktopElements,
                kCGNullWindowID,
                kCGWindowBounds,
                kCGWindowLayer
            )
            from AppKit import NSScreen

            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID
            )

            front_window = None
            for window in window_list:
                if window.get(kCGWindowLayer, 0) == 0:
                    bounds = window.get(kCGWindowBounds, {})
                    width = int(bounds.get("Width", 0))
                    height = int(bounds.get("Height", 0))
                    if width > 100 and height > 100:
                        front_window = window
                        break

            if front_window:
                bounds = front_window.get(kCGWindowBounds, {})
                x = int(bounds.get("X", 0))
                y = int(bounds.get("Y", 0))
                width = int(bounds.get("Width", 0))
                height = int(bounds.get("Height", 0))

                if width <= 0 or height <= 0:
                    raise ValueError("Active window bounds invalid")

                with mss.mss() as sct:
                    primary_monitor = sct.monitors[1]
                    mss_width = primary_monitor["width"]
                    mss_height = primary_monitor["height"]

                    screen = NSScreen.mainScreen()
                    logical_frame = screen.frame()
                    logical_width = logical_frame.size.width
                    logical_height = logical_frame.size.height

                    scale_x = mss_width / logical_width if logical_width else 1.0
                    scale_y = mss_height / logical_height if logical_height else 1.0

                    logical_top = logical_height - (y + height)

                    monitor = {
                        "left": int(x * scale_x),
                        "top": int(logical_top * scale_y),
                        "width": int(width * scale_x),
                        "height": int(height * scale_y)
                    }

                    monitor["left"] = max(0, min(monitor["left"], mss_width - 1))
                    monitor["top"] = max(0, min(monitor["top"], mss_height - 1))
                    monitor["width"] = max(1, min(monitor["width"], mss_width - monitor["left"]))
                    monitor["height"] = max(1, min(monitor["height"], mss_height - monitor["top"]))

                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img.save(save_filepath)
                    return [{"filepath": save_filepath, "timestamp": timestamp}]
            else:
                print("Warning: No frontmost window detected, falling back to full screen")
                return take_screenshots()

        except ImportError:
            print("Warning: Quartz/AppKit not available, falling back to full screen")
            return take_screenshots()
        except Exception as e:
            print(f"Warning: Error capturing active window: {e}")
            print("Falling back to full screen capture")
            return take_screenshots()
    
    else:
        # Linux or other - fall back to full screen
        print("Active window capture not implemented for this platform, using full screen")
        return take_screenshots()


def take_screenshots():
    """
    Takes screenshots of each monitor and returns a list of dictionaries.
    Each dict contains the filepath and a timestamp.
    Cross-platform implementation using MSS for Windows/Linux, screencapture for macOS.
    
    NOTE: For active window only, use take_screenshot_active_window() instead.
    """
    if IS_MACOS:
        # macOS-specific implementation using screencapture
        try:
            from AppKit import NSScreen
            num_screens = len(NSScreen.screens())
            if num_screens == 0:
                print("Error: No screens detected.")
                return []
            
            screenshots = []
            for screen in range(1, num_screens+1):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filepath = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "screenshots",
                    f"screen_{screen}_{timestamp}.png"
                )
                subprocess.run(["screencapture", "-x", f"-D{screen}", save_filepath])
                screenshots.append({"filepath": save_filepath, "timestamp": timestamp})
            return screenshots
        except ImportError:
            # Fallback to MSS if AppKit not available
            pass
    
    # Windows/Linux implementation using MSS (also macOS fallback)
    with mss.mss() as sct:
        num_screens = len(sct.monitors) - 1  # monitor[0] is all monitors combined
        
        if num_screens == 0:
            print("Error: No screens detected.")
            return []
        
        screenshots = []
        # Start from 1 because monitor[0] is the combined monitor
        for monitor_num in range(1, num_screens + 1):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_filepath = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "screenshots",
                f"screen_{monitor_num}_{timestamp}.png"
            )
            
            # Capture the monitor
            monitor = sct.monitors[monitor_num]
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image and save
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(save_filepath)
            
            screenshots.append({"filepath": save_filepath, "timestamp": timestamp})
        
        return screenshots

def get_text_to_speech(text, voice="Harry"):
    character_dict = {
        "Adam" : "pNInz6obpgDQGcFmaJgB",
        "Arnold" : "VR6AewLTigWG4xSOukaG",
        "Emily" : "LcfcDJNUP1GQjkzn1xUU",
        "Harry" : "SOYHLrjzK2X1ezoPC6cr",
        "Josh": "TxGEqnHWrfWFTfGW9XjX",
        "Patrick" : "ODq5zmih8GrVes37Dizd"
    }
    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{character_dict[voice]}"
    headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": xi_api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    response = requests.post(url, json=data, headers=headers)
    voice_path_mp3 = os.path.join(os.path.dirname(__file__), "yell_voice.mp3")
    with open(voice_path_mp3, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    voice_path_wav = os.path.join(os.path.dirname(__file__), "yell_voice.wav")
    audio = AudioSegment.from_mp3(voice_path_mp3)
    audio.export(voice_path_wav, format="wav")
    return voice_path_wav


def play_text_to_speech(voice_file):
    data, samplerate = sf.read(voice_file)
    sd.play(data, samplerate)
    sd.wait()