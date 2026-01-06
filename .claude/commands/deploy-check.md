# Pre-Deployment Verification

Verify the application is ready for deployment by running all checks.

## Steps

### 1. Backend Checks

```bash
cd backend

# Check Python environment
.venv/Scripts/python.exe --version

# Verify dependencies installed
.venv/Scripts/pip.exe check

# Run tests (if available)
.venv/Scripts/python.exe -m pytest -v

# Verify imports work
.venv/Scripts/python.exe -c "from app.main import app; print('✓ Backend imports OK')"

# Check for security issues in dependencies
.venv/Scripts/pip.exe audit 2>/dev/null || echo "pip-audit not installed, skipping"
```

### 2. Frontend Checks

```bash
cd frontend

# Check Node version
node --version

# Verify dependencies
npm ls --depth=0

# Run linter
npm run lint 2>/dev/null || echo "No lint script configured"

# Build for production
npm run build

# Check bundle size
du -sh dist/
```

### 3. Environment Checks

```bash
# Check .env files exist
[ -f backend/.env ] && echo "✓ backend/.env exists" || echo "✗ backend/.env missing"
[ -f frontend/.env ] && echo "✓ frontend/.env exists" || echo "✗ frontend/.env missing"

# Verify no secrets in git
git diff --cached --name-only | grep -E "\.env$|secret|key|password" && echo "⚠ Potential secrets staged" || echo "✓ No secrets in staged files"
```

### 4. Git Status

```bash
# Check for uncommitted changes
git status --short

# Verify remote is set
git remote -v
```

## Checklist

- [ ] Backend imports successfully
- [ ] Backend tests pass (if any)
- [ ] Frontend builds without errors
- [ ] No TypeScript errors
- [ ] Bundle size reasonable (<500KB gzipped)
- [ ] Environment files in place
- [ ] No secrets in committed code
- [ ] Git remote configured

## Report Format

```
=== Deployment Readiness Report ===

Backend:  ✓ Ready / ✗ Issues found
Frontend: ✓ Ready / ✗ Issues found
Env:      ✓ Configured / ✗ Missing files
Git:      ✓ Clean / ⚠ Uncommitted changes

Blockers:
- [List any blocking issues]

Warnings:
- [List any non-blocking warnings]
```
