# Contributing

Thanks for your interest in contributing.

## Development

1. Fork the repository
2. Create a branch from `main`
3. Make focused changes
4. Add or update tests
5. Open a pull request

## Standards

- Keep PRs small and reviewable
- Include clear commit messages
- Document behavior changes

## Documentation scope

Keep `docs/` focused on public user/operator documentation, release notes, site
configuration, and supporting assets. Internal plans, audit/decision memos,
porting manifests, and release-process rules belong in access-controlled private
storage, not this repository (including dot-folders).

GitHub does not support admin-only files within a public repository. `.gitignore`
helps prevent accidental additions but is not access control, and removing a file
does not remove earlier copies from Git history or existing clones.

## Pull Request Checklist

- [ ] Tests pass locally
- [ ] Lint checks pass
- [ ] Docs updated when needed
- [ ] No secrets or internal infrastructure details added
