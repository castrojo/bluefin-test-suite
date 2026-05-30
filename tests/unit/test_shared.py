"""Unit tests for testsuite Python modules — file structure and syntax validation."""

import os


def test_testsuite_structure_has_expected_directories():
    """The tests/ directory contains all expected test suite subdirectories."""
    tests_dir = os.path.join(os.path.dirname(__file__), "..")
    suites = os.listdir(tests_dir)

    expected = {
        "smoke", "developer", "dx", "hardware", "lifecycle",
        "nvidia", "security", "software", "vanilla-gnome", "flatcar",
        "bazzite", "common",
    }
    found = set(suites) & expected
    missing = expected - found
    assert not missing, f"Missing test suite directories: {missing}"


def test_shared_ssh_steps_file_exists_and_has_key_functions():
    """ssh_steps.py is present and textually contains expected function names."""
    ssh_steps_path = os.path.join(
        os.path.dirname(__file__), "..", "shared", "ssh_steps.py"
    )
    assert os.path.isfile(ssh_steps_path), f"Missing {ssh_steps_path}"

    with open(ssh_steps_path) as fh:
        source = fh.read()

    assert "def run_ssh" in source, "run_ssh not found in ssh_steps.py"
    assert "def vm_reachable_over_ssh" in source, "vm_reachable_over_ssh not found"
    assert "def run_ssh_command" in source, "run_ssh_command not found"


def test_smoke_step_files_syntax():
    """All smoke step .py files compile cleanly."""
    tests_base = os.path.join(os.path.dirname(__file__), "..")
    smoke_steps_dir = os.path.join(tests_base, "smoke", "features", "steps")
    assert os.path.isdir(smoke_steps_dir), f"Missing {smoke_steps_dir}"

    for sf in sorted(os.listdir(smoke_steps_dir)):
        if not sf.endswith(".py"):
            continue
        path = os.path.join(smoke_steps_dir, sf)
        with open(path) as fh:
            source = fh.read()
        compile(source, path, "exec")  # Syntax check
        print(f"  ✓ {sf}")


def test_environment_files_syntax():
    """All environment.py files compile cleanly (syntax-check only)."""
    tests_base = os.path.join(os.path.dirname(__file__), "..")
    for suite_dir in sorted(os.listdir(tests_base)):
        suite_path = os.path.join(tests_base, suite_dir)
        env_py = os.path.join(suite_path, "features", "environment.py")
        if os.path.isfile(env_py):
            with open(env_py) as fh:
                source = fh.read()
            compile(source, env_py, "exec")
            print(f"  ✓ {suite_dir}/features/environment.py")


def test_all_python_files_syntax():
    """Every .py file under tests/ compiles cleanly."""
    tests_base = os.path.join(os.path.dirname(__file__), "..")
    count = 0
    for root, dirs, files in os.walk(tests_base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                source = fh.read()
            compile(source, path, "exec")
            count += 1
    assert count > 0, "No Python files found"
    print(f"  ✓ {count} Python files compile cleanly")


def test_workflows_directory_has_expected_files():
    """CI workflow files exist."""
    workflows_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", ".github", "workflows"
    )
    assert os.path.isdir(workflows_dir), f"Missing {workflows_dir}"
    wf_files = os.listdir(workflows_dir)
    assert "unit-tests.yml" in wf_files, "unit-tests.yml workflow is missing"
    assert "pr-validate.yml" in wf_files, "pr-validate.yml workflow is missing"


def test_feature_files_have_scenarios():
    """Every feature file contains at least one Scenario."""
    tests_base = os.path.join(os.path.dirname(__file__), "..")
    empty_features = []
    for root, dirs, files in os.walk(tests_base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for f in sorted(files):
            if not f.endswith(".feature"):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            if "Scenario" not in content:
                empty_features.append(path)
    assert not empty_features, f"Feature files with no Scenario: {empty_features}"


def test_qa_review_has_scenario_count():
    """QA-REVIEW.md contains a scenario count line."""
    qa_path = os.path.join(os.path.dirname(__file__), "..", "..", "QA-REVIEW.md")
    assert os.path.isfile(qa_path), "QA-REVIEW.md is missing"
    with open(qa_path) as fh:
        content = fh.read()
    assert "scenarios across" in content, (
        "QA-REVIEW.md must contain a 'N scenarios across M feature files' line"
    )


def test_suite_map_has_scenario_count():
    """docs/skills/suite-map.md contains a scenario count line."""
    map_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "skills", "suite-map.md"
    )
    assert os.path.isfile(map_path), "docs/skills/suite-map.md is missing"
    with open(map_path) as fh:
        content = fh.read()
    assert "scenarios across" in content, (
        "suite-map.md must contain a 'N scenarios across M feature files' line"
    )
