# Custom build rules for testing

def _my_binary_impl(ctx):
    """Implementation of my_binary rule."""
    return None

def _my_library_impl(ctx):
    """Implementation of my_library rule."""
    return None

def my_binary(name, srcs = [], deps = []):
    """A simple binary target.

    Args:
        name: The name of the target
        srcs: Source files
        deps: Dependencies
    """
    pass

def my_library(name, srcs = [], hdrs = [], deps = []):
    """A simple library target.

    Args:
        name: The name of the target
        srcs: Source files
        hdrs: Header files
        deps: Dependencies
    """
    pass

def create_test_target(name, test_srcs):
    """Helper function to create test targets.

    Args:
        name: The name of the test target
        test_srcs: List of test source files
    """
    my_binary(
        name = name,
        srcs = test_srcs,
    )

def get_default_visibility():
    """Returns the default visibility for targets."""
    return ["PUBLIC"]

# Constants
DEFAULT_COMPILER_FLAGS = [
    "-Wall",
    "-Werror",
]

SUPPORTED_PLATFORMS = [
    "linux-x86_64",
    "macos-arm64",
    "windows-x86_64",
]
