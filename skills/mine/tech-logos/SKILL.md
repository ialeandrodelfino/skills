---
name: tech-logos
description: Reuse or add official tech brand logos through the repository's existing asset inventory. Use when user needs logos for tech companies (Clerk, Vercel, GitHub, etc.), AI providers (OpenAI, Anthropic, Claude), social platforms, or any brand assets. Triggers on "logo", "brand", "icon for [company]", "add [company] logo", placeholder logo detection, or when building landing pages, auth UIs, or integrations showcases. Don't use for custom in-house logos, generic icon libraries (Lucide, Heroicons), or marketing image assets.
metadata:
  author: Pedro Nauck
  github: https://github.com/pedronauck
  repository: https://github.com/pedronauck/skills
---
# Tech Logos

Reuse the repository's existing official brand assets before fetching or installing anything. Inspect the logo index and the component's real props; do not assume every logo supports `variant` or `mode`.

1. Find the logo in the existing inventory. In Compozy, check `packages/ui/src/logos/index.ts` and import from `@compozy/ui/logos`.
2. When it is missing, use an authoritative brand asset and the project's established SVG/component pattern. Preserve provenance, brand geometry, accessible labeling, and appropriate light/dark behavior.
3. Add only the requested asset to the shared logo directory and public export. Extend the relevant story when it demonstrates a new supported state; no all-brand bundles or duplicated app-local logos.
4. Use an external registry such as Elements only when the task calls for that source or the project already adopts it. Inspect the proposed files and use the repository package manager. A missing logo does not require opening a third-party issue.

In other repositories, locate the equivalent inventory and package path instead of creating a Compozy-shaped folder tree.
