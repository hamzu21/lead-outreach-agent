import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE

def main():
    print("🔑 Starting Google OAuth Authorization Flow...")
    print(f"Scopes requested: {SCOPES}")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: {CREDENTIALS_FILE} not found!")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    
    token_json = creds.to_json()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token_json)
        
    print(f"✅ Fresh token saved to {TOKEN_FILE} successfully!")
    print("\nBelow is your updated GOOGLE_TOKEN_JSON string for .env:\n")
    print(token_json)

if __name__ == "__main__":
    main()
