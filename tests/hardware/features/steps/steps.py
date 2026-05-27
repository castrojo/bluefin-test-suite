"""
Hardware emulation step definitions.

Most steps are SSH command + output check — reuse common patterns.
TODO: Implement custom steps for device-specific checks.
See QA-REVIEW.md Epic E12.
"""
from behave import step


# Most steps reuse common SSH patterns from other suites.
# Only hardware-specific custom steps go here.
