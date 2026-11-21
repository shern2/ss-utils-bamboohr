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
# Policy: patch by default; minor for features; major only for breaks.
# A release is a tag on this branch — there is no release branch. See RELEASING.md.

# Install the just-built wheel in a throwaway venv; assert metadata + import.
[private]
_verify_wheel version:
    #!/usr/bin/env bash
    set -euo pipefail
    PROJECT_NAME=$(grep -m 1 '^name = ' pyproject.toml | cut -d '"' -f 2)
    MODULE=${PROJECT_NAME//-/_}
    DIST=$(ls dist/*.whl 2>/dev/null | head -1)
    if [ -z "$DIST" ]; then
        echo "❌ {{RED}}Error: no wheel in dist/. Run 'uv build' first.{{RESET}}"
        exit 1
    fi
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    uv venv "$TMP/venv" >/dev/null
    uv pip install --python "$TMP/venv/bin/python" "$DIST" >/dev/null
    GOT=$("$TMP/venv/bin/python" -c 'import importlib.metadata as m, sys; print(m.version(sys.argv[1]))' "$PROJECT_NAME")
    if [[ "$GOT" != "{{version}}" ]]; then
        echo "❌ {{RED}}Error: wheel reports $GOT, expected {{version}}{{RESET}}"
        exit 1
    fi
    "$TMP/venv/bin/python" -c "import ${MODULE}" >/dev/null
    echo "✅ {{GREEN}}wheel ok: ${PROJECT_NAME}==${GOT} (${MODULE} imports){{RESET}}"

# Verify the published artifact installs from the registry and reports its version.
# Usage: just verify-release [version]
[group('Publishing')]
verify-release version="":
    #!/usr/bin/env bash
    set -euo pipefail
    PROJECT_NAME=$(grep -m 1 '^name = ' pyproject.toml | cut -d '"' -f 2)
    MODULE=${PROJECT_NAME//-/_}
    VERSION="{{version}}"
    if [ -z "$VERSION" ]; then
        VERSION=$(uv version --short)
    fi
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    uv venv "$TMP/venv" >/dev/null
    uv pip install --python "$TMP/venv/bin/python" "${PROJECT_NAME}==${VERSION}" >/dev/null
    GOT=$("$TMP/venv/bin/python" -c 'import importlib.metadata as m, sys; print(m.version(sys.argv[1]))' "$PROJECT_NAME")
    if [[ "$GOT" != "$VERSION" ]]; then
        echo "❌ {{RED}}Error: registry serves $GOT, expected $VERSION{{RESET}}"
        exit 1
    fi
    "$TMP/venv/bin/python" -c "import ${MODULE}" >/dev/null
    echo "✅ {{GREEN}}registry ok: ${PROJECT_NAME}==${GOT}{{RESET}}"

# Publish the existing dist/ artifact (builds only if dist/ is empty).
# Usage: just publish [version]
[group('Publishing')]
publish version="":
    #!/usr/bin/env bash
    set -euo pipefail

    VERSION="{{version}}"
    if [ -n "$VERSION" ]; then
        echo "🏷️ {{YELLOW}}Setting version to $VERSION...{{RESET}}"
        uv version "$VERSION"
    fi
    VERSION=$(uv version --short)

    echo "📦 {{YELLOW}}Publishing $VERSION...{{RESET}}"
    if ! ls dist/*.whl >/dev/null 2>&1; then
        uv build
    fi
    if [ -f .env ]; then source .env; fi
    if [ -z "${UV_PUBLISH_TOKEN:-}" ]; then
        echo "❌ {{RED}}Error: UV_PUBLISH_TOKEN is not set. Add it to .env or export it.{{RESET}}"
        exit 1
    fi
    uv publish --token="$UV_PUBLISH_TOKEN"

# Release: build once, verify the wheel, write the record, publish, verify the
# registry, then tag. Usage: just bump [patch|minor|major] [verify=true]
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
        echo "⚠️  {{YELLOW}}Warning: Skipping git status check{{RESET}}"
    fi

    PROJECT_NAME=$(grep -m 1 '^name = ' pyproject.toml | cut -d '"' -f 2)
    TAG_PREFIX="${PROJECT_NAME}-v"

    CUR=$(uv version --short)
    if [[ "$CUR" == *rc* || "$CUR" == *a* || "$CUR" == *b* ]]; then
        echo "❌ {{RED}}Error: $CUR is a prerelease. Finalise it first:{{RESET}}"
        echo "   uv version ${CUR%%rc*}; then: just publish && just verify-release"
        exit 1
    fi

    echo "🧪 {{YELLOW}}Running tests before release...{{RESET}}"
    just env={{env}} test-unit

    echo "📈 {{YELLOW}}Bumping {{bump}} version...{{RESET}}"
    uv version --bump {{bump}}
    NEW=$(uv version --short)

    echo "🏗️ {{YELLOW}}Building and verifying $NEW...{{RESET}}"
    rm -rf dist
    uv build
    just _verify_wheel "$NEW"

    echo "📝 {{YELLOW}}Writing releases/v$NEW.md...{{RESET}}"
    mkdir -p releases
    PREV=$(git describe --tags --abbrev=0 --match "${TAG_PREFIX}*" 2>/dev/null || true)
    sed -e "s/__VERSION__/$NEW/g" -e "s/__DATE__/$(date +%F)/g" releases/_template.md > "releases/v$NEW.md"
    echo "" >> "releases/v$NEW.md"
    echo "## Shipped" >> "releases/v$NEW.md"
    echo "" >> "releases/v$NEW.md"
    git log --no-merges --pretty='- %s (%h)' ${PREV:+$PREV..HEAD} >> "releases/v$NEW.md"
    echo "" >> "releases/v$NEW.md"
    echo "_Local wheel verification passed before publish._" >> "releases/v$NEW.md"

    git add pyproject.toml uv.lock releases/
    git commit -m "chore(release): [$PROJECT_NAME] bump version to $NEW"

    echo "📦 {{YELLOW}}Publishing $NEW...{{RESET}}"
    just env={{env}} publish "$NEW"

    echo "🔎 {{YELLOW}}Verifying the published artifact...{{RESET}}"
    just env={{env}} verify-release "$NEW"
    sed -i '' "s|^- registry: .*|- registry: \`${PROJECT_NAME}==${NEW}\` installs and reports ${NEW}|" "releases/v$NEW.md" 2>/dev/null || \
        sed -i "s|^- registry: .*|- registry: \`${PROJECT_NAME}==${NEW}\` installs and reports ${NEW}|" "releases/v$NEW.md"
    git add "releases/v$NEW.md"
    git commit --amend --no-edit

    echo "🏷️ {{YELLOW}}Tagging $TAG_PREFIX$NEW...{{RESET}}"
    git tag "$TAG_PREFIX$NEW"
    git push origin "$TAG_PREFIX$NEW"
    git push

    echo ""
    echo "✅ {{GREEN}}Released $PROJECT_NAME $NEW{{RESET}}"
    echo "   Retro: add up to 3 friction items to releases/v$NEW.md,"
    echo "   then edit RELEASING.md — not product code. See RELEASING.md."
    if command -v gh >/dev/null 2>&1; then
        gh release create "$TAG_PREFIX$NEW" --title "$NEW" --notes "Release $NEW" >/dev/null 2>&1 || true
    fi

# ==========================================
# 🔒 Internal Helpers
# ==========================================

[private]
_check_dependency bin:
    @command -v {{bin}} >/dev/null 2>&1 || (echo "❌ {{RED}}Error: {{bin}} is not installed{{RESET}}" && exit 1)
