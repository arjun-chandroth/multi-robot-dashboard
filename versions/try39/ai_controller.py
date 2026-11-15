import os
import re
import threading
import time
import logging
import requests
from typing import Optional

class AIController:
    def __init__(self, hardware_controller, socketio, current_control_mode_getter, set_control_mode_callback):
        self.hardware_controller = hardware_controller
        self.socketio = socketio
        self.current_control_mode_getter = current_control_mode_getter
        self.set_control_mode_callback = set_control_mode_callback
        self.ai_active = False
        self.ai_thread = None
        self.thinking = False

        self.logger = logging.getLogger('AIController')
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
        except Exception as e:
            self.logger.warning(f"Could not initialize TTS engine: {e}")
            self.engine = None

    def speak(self, text: str) -> None:
        if self.engine and self.ai_active:
            try:
                self.logger.debug(f"Speaking: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS Error: {e}")

    def extract_commands(self, text: str) -> Optional[str]:
        command_pattern = r'\b([FBLRS]\d+)(?:,\s*([FBLRS]\d+))*\b'
        match = re.search(command_pattern, text)
        return ' '.join(match.groups()) if match else None

    def send_to_arduino(self, command: str) -> bool:
        if not self.hardware_controller.arduino_connected:
            self.logger.warning("Arduino not connected.")
            return False
        try:
            self.logger.info(f"Sending to Arduino: {command}")
            self.hardware_controller.arduino.write((command + '\n').encode('utf-8'))
            self.hardware_controller.arduino.flush()
            return True
        except Exception as e:
            self.logger.error(f"Arduino error: {e}")
            return False

    def process_response(self, response: str) -> Optional[str]:
        commands = self.extract_commands(response)
        self.logger.debug(f"Extracted commands: {commands}")
        if commands and len(commands.strip()) == len(response.strip()):
            self.send_to_arduino(commands)
            return None
        elif commands:
            self.send_to_arduino(commands)
            return re.sub(r'\b([FBLRS]\d+)(?:,\s*([FBLRS]\d+))*\b', '', response).strip()
        return response

    def query_llama(self, prompt: str) -> None:
        self.thinking = True
        self.logger.info(f"Querying phi: {prompt}")
        self.socketio.emit('ai_response', {'text': '', 'status': 'streaming'})

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi",
                    "prompt": prompt,
                    "stream": False
                }
            )
            result = response.json()
            full_response = result.get("response", "").strip()

            self.socketio.emit('ai_response', {
                'text': full_response,
                'status': 'done'
            })

            filtered = self.process_response(full_response)
            if filtered:
                self.speak(filtered)

        except Exception as e:
            self.logger.error(f"Ollama HTTP error: {str(e)}")
            self.socketio.emit('ai_response', {'text': f"Error: {str(e)}", 'status': 'error'})
        finally:
            self.thinking = False

    def run_voice_ai_loop(self) -> None:
        if self.current_control_mode_getter() != 'AI':
            self.logger.warning("AI loop started in wrong mode.")
            return
        self.ai_active = True
        self.logger.info("AI control loop started")
        self.speak("AI control is now active.")
        self.socketio.emit('ai_response', {
            'text': "AI mode activated! How can I assist you with the robot controls?",
            'status': 'active'
        })
        try:
            while self.ai_active and self.current_control_mode_getter() == 'AI':
                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"AI loop error: {e}")
        finally:
            self.logger.info("AI control loop ended")
            self.ai_active = False

    def start_ai_thread(self) -> None:
        if self.ai_active:
            self.logger.warning("AI thread already running")
            return
        self.ai_thread = threading.Thread(
            target=self.run_voice_ai_loop,
            daemon=True
        )
        self.ai_thread.start()
        self.logger.info("AI thread started")

    def stop_ai(self) -> None:
        self.logger.info("Stopping AI controller")
        self.ai_active = False
        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join(timeout=2)
        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                self.logger.error(f"TTS stop error: {e}")
        self.socketio.emit('ai_response', {
            'text': "AI mode deactivated",
            'status': 'inactive'
        })
