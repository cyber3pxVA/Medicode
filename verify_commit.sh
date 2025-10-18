#!/bin/bash
# Pre-commit verification script to ensure no proprietary files are committed
# Run this before committing to GitHub

set -e

echo "🔍 Checking for proprietary files before commit..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any issues found
ISSUES_FOUND=0

# Check for UMLS data files
echo "Checking for UMLS data files..."
UMLS_FILES=$(git ls-files | grep -iE "(\.RRF$|\.ctl$|MRCONSO|MRSTY|MRREL|MRSAT|MRDEF|MRHIER|MRXW|MRXNS|AMBIG|MRCUI|MRCOLS|MRDOC|MRFILES|MRMAP|MRRANK|MRSAB|MRSMAP|quickumls_cache|/umls_data/|/META/)" || true)

if [ -n "$UMLS_FILES" ]; then
    echo -e "${RED}❌ FOUND UMLS DATA FILES IN GIT:${NC}"
    echo "$UMLS_FILES"
    echo ""
    echo -e "${YELLOW}These files are copyrighted by NLM and MUST NOT be committed!${NC}"
    echo "Run: git rm --cached <file>"
    echo "And ensure patterns are in .gitignore"
    ISSUES_FOUND=1
else
    echo -e "${GREEN}✓ No UMLS data files found${NC}"
fi

echo ""

# Check for CMS DRG source files (full datasets, not sample mappings)
echo "Checking for CMS DRG source files..."
DRG_SOURCE_FILES=$(git ls-files | grep -iE "(drg_source/.*\.(csv|txt|zip|xlsx|xls)$|msdrgv[0-9]|FY202[0-9]/[^/]+\.(csv|txt|zip))" || true)

if [ -n "$DRG_SOURCE_FILES" ]; then
    echo -e "${RED}❌ FOUND CMS DRG SOURCE FILES IN GIT:${NC}"
    echo "$DRG_SOURCE_FILES"
    echo ""
    echo -e "${YELLOW}Raw CMS files should not be committed!${NC}"
    echo "Only sample mappings (< 20 lines) should be in the repo."
    ISSUES_FOUND=1
else
    echo -e "${GREEN}✓ No CMS DRG source files found${NC}"
fi

echo ""

# Check for .env files with secrets
echo "Checking for .env files with secrets..."
ENV_FILES=$(git ls-files | grep -E "\.env$|\.env\..*" | grep -v "\.env\.example" || true)

if [ -n "$ENV_FILES" ]; then
    echo -e "${RED}❌ FOUND .env FILES IN GIT:${NC}"
    echo "$ENV_FILES"
    echo ""
    echo -e "${YELLOW}Environment files may contain API keys and secrets!${NC}"
    echo "Run: git rm --cached <file>"
    ISSUES_FOUND=1
else
    echo -e "${GREEN}✓ No .env files found${NC}"
fi

echo ""

# Check for database files
echo "Checking for database files..."
DB_FILES=$(git ls-files | grep -E "\.(db|sqlite|sqlite3)$|/instance/" || true)

if [ -n "$DB_FILES" ]; then
    echo -e "${RED}❌ FOUND DATABASE FILES IN GIT:${NC}"
    echo "$DB_FILES"
    echo ""
    echo -e "${YELLOW}Database files may contain user data and should not be committed!${NC}"
    ISSUES_FOUND=1
else
    echo -e "${GREEN}✓ No database files found${NC}"
fi

echo ""

# Check for large files that might be data
echo "Checking for large files (> 1MB)..."
LARGE_FILES=$(git ls-files | while read file; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$size" -gt 1048576 ]; then
            echo "$file ($(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo "${size} bytes"))"
        fi
    fi
done)

if [ -n "$LARGE_FILES" ]; then
    echo -e "${YELLOW}⚠️  FOUND LARGE FILES:${NC}"
    echo "$LARGE_FILES"
    echo ""
    echo "Verify these are not data files that should be in .gitignore"
else
    echo -e "${GREEN}✓ No large files found${NC}"
fi

echo ""

# Verify .gitignore has required patterns
echo "Checking .gitignore patterns..."
REQUIRED_PATTERNS=(
    "umls_data"
    "drg_source"
    ".env"
    "instance"
    "*.db"
    "*.sqlite"
    "quickumls_cache"
)

MISSING_PATTERNS=()
for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -q "$pattern" .gitignore 2>/dev/null; then
        MISSING_PATTERNS+=("$pattern")
    fi
done

if [ ${#MISSING_PATTERNS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  MISSING .gitignore PATTERNS:${NC}"
    printf '%s\n' "${MISSING_PATTERNS[@]}"
    echo ""
    echo "Add these patterns to .gitignore"
else
    echo -e "${GREEN}✓ All required patterns in .gitignore${NC}"
fi

echo ""
echo "=================================================="

# Final verdict
if [ $ISSUES_FOUND -eq 1 ]; then
    echo -e "${RED}❌ VERIFICATION FAILED!${NC}"
    echo ""
    echo "DO NOT COMMIT until issues are resolved!"
    echo ""
    echo "To remove files from git but keep locally:"
    echo "  git rm --cached <file>"
    echo ""
    echo "To add pattern to .gitignore:"
    echo "  echo 'pattern/' >> .gitignore"
    echo "  git add .gitignore"
    exit 1
else
    echo -e "${GREEN}✅ VERIFICATION PASSED!${NC}"
    echo ""
    echo "Safe to commit to GitHub!"
    echo ""
    echo "Remember:"
    echo "  - Users must obtain their own UMLS license"
    echo "  - Users must download UMLS data separately"
    echo "  - Users must download CMS DRG data if needed"
    echo "  - Document setup steps in SETUP_INSTRUCTIONS.md"
    exit 0
fi
