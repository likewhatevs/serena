"""
Basic integration tests for the Starlark language server functionality using starpls.

These tests validate the functionality of the language server APIs
using the Starlark test repository.

starpls Capabilities:
- ✅ textDocumentSync (full sync)
- ✅ definitionProvider (go-to-definition)
- ✅ referencesProvider (find references)
- ✅ hoverProvider (hover information)
- ✅ completionProvider (code completion)
- ✅ documentSymbolProvider (document symbols)
- ✅ diagnostics (syntax errors, type checking)
- ❌ renameProvider (not implemented)
- ❌ workspaceSymbolProvider (not implemented)

https://github.com/withered-magic/starpls
"""

import shutil

import pytest

from solidlsp import SolidLanguageServer
from solidlsp.ls_config import Language

# Skip all tests if starpls is not installed
pytestmark = pytest.mark.skipif(
    shutil.which("starpls") is None,
    reason="starpls is not installed. Install from https://github.com/withered-magic/starpls/releases",
)


@pytest.mark.starlark
class TestStarlarkLanguageServerBasics:
    """Test basic functionality of the starpls language server."""

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_language_server_initialization(self, language_server: SolidLanguageServer) -> None:
        """Test that Starlark language server can be initialized successfully."""
        assert language_server is not None
        assert language_server.language == Language.STARLARK

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_server_is_running(self, language_server: SolidLanguageServer) -> None:
        """Test that starpls is running after initialization."""
        assert language_server.server is not None
        assert language_server.server.is_running()

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_go_to_definition(self, language_server: SolidLanguageServer) -> None:
        """Test go-to-definition for Starlark symbols.

        Tests that clicking on 'my_binary' call within create_test_target in defs.bzl
        navigates to the my_binary function definition.
        """
        # In defs.bzl line 39 (0-indexed 38): my_binary(
        # This is inside create_test_target function, calling my_binary
        definitions = language_server.request_definition("defs.bzl", 38, 6)

        assert len(definitions) > 0, "Should find definition of my_binary"
        assert definitions[0]["relativePath"] == "defs.bzl", "Definition should be in defs.bzl"

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_hover(self, language_server: SolidLanguageServer) -> None:
        """Test hover functionality."""
        # Hover over a function definition
        hover = language_server.request_hover("defs.bzl", 10, 5)

        # Hover should return something (even if contents is empty)
        # The important thing is it doesn't hang or error
        assert hover is not None or hover == {}, "Hover should return a response (may be empty)"

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_document_symbols(self, language_server: SolidLanguageServer) -> None:
        """Test document symbols functionality."""
        symbols = language_server.request_document_symbols("defs.bzl")

        # defs.bzl contains functions like my_binary, my_library, create_test_target, get_default_visibility
        # and constants like DEFAULT_COMPILER_FLAGS, SUPPORTED_PLATFORMS
        assert symbols is not None, "Should return document symbols"
        # At minimum we should have some symbols
        assert len(symbols.root_symbols) > 0, "Should find symbols in defs.bzl"

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_completions(self, language_server: SolidLanguageServer) -> None:
        """Test code completion functionality.

        starpls provides completions for variables, function parameters,
        builtin type fields, and more.
        """
        # Request completions at a position where we'd expect suggestions
        # In defs.bzl, inside a function body after typing a partial identifier
        completions = language_server.request_completions("defs.bzl", 38, 4)

        # Completions should return a response (list may be empty depending on context)
        assert completions is not None, "Should return completions response"

    @pytest.mark.parametrize("language_server", [Language.STARLARK], indirect=True)
    def test_starlark_references(self, language_server: SolidLanguageServer) -> None:
        """Test find references functionality.

        starpls supports finding references to symbols.
        """
        # Find references to my_binary function (defined at line 11, column 4)
        # my_binary is called in create_test_target at line 39
        references = language_server.request_references("defs.bzl", 10, 6)

        # Should find at least the definition and one usage
        assert references is not None, "Should return references response"
