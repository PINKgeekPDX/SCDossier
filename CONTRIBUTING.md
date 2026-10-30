# Contributing to SCDossier

Thanks for your interest in contributing to SCDossier. We welcome bug reports, documentation improvements, feature ideas, and code contributions.

This project is open source under the MIT License. By submitting contributions to this repository, you agree that your contribution will be licensed under the same MIT License terms as the project.

## Project goals

SCDossier is a Star Citizen companion application focused on:

- fast player and organization lookups
- local archival and export workflows
- OCR-assisted data capture from the game client
- an offline-first, lightweight experience for players

Contributions should stay aligned with those goals and avoid introducing unnecessary complexity or behavior that conflicts with the project’s privacy-first and local-first design.

## Before you contribute

- Read the project README and current issue tracker first.
- Check whether your idea or bug is already tracked.
- Keep changes focused and explain the reason for the change in your pull request.
- Prefer small, well-scoped pull requests over broad rewrites.

## Ways to contribute

### Bug reports

Please open an issue with:

- a clear description of the problem
- steps to reproduce it
- expected behavior vs. actual behavior
- relevant environment details (Windows/Linux, app version, Python version, logs if available)

### Feature requests

Open an issue describing the problem you want to solve and why it matters. If possible, include examples, mockups, or a short user story.

### Code contributions

1. Fork the repository.
2. Create a feature branch from `main`.
3. Make your changes with clear, focused commits.
4. Run the relevant tests or validation steps for the area you changed.
5. Open a pull request with a clear summary and rationale.

## Development guidelines

- Target Python 3.11+.
- Keep code readable and maintainable.
- Prefer small, testable functions and reuse patterns already present in the codebase.
- Avoid introducing hard dependencies unless they are clearly necessary.
- Preserve the project’s privacy-first and local-processing behavior.
- Follow existing project structure and naming conventions where possible.

## Pull request expectations

A good pull request should include:

- a concise title
- a clear explanation of what changed and why
- screenshots or short demos when UX changes are involved
- any relevant validation steps or test results

We may request changes if a contribution is too broad, lacks tests, or does not align with the project’s scope.

## Licensing and contribution terms

By contributing code, documentation, design assets, or other materials to this repository, you confirm that:

- you have the right to submit the material,
- the material is your original work or you have permission to contribute it, and
- the contribution will be distributed under the MIT License.

No separate Contributor License Agreement (CLA) is required for this project. The MIT License governs all accepted contributions.

## Security or sensitive issues

If you discover a security issue or other sensitive problem, do not disclose it publicly in a normal issue thread. Please contact the maintainer directly through GitHub or the project’s secure contact channel, if provided.

Thank you for helping improve SCDossier.
