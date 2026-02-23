# Contributing Guide

Welcome! To keep our commit history clean and easy to read, please follow the rules below when submitting changes.

---

## 📬 Pull Request Workflow

1. Fork the repository and create your branch from `main`
2. Make your changes and commit using the format below
3. Open a Pull Request — your changes will be reviewed and approved

---

## ✅ Commit Rules

Use **clear and concise** commit messages that describe *what* changed and *why*.

### Format

```
type: short description
```

> Keep the short description under 72 characters.  
> Use the imperative mood: *"add feature"*, not *"added feature"* or *"adds feature"*.

---

### Commit Types

| Type | When to Use |
|------|-------------|
| `feat` | Introducing a new feature |
| `fix` | Fixing a bug |
| `refactor` | Restructuring code without changing behavior |
| `docs` | Documentation changes only |
| `style` | Formatting, whitespace, missing semicolons (no logic changes) |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks (dependencies, build scripts, etc.) |

---

### Examples

```bash
feat: add user authentication endpoint
fix: resolve memory leak in data parser
refactor: simplify payment processing logic
docs: update installation guide
style: reformat code to follow ESLint rules
test: add unit tests for login validation
chore: upgrade dependencies to latest versions
```

---

## 🔀 Submitting a Pull Request

- **Branch naming:** `type/short-description` (e.g., `feat/user-auth`, `fix/memory-leak`)
- **PR title:** Follow the same commit format above
- **PR description:** Briefly explain what you changed and why
- Link any related issues using `Closes #issue-number`

---

## 📝 Notes

- One logical change per commit — avoid bundling unrelated changes
- Avoid committing directly to `main`
- If unsure about a type, choose the one that best fits the *primary* intent of the change
