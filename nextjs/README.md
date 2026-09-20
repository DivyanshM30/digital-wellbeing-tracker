# Digital Wellbeing landing page — Next.js

A Next.js App Router port of the existing landing page, preserving its content, CSS, responsive layouts, links, native FAQ accordions, and Overview screenshot. The original static page remains at `../index.html`. The Python desktop application is separate.

## Run locally

Use Node.js 20.9 or newer and run from this folder:

```powershell
npx pnpm@11.19.0 install --frozen-lockfile
npx pnpm@11.19.0 dev
```

Open http://localhost:3000. Stop the server with Ctrl+C.

## Deploy to Vercel

The default build uses Vercel's native Next.js integration:

- Root Directory: `nextjs`
- Framework Preset: `Next.js`
- Install Command: `pnpm install --frozen-lockfile`
- Build Command: `pnpm build`
- Output Directory: leave the override disabled (framework default)
- Production Branch: `main`
- Use a supported Node.js version that satisfies `package.json`.

Do not set `NEXT_STATIC_EXPORT` on Vercel. Push the updated commit, then deploy that commit. Configuration changes do not change an existing deployment. If necessary, redeploy with the build cache disabled.

Verify the deployment is Ready, its source commit includes these changes, and the build log lists the `/` route. Open that deployment's generated URL using Visit. If it works but a custom domain still returns 404, check the domain's project and production deployment assignment. If the generated URL also fails, capture its exact error code and build logs. See [Vercel's 404 troubleshooting guide](https://vercel.com/kb/guide/how-to-debug-404-errors).

To test the production build locally:

```powershell
npx pnpm@11.19.0 build
npx pnpm@11.19.0 start
```

Open http://localhost:3000 and check the page and screenshot.

## Export for another static host

```powershell
npx pnpm@11.19.0 build:static
```

This explicit export generates `out/` using [Next.js static export](https://nextjs.org/docs/app/guides/static-exports). Upload its contents to a static host at the domain root. `next start` cannot serve this export; run the normal build again before using `start`. Subdirectory hosting needs a matching Next.js base path and asset URLs before deployment.

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
6. Run `build` and `start` to check the production page. For static hosting, run `build:static` and confirm `out/index.html` is generated.
