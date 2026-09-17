# Project Structure

Complete overview of The Judge project organization.

## Directory Structure

```
the-judge/
├── .github/                    # GitHub configuration
│   ├── ISSUE_TEMPLATE/        # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/             # CI/CD workflows (future)
│
├── .vscode/                   # VS Code configuration
│   ├── extensions.json        # Recommended extensions
│   ├── settings.json          # Editor settings
│   └── tasks.json            # Task definitions
│
├── assets/                    # Project assets
│   └── logo.svg              # Project logo
│
├── benchmark/                 # Adversarial test benchmarks
│   └── adversarial_tasks/    # Challenge scenarios
│
├── docs/                      # Documentation
│   ├── INDEX.md              # Documentation index
│   ├── QUICK_START.md        # Quick start guide
│   ├── API.md                # Python API reference
│   ├── DEVELOPMENT.md        # Development guide
│   └── architecture.md       # Architecture spec
│
├── examples/                  # Usage examples
│   ├── INTEGRATION_EXAMPLES.md
│   └── simple_cache/         # Example project
│       ├── __init__.py
│       ├── cache.py          # Implementation
│       ├── test_cache.py     # Tests
│       ├── judge.json        # Contract
│       └── README.md
│
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── test_critique_engine.py
│   ├── test_visual_engine.py
│   └── test_*.py             # Integration tests
│
├── the_judge/                 # Main package
│   ├── __init__.py           # Public API exports
│   ├── api.py                # Core API functions
│   ├── py.typed              # Type checking marker
│   │
│   ├── core/                 # Core verification engine
│   │   ├── __init__.py
│   │   ├── sandbox.py        # Sandboxed execution
│   │   ├── evidence.py       # Evidence capture
│   │   ├── score_engine.py   # Scoring and gates
│   │   ├── critique_engine.py # Adversarial critique
│   │   ├── contract_engine.py # Requirement contracts
│   │   ├── contract_parser.py # Contract parsing
│   │   ├── property_engine.py # Dynamic properties
│   │   ├── behavior_engine.py # Behavioral checks
│   │   ├── visual_engine.py   # Visual evaluation
│   │   └── decision.py        # Result data classes
│   │
│   └── integrations/         # External integrations
│       ├── __init__.py
│       ├── cli.py            # CLI interface
│       ├── agent_adapter.py  # Agent formatters
│       ├── repair_loop.py    # Improvement loop
│       ├── auto_improver.py  # Auto-repair engine
│       ├── audit_trail.py    # Audit logging
│       ├── progress_report.py # Progress tracking
│       ├── hooks.py          # Git hooks
│       ├── ide.py            # IDE integration
│       ├── watcher.py        # File watcher
│       └── demo.py           # Interactive demo
│
├── judge/                     # Backward compatibility shim
│   └── __init__.py           # Redirects to the_judge
│
├── .editorconfig             # Editor configuration
├── .gitattributes            # Git attributes
├── .gitignore                # Git ignore rules
├── AGENTS.md                 # Agent integration protocol
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contributing guidelines
├── INSTALL.md                # Installation instructions
├── LICENSE                   # MIT License
├── Makefile                  # Development commands
├── MANIFEST.in               # Package manifest
├── PLUGIN_GUIDE.md           # Plugin integration guide
├── pyproject.toml            # Package configuration
├── README.md                 # Project overview
├── SECURITY.md               # Security model
├── setup.py                  # Setup script (backward compat)
└── THREAT_MODEL.md           # Threat analysis
```

## Core Components

### Verification Engine (`the_judge/core/`)

**Purpose**: Core verification logic

- `sandbox.py` - Isolated test execution
- `evidence.py` - Evidence collection from tests
- `score_engine.py` - Scoring algorithm and hard gates
- `behavior_engine.py` - Behavioral property checks
- `property_engine.py` - Dynamic property validation
- `contract_engine.py` - Requirement contract evaluation
- `critique_engine.py` - Adversarial critique system
- `visual_engine.py` - Visual quality evaluation
- `decision.py` - Result data structures

### Integration Layer (`the_judge/integrations/`)

**Purpose**: External tool integration

- `cli.py` - Command-line interface
- `agent_adapter.py` - AI agent output formatting
- `repair_loop.py` - Multi-round improvement
- `auto_improver.py` - Autonomous repair engine
- `audit_trail.py` - Audit logging and tracking
- `progress_report.py` - Progress reporting
- `hooks.py` - Git hook management
- `ide.py` - IDE task generation
- `watcher.py` - File watching
- `demo.py` - Interactive demo

## Key Files

### Configuration

- `pyproject.toml` - Modern Python package configuration
- `setup.py` - Backward compatibility setup
- `MANIFEST.in` - Package file inclusion rules
- `.editorconfig` - Editor configuration
- `.gitattributes` - Git line ending configuration

### Development

- `Makefile` - Common development commands
- `.vscode/` - VS Code configuration
- `tests/` - Test suite
- `benchmark/` - Adversarial benchmarks

### Documentation

- `README.md` - Project overview
- `INSTALL.md` - Installation guide
- `AGENTS.md` - Agent protocol
- `PLUGIN_GUIDE.md` - Plugin integration
- `CONTRIBUTING.md` - Contributing guidelines
- `CHANGELOG.md` - Version history
- `docs/` - Detailed documentation

### Legal & Security

- `LICENSE` - MIT License
- `SECURITY.md` - Security model
- `THREAT_MODEL.md` - Threat analysis

## Package Structure

### Public API (`the_judge/__init__.py`)

Exports:
- `verify()` - Main verification function
- `verify_workspace()` - Workspace verification
- `improve()` - Continuous improvement loop
- `critique()` - Adversarial critique
- `VerificationResult` - Result data class
- `Finding` - Finding data class

### CLI Entry Point

Defined in `pyproject.toml`:
```toml
[project.scripts]
judge = "the_judge.integrations.cli:main"
```

### Import Patterns

```python
# Public API
from the_judge import verify, improve, critique

# Core components (for advanced usage)
from the_judge.core import SandboxRunner, CritiqueEngine

# Integrations (for custom workflows)
from the_judge.integrations import AgentRepairLoop, AutoImprover
```

## File Naming Conventions

- **Python files**: `snake_case.py`
- **Test files**: `test_*.py`
- **Documentation**: `UPPERCASE.md` for root docs, `Title Case.md` for guides
- **Config files**: Standard names (`.editorconfig`, `pyproject.toml`, etc.)

## Code Organization Principles

1. **Separation of concerns**: Core engine vs integrations
2. **Single responsibility**: Each module has one clear purpose
3. **Dependency direction**: Integrations depend on core, not vice versa
4. **Public API**: Clear exports in `__init__.py`
5. **Type safety**: Type hints everywhere, `py.typed` marker
6. **Documentation**: Docstrings for all public APIs

## Data Flow

```
User Request
    ↓
CLI (cli.py) or Python API (api.py)
    ↓
Evidence Capture (evidence.py)
    ↓
Sandbox Execution (sandbox.py)
    ↓
Behavioral Checks (behavior_engine.py, property_engine.py)
    ↓
Contract Evaluation (contract_engine.py)
    ↓
Scoring (score_engine.py)
    ↓
Decision (decision.py)
    ↓
Critique (critique_engine.py) [if needed]
    ↓
Result → User
```

## Extension Points

### Custom Quality Evaluators

```python
def my_evaluator(workspace, verification):
    return {"score": 85, "passed": False, "weaknesses": [...]}
```

### Custom Repair Functions

```python
def my_repair(workspace, feedback):
    # Custom repair logic
    return {"changed": True, "description": "..."}
```

### Custom Agents

```python
from the_judge.integrations import AgentAdapter

adapter = AgentAdapter(name="MyAgent")
feedback = adapter.verify_workspace(".")
```

## Build Artifacts

Generated during build:
- `dist/` - Distribution packages
- `build/` - Build directory
- `*.egg-info/` - Package metadata
- `__pycache__/` - Python bytecode
- `.pytest_cache/` - Pytest cache
- `.mypy_cache/` - Mypy cache
- `.ruff_cache/` - Ruff cache
- `htmlcov/` - Coverage reports

## Version Control

Ignored files (`.gitignore`):
- Build artifacts
- Cache directories
- Virtual environments
- IDE-specific files (except `.vscode/`)
- OS-specific files

Tracked files:
- All source code
- Documentation
- Configuration
- Tests
- Examples

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development guide
- [API.md](API.md) - API reference
- [architecture.md](architecture.md) - Architecture details
