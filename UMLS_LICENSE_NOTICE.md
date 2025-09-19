# UMLS LICENSE COMPLIANCE NOTICE

## ⚠️ IMPORTANT: UMLS Data Licensing

### License Requirement
The UMLS Metathesaurus is **licensed content** from the U.S. National Library of Medicine (NLM). 

**YOU MUST OBTAIN YOUR OWN UMLS LICENSE** to use this application with UMLS data.

### How to Obtain a UMLS License

1. **Visit**: https://uts.nlm.nih.gov/license.html
2. **Create Account**: Register with the UTS (UMLS Terminology Services)
3. **Accept License**: Review and accept the UMLS License Agreement
4. **Download Data**: Once approved, download UMLS files from UTS

### License Restrictions

✅ **Permitted Uses:**
- Research and development
- Clinical decision support
- Educational purposes
- Non-commercial applications

❌ **Prohibited:**
- Redistribution of UMLS data
- Commercial use without proper licensing
- Sharing login credentials
- Including UMLS data in public repositories

### Data Security Requirements

- **No Public Sharing**: Never commit UMLS data to version control
- **Access Control**: Limit access to licensed users only
- **Secure Storage**: Store UMLS data in protected cloud storage
- **Audit Trail**: Maintain logs of data access

### This Repository Compliance

✅ **Repository is Clean**: No UMLS data is stored in this Git repository
✅ **Access Controls**: Google OAuth restricts access to authorized users
✅ **Cloud Storage**: UMLS data is stored separately in Google Cloud Storage
✅ **Download Only**: Application downloads UMLS data at runtime from authorized storage

### User Authorization

The application uses Google OAuth to ensure only authorized users can access UMLS functionality:

1. **Authentication Required**: All users must sign in with Google
2. **Authorized Email List**: Limit access to specific Gmail addresses
3. **Session Management**: Secure session handling
4. **Audit Logging**: Track all data access

### Setting Up Authorized Users

Add authorized user emails to the application configuration:

```python
# In config.py or environment variables
AUTHORIZED_USERS = [
    "researcher1@university.edu",
    "doctor@hospital.org", 
    "student@medschool.edu"
]
```

### Legal Disclaimer

By using this software, you acknowledge that:
- You are responsible for obtaining proper UMLS licensing
- You will comply with all NLM license terms
- You will not redistribute UMLS data
- You understand the legal requirements for UMLS usage

**For questions about UMLS licensing, contact the National Library of Medicine directly.**

### Resources

- **UMLS Home**: https://www.nlm.nih.gov/research/umls/
- **UTS Registration**: https://uts.nlm.nih.gov/license.html
- **License Terms**: https://uts.nlm.nih.gov/license.html
- **Support**: https://support.nlm.nih.gov/