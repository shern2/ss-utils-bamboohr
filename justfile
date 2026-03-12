# ==========================================
# GLOBAL CONFIGURATION
# ==========================================

# UI Colors (ANSI escape codes)
RED    := `tput setaf 1 2>/dev/null || true`
GREEN  := `tput setaf 2 2>/dev/null || true`
YELLOW := `tput setaf 3 2>/dev/null || true`
CYAN   := `tput setaf 6 2>/dev/null || true`
GRAY   := `tput setaf 8 2>/dev/null || true`
RESET  := `tput sgr0 2>/dev/null || true`

# --- Environment ---
env := "dev"

# --- Recipes ---
# List all available commands
default:
    @just --list

# ==========================================
# 🐣 Setup
# ==========================================

# Setup the development environment
[group('Dependency Management / Setup')]
setup: (_check_dependency "uv")
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🐣 {{YELLOW}}Setting up development environment (env: {{env}})...{{RESET}}"
    just env={{env}} install

    if command -v pre-commit >/dev/null 2>&1; then
        echo "🔗 {{YELLOW}}Setting up pre-commit hooks...{{RESET}}"
        pre-commit install --install-hooks
    else
        echo "⚠️ {{YELLOW}}Warning: pre-commit not found, skipping hook installation{{RESET}}"
    fi


    echo ""
    echo "💡 {{CYAN}}Gentle reminder to update the relevant \`dev.env\`, \`uat.env\`, \`prod.env\` files. Template is available at \`.env.example\`{{RESET}}"
    echo "💡 {{CYAN}}Next steps:{{RESET}}"
    echo "  • next-step-item-1"
    echo "  • next-step-item-2"

# ==========================================
# 🐍 Python Utilities (Powered by uv)
# ==========================================

# Clean up cache files (.ruff_cache, .pytest_cache, __pycache__)
[group('Utils')]
clean:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🗑️ {{YELLOW}}Cleaning artifacts...{{RESET}}"
    rm -rf .ruff_cache .pytest_cache .mypy_cache .coverage htmlcov
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Copy the project to a temporary directory for analysis or sharing (e.g. Gemini Gem), excluding artifacts
[group('Utils')]
rsync-for-gemini-gem dest="/tmp/ss-utils-bamboohr/":
    @mkdir -p {{dest}}
    rsync -avz --progress \
        --exclude='/data/' \
        --exclude='/api_playground/' \
        --exclude='/output/' \
        --exclude='/dev/' \
        --exclude='/docs/' \
        --exclude='logs/' \
        --exclude='/tests/data/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.venv/' \
        --exclude='.env' \
        --exclude='*.env' \
        --exclude='.git/' \
        --exclude='.pytest_cache/' \
        --exclude='.ipynb_checkpoints/' \
        --exclude='/.circleci/' \
        ./ {{dest}}
    @echo "Project copied to {{dest}}"


# ==========================================
# 🚀 Publishing
# ==========================================

# Publish to PyPI (e.g., just publish v0.0.2)
[group('Publishing')]
publish version="":
    #!/usr/bin/env bash
    set -euo pipefail

    VERSION="{{version}}"
    if [ -z "$VERSION" ]; then
        VERSION=$(uv version | awk '{print $NF}')
    else
        echo "🏷️ {{YELLOW}}Setting version to $VERSION...{{RESET}}"
        uv version "$VERSION"
    fi

    echo "📦 {{YELLOW}}Publishing $VERSION to PyPI...{{RESET}}"
    rm -rf dist/*
    uv build
    
    # Load environment variables for UV_PUBLISH_TOKEN
    if [ -f .env ]; then
        source .env
    fi

    if [ -z "${UV_PUBLISH_TOKEN:-}" ]; then
        echo "❌ {{RED}}Error: UV_PUBLISH_TOKEN is not set.{{RESET}}"
        exit 1
    fi

    uv publish --token="$UV_PUBLISH_TOKEN"

    # Push Github tag and create release
    echo "🏷️ {{YELLOW}}Creating GitHub tag and release for $VERSION...{{RESET}}"
    # Check if tag already exists
    if git rev-parse "$VERSION" >/dev/null 2>&1; then
        echo "⚠️  {{YELLOW}}Tag $VERSION already exists, skipping tag creation.{{RESET}}"
    else
        git tag -a "$VERSION" -m "Release version $VERSION"
        git push origin "$VERSION"
    fi

    # Check if release already exists
    if gh release view "$VERSION" >/dev/null 2>&1; then
        echo "⚠️  {{YELLOW}}Release $VERSION already exists, skipping release creation.{{RESET}}"
    else
        gh release create "$VERSION" \
          --title "$VERSION" \
          --notes "Release version $VERSION"
    fi

# `just bump patch` (patch version bump) ; `just bump minor false` (minor version bump; skips git check) ; `just bump major`
[group('Publishing')]
bump bump="patch" verify="true":
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ "{{verify}}" == "true" ]]; then
        if [[ -n $(git status --porcelain) ]]; then
            echo "❌ {{RED}}Error: Working directory is not clean. Commit changes first.{{RESET}}"
            echo "   (Use 'just bump {{bump}} false' to bypass this check)"
            exit 1
        fi
    else
        echo "⚠️  {{YELLOW}}Warning: Skipping git status verification (--no-verify){{RESET}}"
    fi

    echo "📈 {{YELLOW}}Bumping {{bump}} version...{{RESET}}"
    uv version --bump {{bump}}

    NEW_VERSION=$(uv version | awk '{print $NF}')

    if [[ -z "$NEW_VERSION" ]]; then
         echo "❌ {{RED}}Error: Could not extract version. Output: $(uv version){{RESET}}"
         exit 1
    fi

    echo "🏷️ {{YELLOW}}Tagging v$NEW_VERSION...{{RESET}}"
    NEW_VERSION=$(uv version | awk '{print $NF}')
    PROJECT_NAME=$(grep -m 1 "^name = " pyproject.toml | cut -d '"' -f 2)

    git add pyproject.toml uv.lock
    git commit -m "chore(release): [$PROJECT_NAME] bump version to $NEW_VERSION"
    git tag "$PROJECT_NAME-v$NEW_VERSION"
    git push origin "$PROJECT_NAME-v$NEW_VERSION"
    git push

    just env={{env}} publish


# ==========================================
# 🔒 Internal Helpers
# ==========================================

[private]
_check_dependency bin:
    @command -v {{bin}} >/dev/null 2>&1 || (echo "❌ {{RED}}Error: {{bin}} is not installed{{RESET}}" && exit 1)
