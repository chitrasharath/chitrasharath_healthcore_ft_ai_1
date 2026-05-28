# Development Commands

Use these direct commands from the repository root:

1. Type-check only (no output files):

```bash
npx -y -p typescript tsc --project /workspaces/chitrasharath_healthcore_ft_ai_1/apps/src/tsconfig.json --noEmit
```

2. Compile TypeScript to JavaScript for browser testing:

```bash
npx -y -p typescript tsc --project /workspaces/chitrasharath_healthcore_ft_ai_1/apps/src/tsconfig.json
```

3. Test functions from command line directly during development:

```bash
npx -y tsx /workspaces/chitrasharath_healthcore_ft_ai_1/apps/src/main.ts
```

4. Run lightweight unit tests:

```bash
npx -y tsx /workspaces/chitrasharath_healthcore_ft_ai_1/apps/src/tests/run-tests.ts
```

5. Serve the apps folder over HTTP (recommended for module loading):

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1/apps
npx -y http-server . -p 3001 -a 0.0.0.0
```

6. Open the manual test page in the browser:

```bash
$BROWSER http://localhost:3001/src/
```
