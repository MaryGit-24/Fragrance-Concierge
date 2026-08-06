"""
SME Ally - Fragrance Concierge
Guarded proxy for the self-hosted model

WHAT THIS FILE DOES, IN PLAIN TERMS:
Ollama runs your AI model locally on the GPU instance, but only answers
requests from that same machine. This script sits in front of Ollama and
does two simple things:

  1. Checks that whoever is asking included the correct secret key.
     Without this, anyone who finds your instance's address could use
     your GPU for free.
  2. If the key is correct, it forwards the question to Ollama, waits
     for the answer, and sends it back.

This is the whole idea behind what's usually called "an API with an
API key." Nothing more mysterious than that.

HOW TO RUN THIS ON THE GPU INSTANCE:
1. Make sure Ollama is already running (ollama serve, or it runs by
   default after install on most setups).
2. Install one small package this script needs:
       pip install flask --break-system-packages
3. Change SECRET_KEY below to something only you know.
4. Run this script:
       python3 guarded_proxy.py
5. This will now listen on port 8000. That is the address your
   concierge webpage should talk to, not Ollama's port directly.
"""

from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Change this to your own secret. Treat it like a password.
# Your concierge webpage will need to send this exact value with
# every request, or it gets rejected.
SECRET_KEY = "change-this-to-your-own-secret"

# This is Ollama's own local address, only reachable from this machine.
OLLAMA_URL = "http://localhost:11434/api/chat"

# Which model to use. Change this to whichever one you pulled.
MODEL_NAME = "llama3.1:8b-instruct-q4_0"


@app.route("/ask", methods=["POST"])
def ask():
    # Step 1: check the password
    provided_key = request.headers.get("X-API-Key", "")
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Invalid or missing key"}), 401

    # Step 2: read what the concierge page sent
    body = request.get_json()
    system_prompt = body.get("system", "")
    user_message = body.get("message", "")

    # Step 3: ask Ollama the question, in the format Ollama expects
    ollama_payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=ollama_payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        # Ollama returns the answer inside result["message"]["content"]
        answer_text = result.get("message", {}).get("content", "")
        return jsonify({"answer": answer_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 0.0.0.0 means "listen for requests coming from outside this machine"
    # not just from itself. This is what makes it reachable at all.
    app.run(host="0.0.0.0", port=8000)
