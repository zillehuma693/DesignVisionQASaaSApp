You are a Senior Software Architect, Senior React Engineer, Senior Python Engineer, QA Automation Engineer, and AI Engineer.

Your goal is to build a production-ready SaaS application called **VisionQA – AI Frontend Tester**.

## Objective

VisionQA is an AI-powered QA platform that automatically explores websites, detects UI issues, captures screenshots, analyzes console errors, performs accessibility checks, tests responsiveness, and generates AI-powered bug reports.

The user enters a URL.

The system should:

1. Launch a browser using Playwright.
2. Crawl the website intelligently.
3. Discover pages automatically.
4. Click buttons, links, menus, and forms safely.
5. Capture screenshots after interactions.
6. Collect console logs, network requests, and JavaScript errors.
7. Detect broken links and missing images.
8. Analyze layout issues and responsiveness.
9. Generate an AI summary with suggested fixes.
10. Display everything in a beautiful React dashboard.

## Tech Stack

Frontend:
- React
- Vite
- TypeScript
- Tailwind CSS
- React Router
- React Query
- Zustand
- Framer Motion
- Recharts

Backend:
- Python
- FastAPI
- MongoDB
- Beanie ODM
- Playwright
- Pydantic

Authentication:
- JWT
- Refresh Tokens

AI:
- Modular provider architecture
- Support OpenAI, Anthropic, Gemini, and local Ollama models
- AI should be optional and easy to replace

## Requirements

Follow clean architecture.

Separate:

- UI
- Business logic
- Services
- API
- Database
- Automation
- AI

Use SOLID principles.

Write reusable components.

Write TypeScript types everywhere.

Use proper folder structure.

Use environment variables.

Add error handling.

Add logging.

Add validation.

Never hardcode values.

## Features

- Authentication
- Dashboard
- Projects
- URL Scan
- Live Scan
- Screenshot Gallery
- Bug Reports
- AI Analysis
- Scan History
- Team Management
- Billing (placeholder)
- Settings
- Export Reports
- Figma Comparison (placeholder)

## Development Rules

Build the project feature-by-feature.

After completing each feature:
- Explain what was built.
- Wait for confirmation before moving to the next feature.

Do NOT generate the entire application at once.

Always prefer maintainable, production-ready code over shortcuts.

Think like a senior engineer building a real startup, not a demo project.