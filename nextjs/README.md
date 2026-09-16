# Digital Wellbeing landing page — Next.js

A Next.js App Router port of the existing landing page, preserving its content, CSS, responsive layouts, links, native FAQ accordions, and Overview screenshot. The original static page remains at `../index.html`. The Python desktop application is separate.

## Run locally

Use Node.js 20.9 or newer and run from this folder:

```powershell
npx pnpm@11.19.0 install --frozen-lockfile
npx pnpm@11.19.0 dev
```

Open http://localhost:3000. Stop the server with Ctrl+C.

## Build and host

```powershell
npx pnpm@11.19.0 build
```

The static site is generated in `out/`. Upload the contents to a static host at the domain root. For hosting platforms that build Next.js, set the project root to `nextjs`, the build command to `pnpm build`, and the output folder to `out`.

This project uses [Next.js static export](https://nextjs.org/docs/app/guides/static-exports), so it needs no application server after building. `next start` is not used with this configuration. Subdirectory hosting (for example a GitHub project Pages URL) needs a matching Next.js base path and asset URLs before deployment.

## What to edit

- `app/page.jsx`: page sections and content.
- `app/globals.css`: original stylesheet, copied without visual changes.
- `app/install-commands.jsx`: interactive copy button, including clipboard failure feedback.
- `app/layout.jsx`: page title, description, language, and theme color.
- `public/landing_page/pic/overview-mock.png`: the current mock Overview screenshot.

CSS and the screenshot are copied into this standalone project; future edits to the original static page do not automatically update this version. Page copy is intentionally preserved, including the existing development limitations FAQ.

## Verify it yourself

1. Compare the original landing page with localhost:3000 at desktop and mobile widths.
2. Use Get started and Take a look; confirm they scroll to the correct sections.
3. Expand each FAQ and check the footer links.
4. Use Copy commands and paste into a text editor to verify the PowerShell paths and line breaks. Clipboard access requires HTTPS or localhost; manual selection remains available.
5. Check that the Overview screenshot loads and shows the sample-data caption.
6. Run the production build and confirm `out/index.html` is generated.
