# Medicode Setup Instructions

## Prerequisites

### 1. UMLS License (Required)
You **MUST** obtain your own UMLS license before using this application.

1. Visit: https://uts.nlm.nih.gov/license.html
2. Create a UTS account
3. Accept the UMLS License Agreement
4. Download UMLS data files (2024AB or later recommended)

⚠️ **IMPORTANT**: UMLS data is copyrighted and cannot be redistributed. You are responsible for compliance with NLM license terms.

See [UMLS_LICENSE_NOTICE.md](UMLS_LICENSE_NOTICE.md) for complete details.

### 2. OpenAI API Key (Optional but Recommended)
For AI-powered analysis features:
1. Get API key from: https://platform.openai.com/api-keys
2. Set in `.env` file: `OPENAI_API_KEY=sk-...`

### 3. CMS DRG Data (Optional)
For DRG classification features:
1. Download from: https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps/ms-drg-classifications-and-software
2. Place in `medical-coding-app/drg_source/FY2025/` (adjust year as needed)
3. Follow instructions in [medical-coding-app/DRG_SOURCE_NOTICE.md](medical-coding-app/DRG_SOURCE_NOTICE.md)

## Installation Steps

### Option 1: Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/frasod/Medicode.git
   cd Medicode
   ```

2. **Set up UMLS data:**
   ```bash
   # Create directory for UMLS data
   mkdir -p medical-coding-app/umls_data
   
   # Copy your downloaded UMLS META files to:
   # medical-coding-app/umls_data/META/
   ```

3. **Configure environment:**
   ```bash
   cd medical-coding-app
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY if using AI features
   ```

4. **Build and run:**
   ```bash
   cd ..
   docker compose up -d
   ```

5. **Initialize UMLS (first time only):**
   ```bash
   # The app will automatically initialize UMLS on first run
   # This may take 5-15 minutes depending on your system
   ```

6. **Access the application:**
   Open your browser to: http://localhost:5009

### Option 2: Local Python Environment

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/frasod/Medicode.git
   cd Medicode/medical-coding-app
   ```

2. **Set up UMLS data:**
   ```bash
   mkdir -p umls_data
   # Copy your UMLS META files to umls_data/META/
   ```

3. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API_KEY if using AI features
   ```

6. **Initialize database and UMLS:**
   ```bash
   python init_db.py
   python init_umls_from_storage.py
   ```

7. **Run the application:**
   ```bash
   python run.py
   ```

8. **Access the application:**
   Open your browser to: http://localhost:5009

## Verification

After installation, verify:

- ✓ UMLS data is NOT in git: `git status` should not show `umls_data/`
- ✓ Application loads without errors
- ✓ Can enter clinical text and extract codes
- ✓ AI Analysis works (if OPENAI_API_KEY is set)
- ✓ DRG features work (if DRG data is configured)

## Directory Structure

```
Medicode/
├── medical-coding-app/
│   ├── app/                    # Application code
│   ├── umls_data/             # YOUR UMLS DATA (NOT IN GIT)
│   │   └── META/              # UMLS META files go here
│   ├── drg_source/            # YOUR DRG DATA (NOT IN GIT)
│   │   └── FY2025/            # CMS files go here
│   ├── instance/              # SQLite database (NOT IN GIT)
│   ├── .env                   # Environment config (NOT IN GIT)
│   └── requirements.txt       # Python dependencies
├── docker-compose.yml         # Docker configuration
├── README.md                  # Project overview
├── UMLS_LICENSE_NOTICE.md    # UMLS licensing information
└── SETUP_INSTRUCTIONS.md     # This file
```

## Troubleshooting

### UMLS Not Loading
- Ensure UMLS files are in `medical-coding-app/umls_data/META/`
- Check that you have `MRCONSO.RRF`, `MRSTY.RRF`, etc.
- Run initialization manually: `docker compose exec web python init_umls_from_storage.py`

### AI Features Not Working
- Verify OPENAI_API_KEY is set in `.env`
- Check API key is valid and has credits
- Review logs: `docker compose logs web`

### Docker Issues
- Rebuild: `docker compose down && docker compose up --build -d`
- Check logs: `docker compose logs -f web`
- Verify port 5009 is not in use

### Performance Issues
- UMLS initialization is CPU-intensive (normal on first run)
- Consider increasing Docker memory allocation
- QuickUMLS cache will improve performance after first use

## Security Notes

- Never commit `.env` files with API keys
- Never commit UMLS data or DRG source files
- Keep `instance/` directory private (contains user data)
- For production deployment, add authentication
- Review [UMLS_LICENSE_NOTICE.md](UMLS_LICENSE_NOTICE.md) for access control requirements

## Getting Help

- **GitHub Issues**: https://github.com/frasod/Medicode/issues
- **UMLS Support**: https://support.nlm.nih.gov/
- **CMS Questions**: https://www.cms.gov/

## License

See [LICENSE](LICENSE) for software license details.

UMLS and CMS DRG data have separate licensing requirements - see respective documentation.
