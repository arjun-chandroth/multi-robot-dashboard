from dotenv import load_dotenv
load_dotenv()
import os
import requests
import time

print("🤖 Testing Groq API with correct model...")

headers = {
    'Authorization': f"Bearer {os.getenv('AI_API_KEY')}",
    'Content-Type': 'application/json'
}

# Test multiple models to find which work
models_to_test = [
    'llama-3.1-8b-instant',
    'llama-3.2-1b-preview', 
    'llama-3.2-3b-preview',
    'llama-3.1-70b-versatile',
    'mixtral-8x7b-32768'
]

for model in models_to_test:
    print(f"\n🔄 Testing model: {model}")
    
    data = {
        'model': model,
        'messages': [
            {
                'role': 'system', 
                'content': 'You are a robot assistant. Respond in one sentence.'
            },
            {
                'role': 'user', 
                'content': 'Say hello and confirm you are ready for robot control!'
            }
        ],
        'max_tokens': 100,
        'temperature': 0.7
    }

    try:
        start_time = time.time()
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions', 
            headers=headers, 
            json=data, 
            timeout=10
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            response_text = result['choices'][0]['message']['content']
            print(f"✅ SUCCESS: {response_time:.2f}s")
            print(f"   Response: {response_text}")
            print(f"   ✅ This model works! Use: AI_MODEL={model}")
            break
        else:
            print(f"❌ Failed: {response.status_code} - {response.json().get('error', {}).get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
