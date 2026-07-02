# What We Will Evaluate

- [ ] A `TESTING.md` file is present and documents the test plan, how to run tests, and coverage results.
- [ ] `uv run pytest` runs without errors from the project root and all tests pass.
- [ ] The test suite includes happy-path, edge-case, and failure-mode tests for each authentication endpoint.
- [ ] Test coverage on the authentication module is at or above 70% (verified with `uv run pytest --cov`).
- [ ] Tests assert business logic, not HTTP serialisation or framework behaviour.
- [ ] If TypeScript utility functions exist, Jest tests are present and passing.
- [ ] The AI-assisted workflow is evident: `TESTING.md` notes at least one case identified with AI assistance or one bug caught by the test suite.
- [ ] Code is clean: tests are named clearly, follow a consistent structure, and include brief comments explaining non-obvious assertions.

> **Note:** The evaluation does not require 100% coverage. The quality and intent of the test cases matter more than the coverage number. A well-reasoned 70% is worth more than a mechanical 95%.

> **Extra activity:** The backoffice and frontend test suites are not required for a passing grade, but they will be recognised in the evaluation if present and passing.
