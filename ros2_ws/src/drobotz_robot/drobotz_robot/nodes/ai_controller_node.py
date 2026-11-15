import json
import os
import re
import threading

import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from drobotz_robot.protocol import extract_ai_command


_SYSTEM_PROMPT = """You are DROBOTZ, a robot-control assistant.
Movement tokens: F=forward, B=backward, L=left, R=right, S=stop.
For movement requests include tokens with durations in milliseconds, such as F1000 or L500.
Use commas between commands, keep durations between 300 and 5000 ms, and end every movement
sequence with S. Be concise and prioritize safety. Never claim an action was sent unless a
movement token is present in your answer."""


class AIControllerNode(Node):
    """Queries an OpenAI-compatible endpoint and publishes only bounded movement tokens."""

    def __init__(self):
        super().__init__("drobotz_ai_controller")
        self.declare_parameter("provider", os.getenv("AI_PROVIDER", "openai"))
        self.declare_parameter("base_url", os.getenv("AI_BASE_URL", ""))
        self.declare_parameter("model", os.getenv("AI_MODEL", "gpt-4o-mini"))
        self.declare_parameter("max_tokens", 300)
        self.declare_parameter("temperature", 0.4)
        self.declare_parameter("timeout_sec", 25.0)
        self.declare_parameter("enable_tts", True)
        self._mode = "BUTTONS"
        self._busy = threading.Lock()
        self._api_key = os.getenv("AI_API_KEY", "").strip()
        self._base_url = str(self.get_parameter("base_url").value).strip()
        if not self._base_url:
            provider = str(self.get_parameter("provider").value).lower()
            endpoints = {
                "openai": "https://api.openai.com/v1/chat/completions",
                "groq": "https://api.groq.com/openai/v1/chat/completions",
                "ollama": "http://localhost:11434/v1/chat/completions",
            }
            self._base_url = endpoints.get(provider, endpoints["openai"])
        self._command_publisher = self.create_publisher(String, "/drobotz/cmd/ai", 10)
        self._response_publisher = self.create_publisher(String, "/drobotz/ai/response", 10)
        self._speech_engine = None
        self.create_subscription(String, "/drobotz/control_mode", self._mode_callback, 10)
        self.create_subscription(String, "/drobotz/ai/prompt", self._prompt_callback, 10)
        self._initialize_speech()
        self.get_logger().info("AI controller ready; configure AI_API_KEY to enable a hosted provider.")

    def _mode_callback(self, message):
        self._mode = message.data.strip().upper()

    def _prompt_callback(self, message):
        prompt = message.data.strip()
        if self._mode != "AI":
            self._publish_response("AI mode is not active. Enable AI mode before sending a prompt.", "error")
            return
        if not prompt:
            self._publish_response("Please enter a message.", "error")
            return
        if not self._busy.acquire(blocking=False):
            self._publish_response("The previous AI request is still in progress.", "error")
            return
        threading.Thread(target=self._query, args=(prompt,), daemon=True).start()

    def _query(self, prompt):
        try:
            if not self._api_key and "localhost" not in self._base_url:
                raise ValueError("AI_API_KEY is not set.")
            response = requests.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                    "Content-Type": "application/json",
                },
                json={
                    "model": str(self.get_parameter("model").value),
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": int(self.get_parameter("max_tokens").value),
                    "temperature": float(self.get_parameter("temperature").value),
                    "stream": False,
                },
                timeout=float(self.get_parameter("timeout_sec").value),
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload["choices"][0]["message"]["content"].strip()
            if self._mode != "AI":
                self._publish_response("AI mode was disabled before the response arrived.", "inactive")
                return
            command = extract_ai_command(answer)
            if command:
                message = String()
                message.data = command
                self._command_publisher.publish(message)
            self._publish_response(answer, "done", command=command)
            self._speak(answer)
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            self.get_logger().error(f"AI request failed: {exc}")
            self._publish_response(f"AI service error: {exc}", "error")
        finally:
            self._busy.release()

    def _initialize_speech(self):
        if not self.get_parameter("enable_tts").value:
            return
        try:
            import pyttsx3

            self._speech_engine = pyttsx3.init()
            self._speech_engine.setProperty("rate", 150)
            self._speech_engine.setProperty("volume", 0.9)
        except (ImportError, OSError, RuntimeError) as exc:
            self.get_logger().warning(f"Text-to-speech is unavailable: {exc}")

    def _speak(self, response):
        if self._speech_engine is None:
            return
        speech_text = re.sub(r"\b[FBLRS]\d*\b", "", response, flags=re.IGNORECASE)
        speech_text = re.sub(r"\s+", " ", speech_text).strip(" ,→")
        if not speech_text:
            return
        try:
            self._speech_engine.say(speech_text)
            self._speech_engine.runAndWait()
        except (OSError, RuntimeError) as exc:
            self.get_logger().warning(f"Text-to-speech failed: {exc}")
            self._speech_engine = None

    def _publish_response(self, text, status, command=None):
        message = String()
        message.data = json.dumps(
            {"text": text, "status": status, "command": command}, allow_nan=False
        )
        self._response_publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = AIControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
