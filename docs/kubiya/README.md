# Kubiya Workflow SDK Documentation

This directory contains the official documentation for the Kubiya Workflow SDK.

## Documentation Structure

The documentation is organized into the following main sections:

```
docs/kubiya/
├── index.mdx                 # Main landing page
├── getting-started/         # Installation and quickstart guides
│   ├── welcome.mdx
│   ├── installation.mdx
│   └── quickstart.mdx
├── concepts/               # Core concepts and architecture
│   ├── platform-overview.mdx
│   ├── workflows.mdx
│   ├── runners.mdx
│   ├── integrations.mdx
│   ├── deterministic-workflows.mdx
│   ├── why-kubiya.mdx
│   └── agent-frameworks-comparison.mdx
├── workflows/              # Workflow documentation
│   ├── overview.mdx
│   ├── dsl-reference.mdx
│   ├── examples.mdx
│   ├── architecture.mdx
│   └── advanced.mdx
├── providers/              # Provider documentation
│   ├── overview.mdx
│   └── adk/               # Agent Development Kit
│       ├── getting-started.mdx
│       ├── agents.mdx
│       └── streaming.mdx
├── sdk/                   # SDK reference documentation
│   ├── overview.mdx
│   ├── api-reference.mdx
│   ├── examples.mdx
│   ├── contributing.mdx
│   └── changelog.mdx
├── api-reference/         # REST API documentation
│   └── compose.mdx
├── deployment/            # Deployment guides
│   └── helm-chart.mdx
├── tutorials/            # Step-by-step tutorials
│   └── ai-powered-automation.mdx
├── mcp/                  # MCP integration docs
│   └── overview.mdx
├── servers/              # Server documentation
│   └── overview.mdx
└── docs.json            # Navigation configuration

```

## Navigation Configuration

The navigation structure is defined in `docs.json`. All documentation is accessible through the sidebar navigation with the following main groups:

1. **Documentation** - Main landing page
2. **Getting Started** - New user onboarding
3. **Core Concepts** - Fundamental concepts
4. **Workflows** - Workflow creation and management
5. **AI & Automation** - ADK and AI features
6. **Platform Features** - Advanced features
7. **SDK Reference** - Complete SDK reference
8. **API Documentation** - REST API reference
9. **Integrations** - External integrations
10. **Deployment & Operations** - Production deployment
11. **Resources** - Changelogs and migration guides

## Adding New Documentation

When adding new documentation:

1. Create the `.mdx` file in the appropriate directory
2. Add frontmatter with title and description:
   ```yaml
   ---
   title: Your Page Title
   description: Brief description of the page content
   ---
   ```
3. Update `docs.json` to include the new page in the appropriate navigation group
4. Follow the existing content structure and style

## Style Guidelines

- Use clear, concise language
- Include code examples where relevant
- Use MDX components for rich content (Cards, Tabs, etc.)
- Add navigation aids (links to related content)
- Include practical examples and use cases
- Keep hierarchy flat where possible for easier navigation

## Building Documentation

The documentation is built using Mintlify. To preview locally:

```bash
npx mintlify dev
```

## Navigation Best Practices

Since all navigation is in the sidebar:
- Keep group names clear and descriptive
- Limit nesting to 2-3 levels maximum
- Use logical grouping of related content
- Ensure the most important pages are easily accessible
- Use the landing page (index.mdx) to provide quick access to key sections

## Contributing

Please ensure all documentation:
- Is accurate and up-to-date
- Follows the established structure
- Includes relevant examples
- Has been reviewed for clarity and correctness
- Maintains consistent navigation patterns

## 🚀 Local Development

```bash
# Run the documentation locally
mintlify dev

# Check for broken links
mintlify broken-links
```

The documentation will be available at `http://localhost:3000`.

## 🌐 Deploying to Mintlify Cloud

### Step 1: Push to GitHub

Make sure your `docs/kubiya` directory with the `docs.json` file is pushed to your GitHub repository.

### Step 2: Connect to Mintlify

1. Go to [dash.mintlify.com](https://dash.mintlify.com)
2. Sign in with your GitHub account
3. Click "New Project" or "Add Documentation"
4. Select your repository: `kubiya-ai/workflow-sdk`
5. Set the docs directory path: `docs/kubiya`
6. Choose your subdomain (e.g., `workflow-sdk-docs`)
7. Click "Deploy"

### Step 3: Custom Domain (Optional)

After deployment, you can add a custom domain:
1. Go to your project settings in Mintlify dashboard
2. Navigate to "Custom Domain"
3. Add your domain (e.g., `docs.kubiya.ai`)
4. Update your DNS records as instructed

## 🔧 Configuration

The documentation is configured via `docs.json`. Key settings:

- **Theme**: `willow` (Mintlify's modern theme)
- **Colors**: Kubiya brand colors
- **Navigation**: Organized by sections
- **Search**: Enabled with custom prompt
- **Social Links**: GitHub, Discord, LinkedIn, X

## 📚 Writing Documentation

### File Format
- Use `.mdx` files for documentation pages
- MDX allows you to use React components in Markdown

### Frontmatter
Each page should have frontmatter:
```yaml
---
title: "Page Title"
description: "Page description for SEO"
icon: "icon-name"
---
```

### Components
Mintlify provides many built-in components:
- `<Card>` - Feature cards
- `<CardGroup>` - Group of cards
- `<Tabs>` - Tabbed content
- `<Accordion>` - Collapsible sections
- `<CodeBlock>` - Syntax-highlighted code
- `<Note>`, `<Warning>`, `<Tip>` - Callout boxes

## 🔗 Useful Links

- [Mintlify Documentation](https://mintlify.com/docs)
- [Mintlify Dashboard](https://dash.mintlify.com)
- [Component Library](https://mintlify.com/docs/components)
- [Kubiya Platform](https://app.kubiya.ai) 