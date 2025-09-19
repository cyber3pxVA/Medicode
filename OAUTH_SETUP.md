# Google OAuth Setup Guide

## Setting up Google OAuth for Medical Coding App

### 1. Create Google Cloud Project OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (`gen-lang-client-0486153020`)
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth 2.0 Client IDs**
5. If prompted, configure the OAuth consent screen first:
   - Choose **External** user type
   - Fill in required fields:
     - App name: "Medical Coding Application"
     - User support email: your email
     - Developer contact: your email
   - Add scopes: `email`, `profile`, `openid`
   - Add test users (your Gmail addresses)

### 2. Configure OAuth Client

1. Select **Web application** as application type
2. Name: "Medical Coding Web App"
3. Add **Authorized JavaScript origins**:
   - `http://localhost:8080` (for local development)
   - `https://your-cloud-run-service-url` (for production)
4. Add **Authorized redirect URIs**:
   - `http://localhost:8080/login` (for local development)
   - `https://your-cloud-run-service-url/login` (for production)
5. Click **CREATE**

### 3. Save Credentials

1. Download the client configuration JSON file
2. Note the **Client ID** and **Client Secret**

### 4. Set Environment Variables

#### For Local Development:
```bash
export GOOGLE_CLIENT_ID="your-client-id.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

Or add to `.env` file:
```env
GOOGLE_CLIENT_ID=your-client-id.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

#### For Cloud Run:
```bash
# Set substitution variables for Cloud Build
gcloud config set builds/substitutions _GOOGLE_CLIENT_ID="your-client-id.googleusercontent.com"
gcloud config set builds/substitutions _GOOGLE_CLIENT_SECRET="your-client-secret"
```

### 5. Test Authentication

1. Start the app locally:
   ```bash
   cd medical-coding-app
   python run.py
   ```

2. Visit `http://localhost:8080`
3. You should see a "Sign in with Google" button
4. Click it and sign in with your Gmail account

### 6. Deploy to Cloud Run

1. Commit and push changes:
   ```bash
   git add .
   git commit -m "🔐 Add Google OAuth authentication"
   git push origin master
   ```

2. The Cloud Build will automatically deploy with OAuth support

### Troubleshooting

- **"Error 400: redirect_uri_mismatch"**: Add your actual URLs to authorized redirect URIs
- **"Error 403: access_blocked"**: Add your email to test users in OAuth consent screen
- **No Google sign-in button**: Check that GOOGLE_CLIENT_ID environment variable is set

### Security Notes

- Never commit OAuth credentials to version control
- Use environment variables for all sensitive configuration
- The OAuth consent screen should be in "Testing" mode initially
- Add only trusted users to the test user list