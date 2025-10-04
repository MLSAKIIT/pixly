"""Main frontend overlay, made using custom Tkinter"""

import sys
import customtkinter as ctk
import requests
import keyboard
import threading
import tkinter as tk
from tkinter import filedialog
import os
import json
from PIL import Image
import base64
import io
from PIL import ImageGrab, ImageTk

class ChatWindow(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Title for chat interface
        self.chat_title = ctk.CTkLabel(
            self,
            text="Chat with Pixly",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray20", "gray80")
        )
        self.chat_title.pack(pady=(10, 5))
        
        # Chat history with improved styling
        self.chat_text = ctk.CTkTextbox(
            self,
            height=300,
            font=ctk.CTkFont(size=12),
            wrap="word",
            corner_radius=15,
            border_width=1,
            border_color=("gray70", "gray30")
        )
        self.chat_text.pack(fill="both", expand=True, padx=10, pady=(5,5))
        try:
            self.chat_text.tag_configure("user", foreground="#00C853")
            self.chat_text.tag_configure("Pixly", foreground="#82B1FF")
            self.chat_text.tag_configure("system", foreground="#B0B0B0")
        except Exception:
            pass

        # Typing indicator label
        self.typing_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=("gray40", "gray60")
        )
        self.typing_label.pack(fill="x", padx=12)
        
        # Screenshot preview area (hidden by default)
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_image_data = None
        self.preview_label = None
        
        # Input area container frame
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        
        # Message input
        self.message_input = ctk.CTkEntry(
            self.bottom_frame,
            placeholder_text="Type your message...",
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.message_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Screenshot buttons container
        self.screenshot_buttons_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.screenshot_buttons_frame.pack(side="right")
        
        # New screenshot button
        self.screenshot_button = ctk.CTkButton(
            self.screenshot_buttons_frame,
            text="📷",
            width=50,
            height=40,
            font=ctk.CTkFont(size=16),
            command=self.capture_new_screenshot,
            fg_color="#4467C4",
            hover_color="#365A9D"
        )
        self.screenshot_button.pack(side="left", padx=(0, 5))
        
        # Existing screenshot button
        self.existing_screenshot_button = ctk.CTkButton(
            self.screenshot_buttons_frame,
            text="🖼️",
            width=50,
            height=40,
            font=ctk.CTkFont(size=16),
            command=self.select_existing_screenshot,
            fg_color="#6A4C93",
            hover_color="#533A71"
        )
        self.existing_screenshot_button.pack(side="left", padx=(0, 10))
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.bottom_frame,
            text="Send",
            width=80,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.send_message
        )
        self.send_button.pack(side="right")
        
        # Bind Enter key
        self.message_input.bind("<Return>", lambda e: self.send_message())
                
        # Welcome message
        self.chat_text.insert("end", "💡 Tips:\n")
        self.chat_text.insert("end", "• 📷 Capture new screenshot with custom prompt\n")
        self.chat_text.insert("end", "• 🖼️ Select from existing screenshots\n")
        self.chat_text.insert("end", "• Edit your prompt before sending\n\n")
        self.chat_text.insert("end", "Pixly: Hello! How can I help you today?\n\n")
        self.chat_text.configure(state="disabled")

    def capture_new_screenshot(self):
        """Capture a new screenshot and show preview with editable prompt."""
        try:
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Convert to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            self.preview_image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Show preview
            self.show_screenshot_preview(screenshot)
            
            # Set default prompt if empty
            if not self.message_input.get().strip():
                self.message_input.delete(0, "end")
                self.message_input.insert(0, "Analyze this screenshot and provide insights.")
            
            self.message_input.focus()
            
        except Exception as e:
            self.add_system_message(f"Error capturing screenshot: {str(e)}")

    def select_existing_screenshot(self):
        """Open dialog to select from existing screenshots."""
        try:
            response = requests.get("http://127.0.0.1:8000/screenshots/recent", params={"limit": 50})
            if response.status_code == 200:
                screenshots = response.json()['screenshots']
                if screenshots:
                    self.open_screenshot_selector(screenshots)
                else:
                    self.add_system_message("No screenshots available. Capture some first!")
            else:
                self.add_system_message("Failed to load screenshots")
        except Exception as e:
            self.add_system_message(f"Error loading screenshots: {str(e)}")

    def open_screenshot_selector(self, screenshots):
        """Open a dialog to select a screenshot."""
        selector = ScreenshotSelector(self, screenshots, self.on_screenshot_selected)

    def on_screenshot_selected(self, screenshot_id):
        """Handle screenshot selection."""
        try:
            response = requests.get(f"http://127.0.0.1:8000/screenshots/{screenshot_id}")
            if response.status_code == 200:
                data = response.json()
                self.preview_image_data = data['data']
                
                # Decode and show preview
                image_bytes = base64.b64decode(self.preview_image_data)
                image = Image.open(io.BytesIO(image_bytes))
                self.show_screenshot_preview(image)
                
                # Set default prompt if empty
                if not self.message_input.get().strip():
                    self.message_input.delete(0, "end")
                    self.message_input.insert(0, "Analyze this screenshot and provide insights.")
                
                self.message_input.focus()
            else:
                self.add_system_message("Failed to load screenshot")
        except Exception as e:
            self.add_system_message(f"Error loading screenshot: {str(e)}")

    def show_screenshot_preview(self, image):
        """Show screenshot preview with option to remove."""
        # Create preview frame if it doesn't exist
        if self.preview_label is None:
            self.preview_frame.pack(fill="x", padx=10, pady=(0, 5), before=self.bottom_frame)
            
            # Resize image for preview
            image_copy = image.copy()
            image_copy.thumbnail((200, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image_copy)
            
            self.preview_label = tk.Label(self.preview_frame, image=photo, bg="#2b2b2b")
            self.preview_label.image = photo
            self.preview_label.pack(side="left", padx=5, pady=5)
            
            # Info label
            info_label = ctk.CTkLabel(
                self.preview_frame,
                text="Screenshot attached\nEdit prompt and press Send",
                font=ctk.CTkFont(size=11)
            )
            info_label.pack(side="left", padx=10)
            
            # Remove button
            remove_btn = ctk.CTkButton(
                self.preview_frame,
                text="✕",
                width=30,
                height=30,
                command=self.remove_screenshot_preview,
                fg_color="red",
                hover_color="darkred"
            )
            remove_btn.pack(side="right", padx=5, pady=5)

    def remove_screenshot_preview(self):
        """Remove screenshot preview."""
        self.preview_image_data = None
        if self.preview_label:
            self.preview_frame.pack_forget()
            for widget in self.preview_frame.winfo_children():
                widget.destroy()
            self.preview_label = None

    def send_message(self):
        message = self.message_input.get().strip()
        
        # Check if there's a screenshot attached
        if self.preview_image_data:
            if not message:
                self.add_system_message("Please enter a prompt for the screenshot analysis.")
                return
            self.send_screenshot_message(message)
        elif message:
            # Regular text message
            self.add_user_message(message)
            self.message_input.delete(0, "end")
            
            # Disable input while processing
            self.message_input.configure(state="disabled")
            self.send_button.configure(state="disabled")
            self.screenshot_button.configure(state="disabled")
            self.existing_screenshot_button.configure(state="disabled")
            
            # Show typing indicator and send to backend
            self.start_typing()
            threading.Thread(
                target=self.get_response,
                args=(message,),
                daemon=True
            ).start()

    def send_screenshot_message(self, message):
        """Send message with screenshot to backend."""
        self.add_user_message(f"{message} [📷 Screenshot attached]")
        self.message_input.delete(0, "end")
        
        # Disable input while processing
        self.message_input.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.screenshot_button.configure(state="disabled")
        self.existing_screenshot_button.configure(state="disabled")
        
        self.start_typing()
        
        # Send to backend
        image_data = self.preview_image_data
        self.remove_screenshot_preview()
        
        threading.Thread(
            target=self.get_response,
            args=(message, image_data),
            daemon=True
        ).start()

    def get_response(self, message, image_data=None):
        try:
            payload = {"message": message}
            if image_data:
                payload["image_data"] = image_data
                
            response = requests.post(
                "http://127.0.0.1:8000/chat",
                json=payload
            )
            if response.status_code == 200:
                ai_response = response.json()["response"]
                self.after(0, self.add_assistant_message, ai_response)
            else:
                self.after(0, self.add_assistant_message, "Error: Could not get response")
        except Exception as e:
            self.after(0, self.add_assistant_message, f"Error: {str(e)}")
        finally:
            # Re-enable input
            self.after(0, self.stop_typing)
            self.after(0, self.enable_input)

    def add_user_message(self, text):
        self.chat_text.configure(state="normal")
        try:
            self.chat_text.insert("end", "You: ", "user")
        except Exception:
            self.chat_text.insert("end", "You: ")
        self.chat_text.insert("end", f"{text}\n\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def add_assistant_message(self, text):
        self.chat_text.configure(state="normal")
        try:
            self.chat_text.insert("end", "Pixly: ", "assistant")
        except Exception:
            self.chat_text.insert("end", "Pixly: ")
        self.chat_text.insert("end", f"{text}\n\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def add_system_message(self, text):
        self.chat_text.configure(state="normal")
        try:
            self.chat_text.insert("end", "System: ", "system")
        except Exception:
            self.chat_text.insert("end", "System: ")
        self.chat_text.insert("end", f"{text}\n\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def start_typing(self):
        self._typing_active = True
        self._typing_step = 0
        self._animate_typing()

    def stop_typing(self):
        self._typing_active = False
        self.typing_label.configure(text="")

    def _animate_typing(self):
        if not hasattr(self, "_typing_active"):
            self._typing_active = False
        if not self._typing_active:
            return
        dots = "." * ((self._typing_step % 3) + 1)
        self.typing_label.configure(text=f"Assistant is typing{dots}")
        self._typing_step += 1
        self.after(400, self._animate_typing)

    def enable_input(self):
        self.message_input.configure(state="normal")
        self.send_button.configure(state="normal")
        self.screenshot_button.configure(state="normal")
        self.existing_screenshot_button.configure(state="normal")
        self.message_input.focus()

    def set_prompt(self, prompt):
        """Set a quick prompt in the message input."""
        self.message_input.delete(0, "end")
        self.message_input.insert(0, prompt)
        self.message_input.focus()

    def return_to_menu(self):
        if hasattr(self.master.master, "show_buttons"):
            self.master.master.show_buttons()


class ScreenshotSelector(ctk.CTkToplevel):
    """Dialog for selecting an existing screenshot."""
    def __init__(self, parent, screenshots, callback):
        super().__init__(parent)
        
        self.callback = callback
        self.title("Select Screenshot")
        self.geometry("800x600")
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Select a Screenshot",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=10)
        
        # Screenshot list
        self.screenshot_list = ctk.CTkScrollableFrame(self)
        self.screenshot_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display screenshots
        for i, screenshot in enumerate(screenshots):
            self.create_screenshot_item(screenshot, i)

    def create_screenshot_item(self, screenshot, index):
        """Create a screenshot item in the selector."""
        item_frame = ctk.CTkFrame(self.screenshot_list)
        item_frame.pack(fill="x", pady=5)
        
        # Screenshot info
        info_text = f"ID: {screenshot[0]} | App: {screenshot[2]} | Time: {screenshot[1]}"
        info_label = ctk.CTkLabel(
            item_frame,
            text=info_text,
            font=ctk.CTkFont(size=12)
        )
        info_label.pack(side="left", padx=10, pady=10)
        
        # Select button
        select_btn = ctk.CTkButton(
            item_frame,
            text="Select",
            command=lambda: self.select_screenshot(screenshot[0]),
            width=80,
            fg_color="#4467C4"
        )
        select_btn.pack(side="right", padx=10, pady=10)

    def select_screenshot(self, screenshot_id):
        """Select a screenshot and close dialog."""
        self.callback(screenshot_id)
        self.destroy()


class SettingsWindow(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Settings title
        self.settings_title = ctk.CTkLabel(
            self,
            text="Screenshot Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray20", "gray80")
        )
        self.settings_title.pack(pady=(10, 20))
        
        # Settings container
        self.settings_container = ctk.CTkScrollableFrame(self)
        self.settings_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Load current settings
        self.settings = self.load_settings()
        # Fetch API key status (non-blocking)
        threading.Thread(target=self.fetch_api_key_status, daemon=True).start()
        
        # Auto-capture section
        self.auto_capture_label = ctk.CTkLabel(
            self.settings_container,
            text="Automatic Screenshot Capture",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#4467C4", "#82B1FF")
        )
        self.auto_capture_label.pack(pady=(5, 10))
        
        # Screenshot toggle
        self.toggle_frame = ctk.CTkFrame(self.settings_container)
        self.toggle_frame.pack(fill="x", pady=5)
        
        self.toggle_label = ctk.CTkLabel(
            self.toggle_frame,
            text="Enable Auto-Capture",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.toggle_label.pack(side="left", padx=10, pady=10)
        
        self.toggle_switch = ctk.CTkSwitch(
            self.toggle_frame,
            text="",
            command=self.toggle_screenshot_capture
        )
        self.toggle_switch.pack(side="right", padx=10, pady=10)
        self.toggle_switch.select() if self.settings.get('enabled', False) else None
        
        # Interval setting
        self.interval_frame = ctk.CTkFrame(self.settings_container)
        self.interval_frame.pack(fill="x", pady=5)
        
        self.interval_label = ctk.CTkLabel(
            self.interval_frame,
            text="Capture Interval (seconds)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.interval_label.pack(side="left", padx=10, pady=10)
        
        self.interval_entry = ctk.CTkEntry(
            self.interval_frame,
            placeholder_text="30",
            width=100
        )
        self.interval_entry.pack(side="right", padx=10, pady=10)
        self.interval_entry.insert(0, str(self.settings.get('interval', 30)))
        
        # Analysis toggle
        self.analysis_frame = ctk.CTkFrame(self.settings_container)
        self.analysis_frame.pack(fill="x", pady=5)
        
        self.analysis_label = ctk.CTkLabel(
            self.analysis_frame,
            text="Auto-Analyze Screenshots",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analysis_label.pack(side="left", padx=10, pady=10)
        
        self.analysis_switch = ctk.CTkSwitch(
            self.analysis_frame,
            text=""
        )
        self.analysis_switch.pack(side="right", padx=10, pady=10)
        self.analysis_switch.select() if self.settings.get('auto_analyze', True) else None
        
        # Folder selection
        self.folder_frame = ctk.CTkFrame(self.settings_container)
        self.folder_frame.pack(fill="x", pady=5)
        
        self.folder_label = ctk.CTkLabel(
            self.folder_frame,
            text="Screenshot Folder",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.folder_label.pack(side="left", padx=10, pady=10)
        
        self.folder_button = ctk.CTkButton(
            self.folder_frame,
            text="Select Folder",
            command=self.select_folder,
            width=120,
            fg_color="#4467C4"
        )
        self.folder_button.pack(side="right", padx=10, pady=10)
        
        self.folder_path_label = ctk.CTkLabel(
            self.folder_frame,
            text=self.settings.get('folder', 'Default: ./screenshots'),
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray50")
        )
        self.folder_path_label.pack(side="right", padx=10, pady=5)

        # API Key section
        self.api_key_frame = ctk.CTkFrame(self.settings_container)
        self.api_key_frame.pack(fill="x", pady=10)

        self.api_key_label = ctk.CTkLabel(
            self.api_key_frame,
            text="Gemini API Key",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.api_key_label.pack(side="left", padx=10, pady=10)

        self.api_key_entry = ctk.CTkEntry(
            self.api_key_frame,
            placeholder_text="Enter or paste your API key",
            width=260
        )
        self.api_key_entry.pack(side="left", padx=10, pady=10)

        self.api_key_save_btn = ctk.CTkButton(
            self.api_key_frame,
            text="Save API Key",
            command=self.save_api_key,
            width=120,
            fg_color="#4467C4"
        )
        self.api_key_save_btn.pack(side="right", padx=10, pady=10)
        
        # Manual view button
        self.view_frame = ctk.CTkFrame(self.settings_container)
        self.view_frame.pack(fill="x", pady=5)
        
        self.view_button = ctk.CTkButton(
            self.view_frame,
            text="View Screenshots",
            command=self.view_screenshots,
            height=40,
            fg_color="#4467C4"
        )
        self.view_button.pack(fill="x", padx=10, pady=10)
        
        # Save settings button
        self.save_frame = ctk.CTkFrame(self.settings_container)
        self.save_frame.pack(fill="x", pady=5)
        
        self.save_button = ctk.CTkButton(
            self.save_frame,
            text="Save Settings",
            command=self.save_settings,
            height=40,
            fg_color="green"
        )
        self.save_button.pack(fill="x", padx=10, pady=10)

    def load_settings(self):
        """Load settings from file."""
        settings_file = "screenshot_settings.json"
        default_settings = {
            'enabled': False,
            'interval': 30,
            'folder': './screenshots',
            'auto_analyze': True
        }
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except:
                return default_settings
        return default_settings

    def fetch_api_key_status(self):
        """Fetch API key configuration status from backend and update placeholder/label."""
        try:
            resp = requests.get("http://127.0.0.1:8000/settings/api-key", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("configured"):
                    preview = data.get("preview", "")
                    self.api_key_entry.configure(placeholder_text=f"Configured: {preview}")
                else:
                    self.api_key_entry.configure(placeholder_text="Enter or paste your API key")
        except Exception:
            pass
    
    def save_settings(self):
        """Save settings to file."""
        settings_file = "screenshot_settings.json"
        
        # Get current settings from UI
        self.settings['enabled'] = self.toggle_switch.get() == 1
        self.settings['interval'] = int(self.interval_entry.get() or 30)
        self.settings['auto_analyze'] = self.analysis_switch.get() == 1
        
        # Save to file
        with open(settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
        
        # Apply settings
        self.apply_settings()
        
        # Show confirmation
        self.show_message("Settings saved successfully!")

    def save_api_key(self):
        """Send API key to backend for persistence and live reconfigure."""
        try:
            key = (self.api_key_entry.get() or "").strip()
            if not key:
                self.show_message("Please enter a valid API key")
                return
            resp = requests.post(
                "http://127.0.0.1:8000/settings/api-key",
                json={"api_key": key},
                timeout=8
            )
            if resp.status_code == 200:
                self.show_message("API key saved")
                self.api_key_entry.delete(0, "end")
                self.fetch_api_key_status()
            else:
                try:
                    detail = resp.json().get("detail", "Error saving API key")
                except Exception:
                    detail = "Error saving API key"
                self.show_message(detail)
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def apply_settings(self):
        """Apply settings to the screenshot system."""
        try:
            if self.settings['enabled']:
                # Start screenshot capture
                response = requests.post(
                    "http://127.0.0.1:8000/screenshots/start",
                    params={
                        "interval": self.settings['interval'],
                        "auto_analyze": self.settings['auto_analyze']
                    }
                )
                if response.status_code == 200:
                    print("Screenshot capture started")
                else:
                    print("Failed to start screenshot capture")
            else:
                # Stop screenshot capture
                response = requests.post("http://127.0.0.1:8000/screenshots/stop")
                if response.status_code == 200:
                    print("Screenshot capture stopped")
                else:
                    print("Failed to stop screenshot capture")
        except Exception as e:
            print(f"Error applying settings: {e}")
    
    def toggle_screenshot_capture(self):
        """Toggle screenshot capture on/off."""
        self.settings['enabled'] = self.toggle_switch.get() == 1
        self.apply_settings()
    
    def select_folder(self):
        """Select folder for screenshots."""
        folder = filedialog.askdirectory()
        if folder:
            self.settings['folder'] = folder
            self.folder_path_label.configure(text=folder)
    
    def view_screenshots(self):
        """Open screenshot viewer window."""
        try:
            # Get recent screenshots
            response = requests.get("http://127.0.0.1:8000/screenshots/recent", params={"limit": 20})
            if response.status_code == 200:
                screenshots = response.json()['screenshots']
                self.open_screenshot_viewer(screenshots)
            else:
                self.show_message("Failed to load screenshots")
        except Exception as e:
            self.show_message(f"Error loading screenshots: {str(e)}")
    
    def open_screenshot_viewer(self, screenshots):
        """Open a new window to view screenshots."""
        viewer = ScreenshotViewer(self, screenshots)
        viewer.lift()
        viewer.focus()
    
    def show_message(self, message):
        """Show a temporary message."""
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=12),
            fg_color=("green", "darkgreen"),
            corner_radius=15
        )
        msg_label.pack(pady=5)
        self.after(3000, lambda: msg_label.destroy())
    
    def return_to_menu(self):
        if hasattr(self.master.master, "show_buttons"):
            self.master.master.show_buttons()


class ScreenshotViewer(ctk.CTkToplevel):
    def __init__(self, parent, screenshots):
        super().__init__(parent)
        
        self.title("Screenshot Viewer")
        self.geometry("800x600")
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Screenshot Gallery",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=10)
        
        # Screenshot list
        self.screenshot_list = ctk.CTkScrollableFrame(self)
        self.screenshot_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display screenshots
        for i, screenshot in enumerate(screenshots):
            self.create_screenshot_item(screenshot, i)
    
    def create_screenshot_item(self, screenshot, index):
        """Create a screenshot item in the viewer."""
        item_frame = ctk.CTkFrame(self.screenshot_list)
        item_frame.pack(fill="x", pady=5)
        
        # Screenshot info
        info_text = f"ID: {screenshot[0]} | App: {screenshot[2]} | Time: {screenshot[1]}"
        info_label = ctk.CTkLabel(
            item_frame,
            text=info_text,
            font=ctk.CTkFont(size=12)
        )
        info_label.pack(side="left", padx=10, pady=10)
        
        # View button
        view_btn = ctk.CTkButton(
            item_frame,
            text="View",
            command=lambda: self.view_screenshot(screenshot[0]),
            width=80
        )
        view_btn.pack(side="right", padx=10, pady=10)

        # Delete button
        delete_btn = ctk.CTkButton(
            item_frame,
            text="Delete",
            command=lambda: self.delete_screenshot_item(item_frame, screenshot[0]),
            width=80,
            fg_color=("#B71C1C", "#B71C1C"),
            hover_color=("#D32F2F", "#D32F2F")
        )
        delete_btn.pack(side="right", padx=5, pady=10)

    def delete_screenshot_item(self, item_frame, screenshot_id):
        """Call backend to delete screenshot and remove from UI."""
        try:
            resp = requests.delete(f"http://127.0.0.1:8000/screenshots/{screenshot_id}", timeout=5)
            if resp.status_code == 200:
                item_frame.destroy()
            else:
                try:
                    detail = resp.json().get('detail', 'Failed to delete screenshot')
                except Exception:
                    detail = 'Failed to delete screenshot'
                print(detail)
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def view_screenshot(self, screenshot_id):
        """View a specific screenshot in a new window."""
        try:
            # Get screenshot data
            response = requests.get(f"http://127.0.0.1:8000/screenshots/{screenshot_id}")
            if response.status_code == 200:
                data = response.json()['data']
                self.open_image_viewer(data, screenshot_id)
            else:
                print("Failed to load screenshot")
        except Exception as e:
            print(f"Error loading screenshot: {e}")
    
    def open_image_viewer(self, image_data, screenshot_id):
        """Open a new window to view the actual image."""
        # Create new window
        image_window = ctk.CTkToplevel(self)
        image_window.title(f"Screenshot {screenshot_id}")
        image_window.geometry("1000x700")
        
        # Decode image data
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Resize image to fit window
            image.thumbnail((900, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Display image
            image_label = tk.Label(image_window, image=photo)
            image_label.pack(pady=10)
            
            # Keep reference to prevent garbage collection
            image_label.image = photo
            
        except Exception as e:
            error_label = ctk.CTkLabel(
                image_window,
                text=f"Error displaying image: {str(e)}",
                font=ctk.CTkFont(size=14)
            )
            error_label.pack(pady=50)


class Overlay(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Configure window
        self.title("Pixly")
        self.geometry("600x700")
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color=("gray90", "gray10"))
        
        # Add subtle transparency
        self.attributes('-alpha', 0.80)
        
        # Make the window itself have rounded corners
        self.attributes('-transparentcolor', 'white')
        
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create main frame with rounded corners and shadow effect
        self.frame = ctk.CTkFrame(
            self, 
            corner_radius=25,
            border_width=2,
            border_color=("gray70", "gray30"),
            fg_color=("white", "gray15")
        )
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Create header section
        self.header_frame = ctk.CTkFrame(
            self.frame, 
            corner_radius=15,
            fg_color=("gray85", "gray20"),
            height=60
        )
        self.header_frame.pack(fill="x", padx=15, pady=(15, 10))
        self.header_frame.pack_propagate(False)
        
        # Close/Back button in top left
        self.header_button = ctk.CTkButton(
            self.header_frame,
            text="✕",
            command=self.close_app,
            width=30,
            height=30,
            corner_radius=15,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("darkgrey", "darkgrey"),
            hover_color=("red", "red"),
            text_color="white"
        )
        self.header_button.place(x=10, y=15)
        
        # Title with icon
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Pixly Control Panel",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray20", "gray80")
        )
        self.title_label.pack(pady=15)
        
        # Main content area
        self.content_frame = ctk.CTkFrame(self.frame, corner_radius=15)
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Chat window (initially hidden)
        self.chat_window = ChatWindow(self.content_frame)
        
        # Settings window (initially hidden)
        self.settings_window = SettingsWindow(self.content_frame)
        
        # Buttons container
        self.buttons_frame = ctk.CTkFrame(self.content_frame, corner_radius=15)
        self.buttons_frame.pack(fill="both", expand=True)
        
        # Create buttons
        self.chat_button = self.create_button(
            "Chat with Pixly",
            self.toggle_chat_window,
            "#636363",
            "#222222"
        )
        self.button2 = self.create_button("Settings", self.toggle_settings_window, "#636363", "#222222")
        self.button3 = self.create_button("Button 3", lambda: None, "#636363", "#222222")
        self.button4 = self.create_button("Button 4", lambda: None, "#636363", "#222222")
        
        # Show buttons initially
        self.show_buttons()
        
        # Center window
        self.center_window()
        
        # Bind drag events to header
        self.header_frame.bind('<Button-1>', self.start_drag)
        self.header_frame.bind('<B1-Motion>', self.on_drag)
        self.title_label.bind('<Button-1>', self.start_drag)
        self.title_label.bind('<B1-Motion>', self.on_drag)
        
    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 700) // 2
        y = (screen_height - 700) // 2
        self.geometry(f'+{x}+{y}')
    
    def close_app(self):
        """Close the application permanently"""
        print("Pixly closed permanently")
        self.quit()
        self.destroy()
        sys.exit()
    
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def on_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")
    
    def create_button(self, text, command, fg_color, hv_color):
        return ctk.CTkButton(
            self.buttons_frame,
            text=text,
            command=command,
            height=45,
            corner_radius=15,
            fg_color=fg_color,
            hover_color=hv_color
        )

    def toggle_chat_window(self):
        if self.chat_window.winfo_viewable():
            self.show_buttons()
        else:
            self.show_chat()
    
    def toggle_settings_window(self):
        if self.settings_window.winfo_viewable():
            self.show_buttons()
        else:
            self.show_settings()

    def show_chat(self):
        self.buttons_frame.pack_forget()
        self.settings_window.pack_forget()
        self.chat_window.pack(fill="both", expand=True)
        # Update header button to back button
        self.header_button.configure(
            text="←",
            command=self.show_buttons,
            hover_color=("gray50", "gray50")
        )

    def show_settings(self):
        self.buttons_frame.pack_forget()
        self.chat_window.pack_forget()
        self.settings_window.pack(fill="both", expand=True)
        # Update header button to back button
        self.header_button.configure(
            text="←",
            command=self.show_buttons,
            hover_color=("gray50", "gray50")
        )

    def show_buttons(self):
        self.chat_window.pack_forget()
        self.settings_window.pack_forget()
        self.buttons_frame.pack(fill="both", expand=True)
        for btn in [self.chat_button, self.button2, self.button3, self.button4]:
            btn.pack(pady=5, padx=20, fill="x")
        # Restore close button
        self.header_button.configure(
            text="✕",
            command=self.close_app,
            hover_color=("red", "red")
        )


def main():
    app = Overlay()
    
    # Toggle visibility with global hotkey
    def toggle_overlay():
        if app.winfo_viewable():
            app.withdraw()
            print("Overlay is now hidden (Ctrl+Alt+M to show)")
        else:
            app.deiconify()
            app.lift()
            print("Pixly is now active!")
    
    keyboard.add_hotkey('ctrl+alt+m', toggle_overlay)
    
    app.withdraw()
    print("Pixly initialized! Press Ctrl+Alt+M to toggle visibility")
    app.mainloop()


if __name__ == "__main__":
    main()