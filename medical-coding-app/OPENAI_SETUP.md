# OpenAI Integration Setup Guide

This medical coding application now includes AI-powered DRG (Diagnosis Related Group) analysis using OpenAI's GPT-4o model.

## Features

The AI analysis provides:
1. **ICD-10 Code Review**: Reviews and selects only appropriate ICD-10 codes from NLP extraction
2. **DRG Code Determination**: Determines the most accurate MS-DRG codes based on clinical context
3. **Complexity Assessment**: Provides complexity levels (Low, Medium, High) with detailed reasoning
4. **Coding Recommendations**: Suggests improvements for better coding and documentation

## Setup Instructions

### 1. Obtain an OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section: https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (it will only be shown once!)

### 2. Configure Environment Variables

The `.env` file has already been created in the `medical-coding-app/` directory.

**Edit the `.env` file** and add your OpenAI API key:

```bash
# OpenAI Configuration for AI-powered DRG Analysis
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-your-actual-api-key-here

# AI Features Toggle (set to 1 to enable, 0 to disable)
ENABLE_OPENAI_DRG=1
```

**Important**: 
- Replace `sk-proj-your-actual-api-key-here` with your real OpenAI API key
- The `.env` file is already in `.gitignore` and will NOT be committed to version control
- NEVER share your API key or commit it to Git

### 3. Restart the Application

If running with Docker:
```bash
docker compose down
docker compose up --build
```

If running locally:
```bash
# The .env file will be automatically loaded
python run.py
```

## How to Use

### Two-Step Workflow:

#### Step 1: NLP Analysis (Traditional)
1. Enter your clinical note in the text area
2. Click "Extract Codes" button
3. Review the NLP-extracted medical concepts and ICD-10 codes

#### Step 2: AI Analysis (Optional)
1. After NLP extraction, click the **"🧠 Analyze with AI"** button
2. The AI will:
   - Review and refine the ICD-10 codes from NLP
   - Determine appropriate MS-DRG codes
   - Assess complexity level
   - Provide coding recommendations
3. View the AI analysis results panel

## API Costs

- **Model Used**: GPT-4o
- **Estimated Cost**: ~$0.01 - $0.05 per analysis
- Monitor your usage at: https://platform.openai.com/usage

## Disable AI Analysis

To disable AI analysis and use only traditional NLP:

Edit `.env`:
```bash
ENABLE_OPENAI_DRG=0
```

Or remove the `OPENAI_API_KEY` from the `.env` file.

## Security Best Practices

✅ **DO:**
- Keep your API key secure and private
- Use environment variables for sensitive data
- Monitor your API usage regularly
- Set billing limits on your OpenAI account

❌ **DON'T:**
- Commit `.env` files to Git (already in `.gitignore`)
- Share your API keys in chat, email, or screenshots
- Use API keys in client-side code
- Leave unused API keys active

## Troubleshooting

### "AI analysis is not enabled"
- Check that `ENABLE_OPENAI_DRG=1` in `.env`
- Verify `OPENAI_API_KEY` is set correctly
- Restart the application

### "Error: Incorrect API key provided"
- Double-check your API key from OpenAI Platform
- Ensure no extra spaces or quotes in `.env`
- Verify the key starts with `sk-`

### "Rate limit exceeded"
- You've hit OpenAI's rate limits
- Wait a few moments and try again
- Consider upgrading your OpenAI plan

## Support

For issues related to:
- **OpenAI API**: https://platform.openai.com/docs
- **Billing**: https://platform.openai.com/account/billing
- **Application**: Check application logs or contact support
