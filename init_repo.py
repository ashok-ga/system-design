import os

# Directory structure
DIRS = [
    "docs/hld/diagrams",
    "docs/lld/class_diagrams",
    "docs/assets",
    ".github/ISSUE_TEMPLATE"
]

# File content templates
FILES = {
    "README.md": """# 📚 System Design Hub (HLD & LLD)
A collaborative, open-source knowledge base for **High-Level Design (HLD)** and **Low-Level Design (LLD)** patterns, examples, and best practices.
""",

    "CONTRIBUTING.md": """# Contributing Guide
Thanks for your interest in improving this repo!
See README for how to contribute.
""",

    "LICENSE": "MIT License",

    "docs/hld/overview.md": "# High-Level Design Overview\n\n*Start writing your system's HLD overview here.*\n",
    "docs/hld/architecture.md": "# Architecture\n\n*Add HLD architecture diagrams and explanation here.*\n",
    "docs/hld/diagrams/hld_architecture.png": "",  # placeholder
    "docs/lld/module1.md": "# Module 1 (LLD)\n\n*Start writing LLD for module 1 here.*\n",
    "docs/lld/module2.md": "# Module 2 (LLD)\n\n*Start writing LLD for module 2 here.*\n",
    "docs/lld/class_diagrams/module1_class.png": "",  # placeholder
    "docs/assets/logo.png": "",  # placeholder
    "docs/references.md": "# References\n\n*List references, resources, papers, links, etc.*\n",

    ".github/ISSUE_TEMPLATE/bug_report.md": """---
name: Bug report
about: Report a bug to help us improve
title: "[BUG] <describe bug>"
labels: bug
---
**Describe the bug**
A clear and concise description of what the bug is.
""",

    ".github/ISSUE_TEMPLATE/feature_request.md": """---
name: Feature request
about: Suggest an idea for this project
title: "[FEATURE] <describe feature>"
labels: enhancement
---
**Describe the feature**
A clear and concise description of what you want to happen.
""",

    ".github/PULL_REQUEST_TEMPLATE.md": """# Pull Request

**Description:**  
Describe your changes here.

**Checklist:**
- [ ] I have read the CONTRIBUTING guidelines.
- [ ] Docs/diagrams added if relevant.
- [ ] Tests added/updated if relevant.
"""
}

def safe_write(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

def main():
    # Make directories
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
    # Make files
    for path, content in FILES.items():
        safe_write(path, content)
    print("Project structure and starter files created!")

if __name__ == "__main__":
    main()

