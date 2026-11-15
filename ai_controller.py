import os
import re
import subprocess
import threading
import time
import logging
from typing import Optional, Dict, Any

class AIController:
    def __init__(self, hardware_controller, socketio, current_control_mode_getter, set_control_mode_callback):
        self.hardware_controller = hardware_controller
        self.socketio = socketio
        self.current_control_mode_getter = current_control_mode_getter
        self.set_control_mode_callback = set_control_mode_callback
        self.ai_active = False
        self.ai_thread = None
        self.thinking = False

        # Configure logging
        self.logger = logging.getLogger('AIController')
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # Initialize text-to-speech engine
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
        except Exception as e:
            self.logger.warning(f"Could not initialize TTS engine: {e}")
            self.engine = None

    def speak(self, text: str) -> None:
        if not self.ai_active or not self.engine:
            return
        try:
            self.logger.debug(f"Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            self.logger.error(f"Error in speech synthesis: {e}")

    def extract_commands(self, text: str) -> Optional[str]:
        command_pattern = r'\b([FBLRS]\d+)(?:,\s*([FBLRS]\d+))*\b'
        match = re.search(command_pattern, text)
        return ' '.join(match.groups()) if match else None

    def send_to_arduino(self, command: str) -> bool:
        if not self.hardware_controller.arduino_connected:
            self.logger.warning("Arduino not connected - command not sent")
            return False
        try:
            self.logger.info(f"Sending command to Arduino: {command}")
            self.hardware_controller.arduino.write((command + '\n').encode('utf-8'))
            self.hardware_controller.arduino.flush()
            return True
        except Exception as e:
            self.logger.error(f"Error sending command to Arduino: {e}")
            return False

    def process_response(self, response: str) -> Optional[str]:
        commands = self.extract_commands(response)
        self.logger.debug(f"Extracted commands: {commands}")
        if commands and len(commands.strip()) == len(response.strip()):
            self.send_to_arduino(commands)
            return None
        elif commands:
            self.send_to_arduino(commands)
            text_response = re.sub(r'\b([FBLRS]\d+)(?:,\s*([FBLRS]\d+))*\b', '', response).strip()
            return text_response
        return response

    def query_llama(self, prompt: str) -> str:
        self.thinking = True
        try:
            self.logger.info(f"Querying Llama with prompt: {prompt[:100]}...")
            env = os.environ.copy()
            env["OLLAMA_NUM_THREADS"] = "4"

            result = subprocess.run(
                ["/usr/local/bin/ollama", "run", "llama3.2:latest", prompt],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                check=True
            )

            response = result.stdout.strip()
            if not response:
                error_msg = "Received empty response from AI"
                self.logger.warning(error_msg)
                return error_msg

            self.logger.debug(f"AI response: {response[:200]}...")
            return response

        except subprocess.TimeoutExpired:
            error_msg = "AI response timed out after 30 seconds"
            self.logger.warning(error_msg)
            return error_msg

        except subprocess.CalledProcessError as e:
            error_msg = f"AI command failed: {e.stderr.strip() or 'Unknown error'}"
            self.logger.error(error_msg)
            return error_msg

        except FileNotFoundError:
            error_msg = "Ollama not found. Please install and start Ollama first."
            self.logger.error(error_msg)
            self.speak(error_msg)
            return error_msg

        except Exception as e:
            error_msg = f"Unexpected AI error: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

        finally:
            self.thinking = False

    def run_voice_ai_loop(self) -> None:
        if self.current_control_mode_getter() != 'AI':
            self.logger.warning("AI control loop started but control mode is not AI")
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
            self.logger.error(f"Error in AI control loop: {e}")
        finally:
            self.logger.info("AI control loop ended")
            self.ai_active = False

    def start_ai_thread(self) -> None:
        if self.ai_active:
            self.logger.warning("AI thread already running")
            return
        if self.current_control_mode_getter() != 'AI':
            self.logger.error("Cannot start AI: control mode is not 'AI'")
            return
        self.ai_active = True
        self.ai_thread = threading.Thread(
            target=self.run_voice_ai_loop,
            daemon=True,
            name="AI-Control-Thread"
        )
        self.ai_thread.start()
        self.logger.info("AI thread started")

    def stop_ai(self) -> None:
        self.logger.info("Stopping AI controller")
        self.ai_active = False

        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join(timeout=2)
            if self.ai_thread.is_alive():
                self.logger.warning("AI thread did not stop gracefully")

        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                self.logger.error(f"Error stopping TTS engine: {e}")

        self.socketio.emit('ai_response', {
            'text': "AI mode deactivated",
            'status': 'inactive'
        })
