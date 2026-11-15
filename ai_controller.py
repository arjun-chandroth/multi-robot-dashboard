import os
import re
import threading
import time
import logging
import requests
from typing import Optional, Dict, Any
import json

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

        # AI API Configuration
        self.ai_config = self._load_ai_config()
        
        # Validate API key on startup
        self._validate_api_key()
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
        except Exception as e:
            self.logger.warning(f"Could not initialize TTS engine: {e}")
            self.engine = None

    def _load_ai_config(self) -> Dict[str, Any]:
        """Load AI configuration from environment variables"""
        config = {
            'provider': os.getenv('AI_PROVIDER', 'openai').lower(),
            'api_key': os.getenv('AI_API_KEY', '').strip(),
            'base_url': os.getenv('AI_BASE_URL', ''),
            'model': os.getenv('AI_MODEL', 'gpt-3.5-turbo'),
            'max_tokens': int(os.getenv('AI_MAX_TOKENS', '500')),
            'temperature': float(os.getenv('AI_TEMPERATURE', '0.7')),
            'timeout': int(os.getenv('AI_TIMEOUT', '30'))
        }
        
        # Set default OpenAI endpoint
        if config['provider'] == 'openai' and not config['base_url']:
            config['base_url'] = 'https://api.openai.com/v1/chat/completions'
            
        return config

    def _validate_api_key(self):
        """Validate the OpenAI API key format"""
        api_key = self.ai_config['api_key']
        if not api_key:
            self.logger.error("❌ AI_API_KEY not found in environment variables")
            self.logger.info("💡 Please set AI_API_KEY in your .env file")
            return False
            
        if api_key.startswith('sk-proj-'):
            self.logger.info("✅ Valid OpenAI API key detected (new format)")
            return True
        elif api_key.startswith('sk-'):
            self.logger.info("✅ Valid OpenAI API key detected (legacy format)")
            return True
        else:
            self.logger.error("❌ Invalid OpenAI API key format")
            return False

    def speak(self, text: str) -> None:
        if self.engine and self.ai_active:
            try:
                self.logger.debug(f"Speaking: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS Error: {e}")

    def extract_commands(self, text: str) -> Optional[str]:
        command_pattern = r'\b([FBLRS]\d*)(?:,\s*([FBLRS]\d*))*\b'
        match = re.search(command_pattern, text)
        if match:
            commands = [cmd for cmd in match.groups() if cmd]
            return ' '.join(commands)
        return None

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
        
        if commands:
            # Send commands to Arduino
            self.send_to_arduino(commands)
            
            # Remove commands from response for TTS
            response_without_commands = re.sub(r'\b([FBLRS]\d*)(?:,\s*([FBLRS]\d*))*\b', '', response).strip()
            return response_without_commands if response_without_commands else None
            
        return response

    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API with your specific key"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.ai_config['api_key']}"
        }
        
        system_message = '''You are ROVER - an AI assistant controlling an autonomous robot. 
You can send movement commands to control the robot:

MOVEMENT COMMANDS:
- F = Move Forward
- B = Move Backward  
- L = Turn Left
- R = Turn Right  
- S = Stop immediately

You can combine commands with numbers for duration:
- "F100" = Move forward for 100ms
- "L50,R50" = Turn left 50ms, then right 50ms
- "F200,B100" = Forward 200ms, backward 100ms

RESPONSE GUIDELINES:
1. If user asks to move, include the appropriate command
2. Keep responses concise and helpful
3. Always prioritize safety
4. Explain what you're doing when sending commands

Example responses:
- "Moving forward → F200"
- "Turning left and right → L100,R100"  
- "Stopping the robot → S"
- "I'll help you explore! Moving forward carefully → F150"'''
        
        payload = {
            'model': self.ai_config['model'],
            'messages': [
                {
                    'role': 'system',
                    'content': system_message
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            'max_tokens': self.ai_config['max_tokens'],
            'temperature': self.ai_config['temperature'],
            'stream': False
        }
        
        self.logger.info(f"🔮 Calling OpenAI API with model: {self.ai_config['model']}")
        
        response = requests.post(
            self.ai_config['base_url'],
            headers=headers,
            json=payload,
            timeout=self.ai_config['timeout']
        )
        
        if response.status_code != 200:
            error_msg = f"API Error {response.status_code}: {response.text}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def query_ai_api(self, prompt: str) -> None:
        """Query the configured AI API"""
        self.thinking = True
        self.logger.info(f"🤖 AI Query: {prompt}")
        self.socketio.emit('ai_response', {'text': 'Thinking...', 'status': 'streaming'})

        try:
            if not self.ai_config['api_key']:
                raise ValueError("OpenAI API key not configured")

            start_time = time.time()
            full_response = self._call_openai_api(prompt)
            response_time = time.time() - start_time
            
            self.logger.info(f"✅ AI Response received in {response_time:.2f}s: {full_response}")

            # Emit the full response
            self.socketio.emit('ai_response', {
                'text': full_response,
                'status': 'done',
                'response_time': f"{response_time:.2f}s"
            })

            # Process commands and speak response
            filtered_response = self.process_response(full_response)
            if filtered_response:
                self.speak(filtered_response)

        except requests.exceptions.Timeout:
            error_msg = "AI request timed out. Please try again."
            self.logger.error(error_msg)
            self.socketio.emit('ai_response', {
                'text': error_msg, 
                'status': 'error'
            })
        except Exception as e:
            self.logger.error(f"AI API error: {str(e)}")
            self.socketio.emit('ai_response', {
                'text': f"AI Service Error: {str(e)}", 
                'status': 'error'
            })
        finally:
            self.thinking = False

    def query_llama(self, prompt: str) -> None:
        """Main method to query AI (now using OpenAI API)"""
        self.query_ai_api(prompt)

    def run_voice_ai_loop(self) -> None:
        if self.current_control_mode_getter() != 'AI':
            self.logger.warning("AI loop started in wrong mode.")
            return
            
        self.ai_active = True
        self.logger.info("🚀 AI control loop started with OpenAI API")
        self.speak("AI control is now active with OpenAI.")
        
        self.socketio.emit('ai_response', {
            'text': f"🤖 AI Mode Activated! Using {self.ai_config['model']}. How can I assist with robot controls?",
            'status': 'active',
            'model': self.ai_config['model']
        })
        
        try:
            while self.ai_active and self.current_control_mode_getter() == 'AI':
                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"AI loop error: {e}")
        finally:
            self.logger.info("🛑 AI control loop ended")
            self.ai_active = False

    def start_ai_thread(self) -> None:
        if self.ai_active:
            self.logger.warning("AI thread already running")
            return
            
        if not self.ai_config['api_key']:
            self.logger.error("❌ Cannot start AI thread - API key not configured")
            self.socketio.emit('ai_response', {
                'text': "Error: OpenAI API key not configured. Please check your .env file.",
                'status': 'error'
            })
            return
            
        self.ai_thread = threading.Thread(
            target=self.run_voice_ai_loop,
            daemon=True
        )
        self.ai_thread.start()
        self.logger.info("✅ AI thread started with OpenAI API")

    def stop_ai(self) -> None:
        self.logger.info("🛑 Stopping AI controller")
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

    def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI configuration status"""
        return {
            'provider': self.ai_config['provider'],
            'model': self.ai_config['model'],
            'api_key_configured': bool(self.ai_config['api_key']),
            'ai_active': self.ai_active,
            'thinking': self.thinking
        }
