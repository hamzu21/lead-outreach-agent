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
    
    # Automatically update .env file
    env_file = ".env"
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            updated = False
            token_line = f"GOOGLE_TOKEN_JSON='{token_json}'\n"
            for line in lines:
                if line.startswith("GOOGLE_TOKEN_JSON="):
                    new_lines.append(token_line)
                    updated = True
                else:
                    new_lines.append(line)
            if not updated:
                new_lines.append(token_line)
            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print("✅ Automatically updated GOOGLE_TOKEN_JSON in your local .env file!")
        except Exception as e:
            print(f"Warning updating .env file: {e}")

    print("\nCopy the following token string for your AWS server .env:\n")
    print(f"GOOGLE_TOKEN_JSON='{token_json}'")

if __name__ == "__main__":
    main()
