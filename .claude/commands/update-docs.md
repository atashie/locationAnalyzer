# Update Project Documentation

Update project documentation files after completing a milestone or major changes.

## Files to Update

### 1. project_status.md

Update current progress:
- Move completed items from "In Progress" to "Completed Tasks"
- Add new items to "Next Steps"
- Update progress percentages
- Update "Last Updated" date

### 2. changelog.md

Add entry for changes:
```markdown
## [Unreleased]

### Added
- [New features]

### Changed
- [Modified features]

### Fixed
- [Bug fixes]
```

When releasing a version, move [Unreleased] items to a versioned section.

### 3. architecture.md

Update if there are:
- New components or services
- Changed data flow
- New API endpoints
- Infrastructure changes

### 4. CLAUDE.md

Update if there are:
- New key files to reference
- Changed commands
- New common tasks
- Updated troubleshooting tips

## Checklist

- [ ] project_status.md - Progress updated
- [ ] changelog.md - Changes documented
- [ ] architecture.md - Design current (if changed)
- [ ] CLAUDE.md - Context accurate (if changed)
- [ ] All dates updated

## When to Update

- After completing a setup phase
- After adding new features
- After fixing significant bugs
- Before creating a release
- After architectural changes
