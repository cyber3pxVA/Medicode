# Git Commit Guide for Medicode

## Before Committing

**ALWAYS** run the verification script before committing:

```bash
./verify_commit.sh
```

This checks for:
- UMLS data files (must not be committed)
- CMS DRG source files (must not be committed)
- .env files with secrets
- Database files with user data
- Required .gitignore patterns

## What to Commit

### Safe Files to Commit:
✅ Application code (Python, HTML, CSS, JavaScript)
✅ Documentation (README.md, SETUP_INSTRUCTIONS.md, etc.)
✅ Sample data files (< 20 lines, clearly marked as samples)
✅ Configuration templates (.env.example)
✅ Scripts and utilities
✅ Docker configuration files
✅ Requirements and dependency files
✅ .gitignore file

### Files to NEVER Commit:
❌ `umls_data/` directory or any UMLS RRF files
❌ `drg_source/` directory with full CMS datasets
❌ `.env` files with API keys or secrets
❌ `instance/` directory with SQLite databases
❌ Any files with user data
❌ Large data files (> 1MB typically indicates data)
❌ `__pycache__/` or other build artifacts
❌ `quickumls_cache/` or other cache directories

## Commit Workflow

### 1. Check Status
```bash
git status
```

### 2. Run Verification
```bash
./verify_commit.sh
```

If verification fails, fix issues before proceeding!

### 3. Add Files
```bash
# Add all safe files
git add .

# OR add specific files
git add medical-coding-app/app/templates/index.html
git add README.md
git add SETUP_INSTRUCTIONS.md
```

### 4. Commit
```bash
git commit -m "Your descriptive commit message"
```

### 5. Push to GitHub
```bash
git push origin master
```

## Common Scenarios

### Accidentally Staged a Protected File
```bash
# Remove from staging but keep the file locally
git rm --cached <file>

# Add the pattern to .gitignore if not already there
echo "pattern/" >> .gitignore
git add .gitignore
```

### Large File Accidentally Committed
```bash
# Remove from history (use carefully!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <file>" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (be careful with this!)
git push origin --force --all
```

### Update .gitignore for New Pattern
```bash
# Add the pattern
echo "new_pattern/" >> .gitignore

# If files matching pattern are already tracked
git rm --cached -r new_pattern/

# Commit the changes
git add .gitignore
git commit -m "Update .gitignore to exclude new_pattern/"
```

## Current Repository Status

Run this to see what needs to be committed:
```bash
git status
```

Run this to see what files are tracked:
```bash
git ls-files
```

## Best Practices

1. **Always run verification before pushing**
2. **Use meaningful commit messages**
3. **Commit related changes together**
4. **Don't commit generated files**
5. **Keep commits focused and atomic**
6. **Review changes before committing**: `git diff`
7. **Document breaking changes in commit messages**

## Current Changes Ready to Commit

Based on recent work, these files have changes:

- `medical-coding-app/app/templates/index.html` - Added GitHub link, removed icon, added delete functionality
- `medical-coding-app/app/main/routes.py` - Added delete endpoints for history
- `medical-coding-app/app/models/db.py` - Added ClinicalNoteHistory model
- `README.md` - Updated with Medicode branding
- `dev_log.md` - Added development notes
- `SETUP_INSTRUCTIONS.md` - New setup guide
- `verify_commit.sh` - New verification script
- Other modified files from recent features

## Quick Commit Commands

```bash
# See what changed
git status

# Run verification
./verify_commit.sh

# Add all changes (after verification passes)
git add .

# Commit with descriptive message
git commit -m "Add history delete feature and GitHub link

- Remove emoji icon from History button
- Add individual delete buttons for history entries
- Add Delete All button for clearing history
- Create backend DELETE endpoints
- Add GitHub repository link below title
- Create setup instructions for new installations
- Add verification script to prevent committing proprietary files
"

# Push to GitHub
git push origin master
```

## Emergency: Remove Sensitive Data

If sensitive data was committed:

1. **Stop immediately** - don't push!
2. Use `git reset --soft HEAD~1` to undo the last commit
3. Remove the files: `git rm --cached <file>`
4. Add to .gitignore
5. Commit again without the sensitive files

If already pushed to GitHub:
1. Contact repository admins immediately
2. Consider the data compromised
3. Rotate any exposed API keys or credentials
4. May need to rewrite history (complex, seek help)

## Resources

- Git Documentation: https://git-scm.com/doc
- GitHub Guides: https://guides.github.com/
- .gitignore patterns: https://git-scm.com/docs/gitignore
