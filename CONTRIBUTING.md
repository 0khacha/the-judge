# Contributing to The Judge

Thank you for your interest in contributing to **The Judge**!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/0khacha/the-judge.git
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install in development mode with test dependencies:
   ```bash
   pip install -e .
   ```

4. Run the test suite:
   ```bash
   pytest tests/
   ```

## Pull Request Guidelines

- Ensure all new features or bug fixes are accompanied by unit or integration tests in `tests/`.
- Maintain strict hard gate invariants and security isolation boundaries.
- Run `pytest tests/` and verify 100% test pass rate before submitting a pull request.
