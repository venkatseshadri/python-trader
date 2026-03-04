# Flattrade Authentication Flow

## Steps to get token:

### Step 1: Generate Authorization URL


### Step 2: Get Request Code
- Open the auth_url in browser
- Login with your Flattrade credentials  
- You'll be redirected to your callback URL with request_code=XXX

### Step 3: Exchange for Token


### Step 4: Use Token
- Add token to creds file or use set_token()

## Note:
- Token doesn't expire unless you regenerate it
