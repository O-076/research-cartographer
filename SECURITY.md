# 🔐 SECURITY.md — Security Guidelines

> **Read this before every `git push`.** This is a public repository.
> Violations result in disqualification from the hackathon per Microsoft's Disclaimer.

---

## The Single Most Important Rule

**Never commit `.env`.** It is gitignored. It contains all real credentials. Use `.env.example` for the template.

---

## What Is NEVER Allowed in This Repo

Per the [Microsoft Agents League Disclaimer](https://aka.ms/AgentsLeague_Disclaimer):

| Category | Examples | Risk |
|----------|---------|------|
| **Credentials & Secrets** | API keys, tokens, passwords, connection strings | Critical — immediate breach |
| **Personal Data (PII)** | Names, emails, phone numbers, addresses, IDs | High — compliance violation |
| **Customer Data** | Any data belonging to real users or organizations | High |
| **Proprietary Code** | Code owned by an employer, client, or third party | High |
| **Pre-release Info** | Anything under NDA | Medium |
| **Internal Docs** | Company-internal documentation | Medium |

---

## Pre-Commit Checklist

Run this mentally (or literally) before every `git push`:

```bash
# 1. Check what you're about to commit
git diff --cached

# 2. Check for common secret patterns
git diff --cached | grep -E "(key|secret|password|token|api_key)" -i

# 3. Verify .env is NOT staged
git status | grep ".env$"
# If it appears — unstage it immediately:
git reset HEAD .env
```

---

## If You Accidentally Commit a Secret

Do NOT just delete the secret in a new commit. Git history preserves it.

```bash
# Remove the file from all history (nuclear option — coordinate with team)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Then force push (requires repo admin access)
git push origin --force --all
```

Then **immediately rotate the exposed credential** (regenerate the API key, change the password).

---

## Correct Way to Handle Credentials

**✅ DO THIS:**
```python
# In code
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("AZURE_OPENAI_KEY")
```

```bash
# In .env (gitignored — never committed)
AZURE_OPENAI_KEY=your-real-key-here
```

```bash
# In .env.example (committed — template only)
AZURE_OPENAI_KEY=
```

**❌ NEVER DO THIS:**
```python
api_key = "sk-abc123-real-key"  # Hardcoded
api_key = "sk-abc123"           # Even in comments
```

---

## GitHub Secret Protection

GitHub automatically scans for 300+ token types and will **block your push** if it detects a secret. If you get a push protection error:

1. Do NOT bypass it
2. Remove the secret from your code
3. Add the variable to `.env` instead
4. Commit the fix and push again

---

## What IS Safe to Commit

- Source code with no hardcoded values
- `.env.example` with empty/placeholder values
- Configuration files using environment variable references
- Documentation (as long as it contains no real values)
- Test fixtures with synthetic/fake data
- The `.gitignore` file itself

---

## Reporting Security Issues

If you find a security issue in this project, report it via:
[GitHub Security Advisories](https://github.com/microsoft/agentsleague/security)

Do NOT open a public issue for security vulnerabilities.

---

## GitHub Account Security

Per Microsoft's guidelines for this hackathon:

- ✅ Enable **two-factor authentication (2FA)** on your GitHub account
- ✅ Use **Personal Access Tokens** instead of passwords for git operations
- ✅ Revoke tokens when no longer needed
- ✅ Keep your recovery codes stored securely offline
