# ngrok_setup.py
from pyngrok import ngrok

# Start ngrok tunnel
public_url = ngrok.connect(8000)
print(f"Ngrok tunnel created: {public_url}")

# Keep the tunnel open
input("Press Enter to stop ngrok...")
ngrok.kill()