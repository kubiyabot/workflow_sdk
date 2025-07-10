# 🚀 Deploy to Mintlify Cloud

Your documentation is now ready to be deployed to Mintlify Cloud!

## ✅ What's been done:

1. **Upgraded to Mintlify v2**: 
   - Converted `mint.json` to `docs.json` format
   - Removed old `mint.json` file
   - Updated navigation structure

2. **Cleaned up directory**:
   - Removed Vercel-related files
   - Removed unnecessary Node.js files
   - Kept only essential documentation files

3. **Documentation structure ready**:
   ```
   docs/kubiya/
   ├── docs.json              # ✅ Mintlify v2 config
   ├── assets/               # Static files
   ├── getting-started/      # Welcome, Installation, Quickstart
   ├── providers/            # AI Provider docs
   ├── workflows/            # Workflow documentation
   ├── servers/              # Server & API docs
   ├── updates.mdx           # What's new
   ├── changelog.mdx         # Version history
   └── migration-guide.mdx   # Migration guide
   ```

## 🌐 Deploy to Mintlify Cloud:

### Step 1: Commit and Push
```bash
cd /Users/shaked/projects/workflow_sdk
git add docs/kubiya/
git commit -m "feat: prepare docs for Mintlify cloud deployment"
git push origin main
```

### Step 2: Connect to Mintlify
1. Go to **[dash.mintlify.com](https://dash.mintlify.com)**
2. Click **"New Project"** or **"Add Documentation"**
3. **Connect your GitHub** account if not already connected
4. **Select repository**: `kubiya-ai/workflow-sdk` (or your repo name)
5. **Set docs path**: `docs/kubiya`
6. **Choose subdomain**: `workflow-sdk-docs` (or your preference)
   - Your docs will be at: `https://workflow-sdk-docs.mintlify.app`
7. Click **"Deploy"**

### Step 3: Verify Deployment
After deployment (usually takes 2-3 minutes):
- Visit your documentation at the Mintlify subdomain
- Check that all pages load correctly
- Test the search functionality

### Step 4: Custom Domain (Optional)
To use a custom domain like `docs.kubiya.ai`:
1. In Mintlify dashboard, go to **Settings > Custom Domain**
2. Add your domain
3. Add the provided CNAME record to your DNS:
   ```
   Type: CNAME
   Name: docs (or your subdomain)
   Value: [your-subdomain].mintlify.app
   ```

## 🔧 Local Development

To continue developing locally:
```bash
cd docs/kubiya
mintlify dev
```

Then open http://localhost:3000

## 📝 Important Notes:

- **No build step needed**: Mintlify Cloud handles all building
- **Auto-deploy**: Every push to your main branch auto-deploys
- **Preview deployments**: PRs get preview URLs automatically
- **Analytics**: Available in Mintlify dashboard
- **Search**: Automatically indexed and searchable
