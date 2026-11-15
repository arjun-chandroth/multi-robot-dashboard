import re
import subprocess
import pyttsx3
import threading
import time

class AIController:
    def __init__(self, hardware_controller, socketio, current_control_mode_getter, set_control_mode_callback):
        self.hardware_controller = hardware_controller
        self.socketio = socketio
        self.engine = pyttsx3.init()
        self.ai_active = False
        self.current_control_mode_getter = current_control_mode_getter
        self.set_control_mode_callback = set_control_mode_callback

    def speak(self, text):
        if self.ai_active: # Only speak if AI is active
            self.engine.say(text)
            self.engine.runAndWait()

    def extract_commands(self, text):
        pattern = r'\b[FBLRS]\d+\b(?:,\s*\b[FBLRS]\d+\b)*'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def send_to_arduino(self, command):
        if self.hardware_controller.arduino_connected and self.hardware_controller.arduino:
            try:
                self.hardware_controller.arduino.write((command + '\n').encode('utf-8'))
                self.hardware_controller.arduino.flush()
                print(f"[AI] Sent to Arduino: {command}")
                return True
            except Exception as e:
                print(f"[AI] Error sending command: {e}")
                return False
        else:
            print("[AI] Arduino not connected")
            return False

    def process_response(self, response):
        commands = self.extract_commands(response)
        if commands and len(commands.strip()) == len(response.strip()):
            self.send_to_arduino(commands)
            return None # If only commands, no need to print/speak Llama's text
        elif commands:
            self.send_to_arduino(commands)
            # Remove commands from the response text
            return re.sub(r'\b([FBLRS]\d+)(?:,\s*([FBLRS]\d+))*\b', '', response).strip()
        return response

    def query_llama(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "run", "arthur-mk1", prompt], # Added prompt correctly
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except FileNotFoundError:
            print("[AI] Ollama command not found. Please ensure Ollama is installed and in your PATH.")
            self.speak("Ollama command not found. Please install Ollama.")
            return None
        except Exception as e:
            print(f"[AI] Llama error: {e}")
            return None

    def run_voice_ai_loop(self):
        if self.current_control_mode_getter() != 'AI':
            print("AI control loop started but control mode is not AI. Exiting.")
            return

        self.ai_active = True
        print("🧠 AI CLI control is active. Type your question or command below.")
        self.speak("AI CLI control is now active.")

        while self.ai_active and self.current_control_mode_getter() == 'AI':
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'stop', 'quit', 'disable ai']:
                    self.speak("Shutting down AI.")
                    print("AI stopped.")
                    self.ai_active = False
                    self.set_control_mode_callback('BUTTONS') # Revert control mode
                    break

                response = self.query_llama(user_input)
                if response:
                    filtered_response = self.process_response(response)
                    if filtered_response:
                        print(f"Llama: {filtered_response}")
                        self.speak(filtered_response)
                        self.socketio.emit('ai_response', {'text': filtered_response})
            except KeyboardInterrupt:
                print("\n[Interrupted] Exiting AI mode.")
                self.ai_active = False
                self.set_control_mode_callback('BUTTONS')
                break
            except Exception as e:
                print(f"Error in AI loop: {e}")
                self.ai_active = False # Stop on unexpected error
                self.set_control_mode_callback('BUTTONS')
                break
        print("AI control loop ended.")


    def start_ai_thread(self):
        if self.ai_active:
            print("AI thread already running.")
            return
        # Ensure control mode is 'AI' before starting the thread
        if self.current_control_mode_getter() != 'AI':
            print("AI cannot be started: control mode is not 'AI'.")
            return
        ai_thread = threading.Thread(target=self.run_voice_ai_loop, daemon=True)
        ai_thread.start()
        print("AI Voice thread started.")

    def stop_ai(self):
        self.ai_active = False
        print("AI stop signal sent.")
        # The loop will check `self.ai_active` and exit.

