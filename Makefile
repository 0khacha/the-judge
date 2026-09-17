.PHONY: help install dev-install test lint format clean build publish docs

help:
	@echo "The Judge - Development Commands"
	@echo ""
	@echo "install       Install the package"
	@echo "dev-install   Install with development dependencies"
	@echo "test          Run test suite"
	@echo "test-cov      Run tests with coverage report"
	@echo "lint          Run linters (ruff, mypy)"
	@echo "format        Format code with ruff"
	@echo "clean         Remove build artifacts and cache files"
	@echo "build         Build distribution packages"
	@echo "verify        Run judge verify on the project itself"
	@echo "demo          Run the interactive demo"
	@echo ""

install:
	pip install -e .

dev-install:
	pip install -e ".[dev,visual]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=the_judge --cov-report=html --cov-report=term

lint:
	ruff check the_judge/ tests/
	mypy the_judge/

format:
	ruff format the_judge/ tests/
	ruff check --fix the_judge/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

verify:
	judge verify .

demo:
	judge demo
