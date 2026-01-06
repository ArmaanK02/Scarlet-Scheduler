# Security Notice

## ⚠️ IMPORTANT: Revoke Exposed API Token

If a Hugging Face API token was previously committed to the repository, you must:

1. **Immediately revoke the token** at: https://huggingface.co/settings/tokens
2. **Generate a new token** if needed
3. **Never commit `.env` files** to version control

## Environment Variables Setup

### Step 1: Create `.env` file
Copy the template below and create a `.env` file in the project root:

```env
# Hugging Face API Token (optional - for LLM features)
# Get your token from: https://huggingface.co/settings/tokens
HF_TOKEN=your_huggingface_token_here

# Auto-refresh course data when stale
AUTO_REFRESH_DATA=false

# Days before data is considered stale (default: 30)
DATA_STALE_DAYS=30

# Debug LLM usage (set to "true" to see when LLM is called)
DEBUG_LLM=false
```

### Step 2: Verify `.gitignore`
The `.gitignore` file has been created to prevent committing:
- `.env`
- `.env.local`
- `.env.*.local`
- `.env.txt`

### Step 3: Remove from Git History (if already committed)
If `.env` was already committed, remove it from history:

```bash
git rm --cached .env
git commit -m "Remove .env from version control"
```

Then add `.env` to `.gitignore` (already done) and never commit it again.

## Best Practices

1. ✅ Always use `.env.example` as a template
2. ✅ Never commit real credentials
3. ✅ Use different tokens for development/production
4. ✅ Rotate tokens regularly
5. ✅ Review `.gitignore` before committing

