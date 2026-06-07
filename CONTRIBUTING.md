# Contributing to website-capture

Thank you for your interest in contributing to website-capture! We welcome contributions from the community, including bug reports, feature requests, documentation improvements, and code submissions.

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project, you agree to abide by its terms.

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check the issue tracker to avoid duplicates. When reporting a bug, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs. **actual behavior**
- **Environment details** (OS, Python version, Docker version)
- **Relevant logs or error messages**
- **Screenshots** if applicable

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** - explain why this enhancement would be useful
- **Possible implementation** (optional but helpful)
- **Alternative solutions** you've considered

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Install development dependencies**:
   ```bash
   cd backend && pip install -e .
   cd ../cli && pip install -e .
   cd ../frontend && npm install
   ```
3. **Make your changes** with clear commit messages
4. **Test your changes**:
   - For backend: Run `pytest tests/`
   - For frontend: Run `npm test`
   - For CLI: Test manually with `webcapture --help`
5. **Update documentation** if you're adding/changing features
6. **Keep commits clean** - one feature/fix per commit
7. **Push to your fork** and submit a pull request

### Development Workflow

```bash
# Clone the repo
git clone https://github.com/yourusername/website-capture.git
cd website-capture

# For backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/

# For CLI development
cd ../cli
pip install -e .
webcapture --help

# For frontend development
cd ../frontend
npm install
npm run dev
```

### Commit Message Guidelines

- Use clear, descriptive messages
- Start with a verb: "Add", "Fix", "Update", "Remove", etc.
- Keep the first line under 50 characters
- Add more detail in the body if needed

Examples:
- `Add sitemap-based URL discovery`
- `Fix cookie banner dismissal on mobile viewports`
- `Update CLI progress bar styling`

## License

By contributing to website-capture, you agree that your contributions will be licensed under the Hippocratic License 3.0. This means:

- Your code can be used for non-commercial purposes
- Derivative works must maintain the same non-commercial restriction
- Commercial use requires explicit permission

For details, see the LICENSE file.

## Questions?

- Check the documentation in `docs/`
- Open an issue with your question
- Review existing issues and PRs for context

Thank you for contributing! 🙏
