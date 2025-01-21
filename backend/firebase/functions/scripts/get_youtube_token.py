from google_auth_oauthlib.flow import InstalledAppFlow
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

def get_refresh_token():
    """Get a refresh token for testing and save it to test.env."""
    # Get the path to test.env
    test_env_path = Path(__file__).parent.parent / 'test.env'
    
    # Check if we have a valid token already
    if test_env_path.exists():
        load_dotenv(test_env_path)
        token = os.getenv('YOUTUBE_REAL_REFRESH_TOKEN')
        expiry_str = os.getenv('YOUTUBE_TOKEN_EXPIRY')
        
        if token and expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str)
                if expiry > datetime.now(timezone.utc):
                    print(f"Valid token exists until {expiry}")
                    return
            except ValueError:
                pass  # Invalid date format, continue to get new token
    
    # Get new token
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json',
        scopes=['https://www.googleapis.com/auth/youtube.readonly']
    )
    
    credentials = flow.run_local_server(port=8080)
    
    # Read existing content
    existing_content = ""
    if test_env_path.exists():
        with open(test_env_path, 'r') as f:
            existing_content = f.read()
    
    # Prepare new content
    lines = existing_content.splitlines()
    new_lines = []
    token_added = False
    expiry_added = False
    
    # Set expiry to 7 days from now (refresh tokens typically last longer,
    # but we'll be conservative)
    expiry = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=7)

    print(f"Credentials:\nREFRESH TOKEN: {credentials.refresh_token}\nEXPIRY: {expiry}\nCREDENTIALS EXPIRY:{credentials.expiry}\n")
    print(f"TOKEN: {credentials.token}")
    if credentials.refresh_token == None:
        credentials.refresh()
        print(f"REFRESHED TOKEN: {credentials.refresh_token}")
    for line in lines:
        if line.startswith('YOUTUBE_REAL_REFRESH_TOKEN='):
            new_lines.append(f'YOUTUBE_REAL_REFRESH_TOKEN="{credentials.refresh_token}"')
            token_added = True
        elif line.startswith('YOUTUBE_TOKEN_EXPIRY='):
            new_lines.append(f'YOUTUBE_TOKEN_EXPIRY="{expiry.isoformat()}"')
            expiry_added = True
        else:
            new_lines.append(line)
    
    if not token_added:
        new_lines.append(f'YOUTUBE_REAL_REFRESH_TOKEN="{credentials.refresh_token}"')
    if not expiry_added:
        new_lines.append(f'YOUTUBE_TOKEN_EXPIRY="{expiry.isoformat()}"')
    
    # Write back to file
    with open(test_env_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"New refresh token has been saved to {test_env_path}")
    print(f"Token will be considered valid until {expiry}")
    
if __name__ == "__main__":
    get_refresh_token() 