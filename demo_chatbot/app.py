from flask import Flask, request, Response, render_template, jsonify
from flask_cors import CORS
import os
import json
import re
import time
import threading
import queue
from dotenv import load_dotenv
import openai
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize API clients
openai.api_key = os.getenv("OPENAI_API_KEY")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

def extract_translation(text):
    """
    Extract text between the last set of <translation> and </translation> tags
    """
    pattern = r'<translation>(.*?)</translation>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        # Return the last match (from the last set of translation tags)
        return matches[-1].strip()
    return ""

def generate_openai_stream(prompt, response_queue):
    """
    Generate a stream of responses from OpenAI's GPT-4o
    """
    try:
        translation_buffer = ""
        stream = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                translation_buffer += content
                
                extracted = extract_translation(translation_buffer)
                if extracted:
                    response_queue.put({"translation": extracted})
                else:
                    response_queue.put({"partialResponse": translation_buffer})
                    
        response_queue.put({"done": True})
    except Exception as e:
        print(f"OpenAI error: {str(e)}")
        response_queue.put({"error": str(e)})
        response_queue.put({"done": True})

def generate_groq_stream(prompt, response_queue):
    """
    Generate a stream of responses from Groq's Llama 3.3
    """
    try:
        translation_buffer = ""
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                translation_buffer += content
                
                extracted = extract_translation(translation_buffer)
                if extracted:
                    response_queue.put({"translation": extracted})
                else:
                    response_queue.put({"partialResponse": translation_buffer})
                    
        response_queue.put({"done": True})
    except Exception as e:
        print(f"Groq error: {str(e)}")
        response_queue.put({"error": str(e)})
        response_queue.put({"done": True})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST', 'GET'])
def translate():
    # Handle GET requests for SSE
    if request.method == 'GET':
        try:
            data = json.loads(request.args.get('data', '{}'))
            hawaiian_text = data.get('hawaiianText', '')
            model_type = data.get('modelType', 'fast')
            natural_translation = data.get('naturalTranslation', False)
        except Exception as e:
            return jsonify({"error": f"Invalid request data: {str(e)}"}), 400
    # Handle POST requests
    else:
        data = request.json
        hawaiian_text = data.get('hawaiianText', '')
        model_type = data.get('modelType', 'fast')
        natural_translation = data.get('naturalTranslation', False)
    
    if not hawaiian_text:
        return jsonify({"error": "No Hawaiian text provided"}), 400
    
    # Set prompt based on translation type
    prompt = (
        f"Translate the following Hawaiian text to natural English. Wrap your final translation in <translation> </translation> tags. Here is the Hawaiian text: {hawaiian_text}"
        if natural_translation
        else f"Translate the following Hawaiian text to English. Wrap your final translation in <translation> </translation> tags. Here is the Hawaiian text: {hawaiian_text}"
    )
    
    # Create a response queue for thread communication
    response_queue = queue.Queue()
    
    # Start the appropriate translation thread
    if model_type == 'best':
        threading.Thread(
            target=generate_openai_stream, 
            args=(prompt, response_queue)
        ).start()
    else:
        threading.Thread(
            target=generate_groq_stream, 
            args=(prompt, response_queue)
        ).start()
    
    # Create a generator for SSE streaming
    def generate():
        while True:
            try:
                data = response_queue.get(timeout=60)  # Wait up to 60 seconds for new data
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get('done', False) or data.get('error'):
                    break
            except queue.Empty:
                # Timeout, end the stream
                yield f"data: {json.dumps({'error': 'Translation timeout', 'done': True})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True, threaded=True)