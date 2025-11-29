"""
Provides Starlark specific instantiation of the LanguageServer class using starpls.
Starpls is a full-featured language server for Starlark, supporting Bazel and Buck2.
https://github.com/withered-magic/starpls
"""

import logging
import os
import pathlib
import shutil
import subprocess
import threading

from overrides import override

from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.lsp_protocol_handler.lsp_types import InitializeParams
from solidlsp.lsp_protocol_handler.server import ProcessLaunchInfo
from solidlsp.settings import SolidLSPSettings

log = logging.getLogger(__name__)


class StarplsServer(SolidLanguageServer):
    """
    Provides Starlark specific instantiation of the LanguageServer class using starpls.
    Starpls provides full LSP support for Starlark files including document symbols,
    go-to-definition, hover, completion, and more.
    """

    @override
    def is_ignored_dirname(self, dirname: str) -> bool:
        # For Starlark/Bazel/Buck2 projects, ignore:
        # - bazel-*: Bazel output directories (symlinks)
        # - buck-out: Buck2 build output directory
        # - .buck: Buck cache directory
        return super().is_ignored_dirname(dirname) or dirname.startswith("bazel-") or dirname in ["buck-out", ".buck"]

    @staticmethod
    def _get_starpls_path() -> str | None:
        """Get the path to starpls executable or None if not found."""
        return shutil.which("starpls")

    @staticmethod
    def _get_starpls_version(starpls_path: str) -> str | None:
        """Get the installed starpls version or None if not found."""
        try:
            result = subprocess.run([starpls_path, "--version"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            return None
        return None

    @staticmethod
    def _setup_runtime_dependency() -> str:
        """
        Check if required starpls runtime dependency is available.
        Returns the path to the starpls executable.
        Raises RuntimeError with helpful message if starpls is not installed.
        """
        starpls_path = StarplsServer._get_starpls_path()
        if not starpls_path:
            raise RuntimeError(
                "starpls is not installed. Please install it:\n\n"
                "  macOS (Homebrew): brew install withered-magic/brew/starpls\n"
                "  Other: Download from https://github.com/withered-magic/starpls/releases\n\n"
                "Make sure the starpls executable is in your PATH."
            )

        version = StarplsServer._get_starpls_version(starpls_path)
        log.info(f"Found starpls: {version or 'unknown version'} at {starpls_path}")
        return starpls_path

    def __init__(self, config: LanguageServerConfig, repository_root_path: str, solidlsp_settings: SolidLSPSettings):
        starpls_path = self._setup_runtime_dependency()

        # starpls server mode with experimental features for better support
        super().__init__(
            config,
            repository_root_path,
            ProcessLaunchInfo(cmd=[starpls_path, "server"], cwd=repository_root_path),
            "starlark",
            solidlsp_settings,
        )
        self.server_ready = threading.Event()
        self.request_id = 0

    @staticmethod
    def _get_initialize_params(repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the starpls Language Server.
        """
        root_uri = pathlib.Path(repository_absolute_path).as_uri()
        initialize_params = {
            "locale": "en",
            "capabilities": {
                "textDocument": {
                    "synchronization": {"didSave": True, "dynamicRegistration": True},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "dynamicRegistration": True,
                        "hierarchicalDocumentSymbolSupport": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                    "hover": {"dynamicRegistration": True, "contentFormat": ["markdown", "plaintext"]},
                    "completion": {"dynamicRegistration": True, "completionItem": {"snippetSupport": True}},
                },
                "workspace": {
                    "workspaceFolders": True,
                    "didChangeConfiguration": {"dynamicRegistration": True},
                },
            },
            "processId": os.getpid(),
            "rootPath": repository_absolute_path,
            "rootUri": root_uri,
            "workspaceFolders": [
                {
                    "uri": root_uri,
                    "name": os.path.basename(repository_absolute_path),
                }
            ],
        }
        return initialize_params  # type: ignore

    def _start_server(self) -> None:
        """Start starpls server process."""

        def register_capability_handler(params: dict) -> None:
            return

        def window_log_message(msg: dict) -> None:
            log.info(f"LSP: window/logMessage: {msg}")

        def do_nothing(params: dict) -> None:
            return

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)

        log.info("Starting starpls server process")
        self.server.start()
        initialize_params = self._get_initialize_params(self.repository_root_path)

        log.info("Sending initialize request from LSP client to LSP server and awaiting response")
        init_response = self.server.send.initialize(initialize_params)

        # Log capabilities for debugging
        capabilities = init_response.get("capabilities", {})
        log.debug(f"starpls capabilities: {capabilities}")

        # Verify expected capabilities
        if "documentSymbolProvider" in capabilities:
            log.info("starpls supports document symbols")
        if "definitionProvider" in capabilities:
            log.info("starpls supports go-to-definition")

        self.server.notify.initialized({})
        self.completions_available.set()

        # starpls is typically ready immediately after initialization
        self.server_ready.set()
        self.server_ready.wait()

    @override
    def _shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown the starpls server.

        Override to suppress noisy shutdown errors from reader threads.
        """
        if not self.server.is_running():
            log.debug("Server process not running, skipping shutdown.")
            return

        log.debug("Shutting down starpls server")

        # Suppress expected shutdown errors from reader threads
        import logging as _logging

        ls_handler_logger = _logging.getLogger("solidlsp.ls_handler")
        original_level = ls_handler_logger.level
        ls_handler_logger.setLevel(_logging.CRITICAL)

        try:
            # Just stop the process directly - starpls exits cleanly
            self.server.stop()
        finally:
            ls_handler_logger.setLevel(original_level)
