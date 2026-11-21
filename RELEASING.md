# Releasing

One page. A release is a **tag on this branch**; there is no release branch and no
backport train. Consumers install tags; `main`/`dev` is development.

## Policy

- **Patch by default.** Fixes ship as `patch`. Features ship as `minor`. `major`
  only when a consumer must change code.
- **Forward-only.** Never move or reuse a tag, never republish a version. A bad
  release is fixed by the next patch.
- **One tag family:** `<dist-name>-v<version>`. Every recipe derives it the same way.
- **A red test is a blocker or a flake, decided before you touch it.** Rerun a flake
  at most twice on the same commit; never re-cut a version only to clear a flake; a
  cancelled CI run still blocks.

## Before you start

1. Working tree clean; you are on the branch consumers track.
2. `just test-unit` green locally.
3. Decide the bump: `patch` (fix), `minor` (feature), `major` (break).

## Release

```bash
just bump patch      # patch | minor | major
```

The recipe, in order: clean-tree check → refuses a prerelease version → tests →
version bump → **one** build → wheel installs in a throwaway venv and reports the new
version → writes `releases/v<version>.md` (shipped commit list) → commits → publishes
the verified artifact → installs it back **from the registry** → amends the record with
the registry result → tags → pushes.

If publishing fails after the commit, fix the cause and run `just publish` then
`just verify-release`; only then tag (`git tag <dist>-v<version>`). Do not run `just bump`
again — it would bump past the version you already built.

## Prerelease (only when you actually need one)

No recipe: it is one command plus the normal publish path.

```bash
uv version 0.4.0rc1      # exact assignment; `uv version --bump rc` refuses from a final version
just publish && just verify-release
uv version 0.4.0         # finalise, then publish normally
```

`just bump` refuses to run from a prerelease so a stray `rc` cannot be tagged as stable.

## Verify by hand (any time)

```bash
just verify-release            # current version
just verify-release 0.4.2      # a specific one
```

This installs the **published** artifact in a clean venv and asserts the version and
an import. The local-wheel check inside `just bump` proves the artifact before upload;
this proves the registry round-trip after it.

## After the release (10 minutes, not 30 findings)

1. Fill the three retro questions in `releases/v<version>.md`.
2. If a fix is needed, edit **this file** — a checklist line, not product code.
3. Do not let the retro grow a second backlog. Anything bigger goes in the repo's
   normal issue list.

## Record

`releases/v<version>.md` is committed with the release, so the tag always carries it:
what shipped, what was ported and how, and what was actually verified. `releases/_template.md`
is the shape.
