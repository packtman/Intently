"""
LSP Client - OPTIONAL enhancement for richer code intelligence.

This is an OPTIONAL FEATURE. The system works without LSP servers installed,
falling back to regex-based analysis for TypeScript/Kotlin.

When LSP servers are installed, this client provides:
- Type information for symbols
- Cross-file reference tracking
- Call hierarchy (who calls what)
- More accurate symbol detection

To install LSP servers (optional):
- TypeScript: npm install -g typescript-language-server typescript
- Python: pip install pyright  
- Kotlin: https://github.com/fwcd/kotlin-language-server
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.lsp.models import (
    Symbol,
    SymbolKind,
    Reference,
    CallHierarchyItem,
    Diagnostic,
    DiagnosticSeverity,
    Location,
    ImportInfo,
    TypeInfo,
)

logger = logging.getLogger(__name__)


# LSP SymbolKind mapping
LSP_SYMBOL_KIND_MAP = {
    1: SymbolKind.FILE,
    2: SymbolKind.MODULE,
    3: SymbolKind.NAMESPACE,
    4: SymbolKind.PACKAGE,
    5: SymbolKind.CLASS,
    6: SymbolKind.METHOD,
    7: SymbolKind.PROPERTY,
    8: SymbolKind.FIELD,
    9: SymbolKind.CONSTRUCTOR,
    10: SymbolKind.ENUM,
    11: SymbolKind.INTERFACE,
    12: SymbolKind.FUNCTION,
    13: SymbolKind.VARIABLE,
    14: SymbolKind.CONSTANT,
    15: SymbolKind.STRING,
    16: SymbolKind.NUMBER,
    17: SymbolKind.BOOLEAN,
    18: SymbolKind.ARRAY,
    19: SymbolKind.OBJECT,
    20: SymbolKind.KEY,
    21: SymbolKind.NULL,
    22: SymbolKind.ENUM_MEMBER,
    23: SymbolKind.STRUCT,
    24: SymbolKind.EVENT,
    25: SymbolKind.OPERATOR,
    26: SymbolKind.TYPE_PARAMETER,
}


@dataclass
class LSPServerConfig:
    """Configuration for a language server."""
    
    language: str
    command: list[str]
    args: list[str] = field(default_factory=list)
    initialization_options: dict[str, Any] = field(default_factory=dict)
    file_extensions: list[str] = field(default_factory=list)
    
    # Environment variables for the server
    env: dict[str, str] = field(default_factory=dict)
    
    # Server capabilities we need
    supports_call_hierarchy: bool = True
    supports_references: bool = True
    supports_document_symbols: bool = True


# Default server configurations
DEFAULT_SERVER_CONFIGS: dict[str, LSPServerConfig] = {
    "typescript": LSPServerConfig(
        language="typescript",
        command=["typescript-language-server", "--stdio"],
        file_extensions=[".ts", ".tsx", ".js", ".jsx"],
        supports_call_hierarchy=True,
        supports_references=True,
    ),
    "python": LSPServerConfig(
        language="python",
        command=["pyright-langserver", "--stdio"],
        file_extensions=[".py"],
        supports_call_hierarchy=True,
        supports_references=True,
    ),
    "kotlin": LSPServerConfig(
        language="kotlin",
        command=["kotlin-language-server"],
        file_extensions=[".kt", ".kts"],
        supports_call_hierarchy=True,
        supports_references=True,
    ),
}


class LSPClient:
    """
    Async LSP client for a single language server.
    
    Usage:
        async with LSPClient(config, workspace_path) as client:
            symbols = await client.get_document_symbols(file_path)
            references = await client.find_references(file_path, line, char)
    """
    
    def __init__(
        self,
        config: LSPServerConfig,
        workspace_path: Path,
    ) -> None:
        self.config = config
        self.workspace_path = workspace_path
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._initialized = False
        self._reader_task: asyncio.Task | None = None
        self._stdin: asyncio.StreamWriter | None = None
        self._stdout: asyncio.StreamReader | None = None
    
    async def __aenter__(self) -> LSPClient:
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
    
    async def start(self) -> None:
        """Start the language server process."""
        if self._process is not None:
            return
        
        try:
            # Build command
            cmd = self.config.command + self.config.args
            
            # Set up environment
            env = os.environ.copy()
            env.update(self.config.env)
            
            # Start process
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(self.workspace_path),
            )
            
            self._stdin = self._process.stdin
            self._stdout = self._process.stdout
            
            # Start reading responses
            self._reader_task = asyncio.create_task(self._read_responses())
            
            # Initialize the server
            await self._initialize()
            
            logger.info(f"LSP server started: {self.config.language}")
            
        except FileNotFoundError:
            logger.warning(
                f"LSP server not found for {self.config.language}. "
                f"Command: {' '.join(cmd)}"
            )
            raise LSPServerNotFoundError(
                f"Language server for {self.config.language} not found. "
                f"Install it with the appropriate package manager."
            )
    
    async def stop(self) -> None:
        """Stop the language server."""
        if self._process is None:
            return
        
        try:
            # Send shutdown request
            await self._send_request("shutdown", {})
            
            # Send exit notification
            await self._send_notification("exit", {})
            
            # Wait for process to terminate
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.terminate()
                await self._process.wait()
            
        except Exception as e:
            logger.warning(f"Error stopping LSP server: {e}")
            if self._process:
                self._process.kill()
        
        finally:
            if self._reader_task:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass
            
            self._process = None
            self._initialized = False
    
    async def _initialize(self) -> None:
        """Send LSP initialize request."""
        init_params = {
            "processId": os.getpid(),
            "rootUri": f"file://{self.workspace_path}",
            "rootPath": str(self.workspace_path),
            "capabilities": {
                "textDocument": {
                    "documentSymbol": {
                        "hierarchicalDocumentSymbolSupport": True,
                    },
                    "references": {},
                    "definition": {},
                    "hover": {},
                    "callHierarchy": {},
                    "publishDiagnostics": {
                        "relatedInformation": True,
                        "tagSupport": {"valueSet": [1, 2]},
                    },
                },
                "workspace": {
                    "symbol": {},
                    "workspaceFolders": True,
                },
            },
            "initializationOptions": self.config.initialization_options,
            "workspaceFolders": [
                {
                    "uri": f"file://{self.workspace_path}",
                    "name": self.workspace_path.name,
                }
            ],
        }
        
        result = await self._send_request("initialize", init_params)
        
        # Send initialized notification
        await self._send_notification("initialized", {})
        
        self._initialized = True
        logger.debug(f"LSP server initialized: {result.get('serverInfo', {})}")
    
    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send an LSP request and wait for response."""
        self._request_id += 1
        request_id = self._request_id
        
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        
        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        # Send message
        await self._send_message(message)
        
        # Wait for response (with timeout)
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            raise LSPTimeoutError(f"LSP request timed out: {method}")
    
    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send an LSP notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self._send_message(message)
    
    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message to the server."""
        if self._stdin is None:
            raise LSPConnectionError("LSP server not connected")
        
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        
        try:
            self._stdin.write(header.encode() + content.encode())
            await self._stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            raise LSPConnectionError("LSP server connection lost")
    
    async def _read_responses(self) -> None:
        """Read responses from the server."""
        if self._stdout is None:
            return
        
        while True:
            try:
                # Read header
                header_data = b""
                while b"\r\n\r\n" not in header_data:
                    chunk = await self._stdout.read(1)
                    if not chunk:
                        return  # EOF
                    header_data += chunk
                
                # Parse content length
                headers = header_data.decode().split("\r\n")
                content_length = 0
                for header in headers:
                    if header.lower().startswith("content-length:"):
                        content_length = int(header.split(":")[1].strip())
                        break
                
                if content_length == 0:
                    continue
                
                # Read content
                content = await self._stdout.read(content_length)
                message = json.loads(content.decode())
                
                # Handle response
                if "id" in message:
                    request_id = message["id"]
                    if request_id in self._pending_requests:
                        future = self._pending_requests.pop(request_id)
                        if "error" in message:
                            future.set_exception(
                                LSPError(message["error"].get("message", "Unknown error"))
                            )
                        else:
                            future.set_result(message.get("result", {}))
                
                # Handle notifications (diagnostics, etc.)
                elif "method" in message:
                    await self._handle_notification(message)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading LSP response: {e}")
    
    async def _handle_notification(self, message: dict[str, Any]) -> None:
        """Handle server notifications."""
        method = message.get("method", "")
        params = message.get("params", {})
        
        if method == "textDocument/publishDiagnostics":
            # Store diagnostics for later retrieval
            pass  # TODO: Implement diagnostic storage
        
        elif method == "window/logMessage":
            level = params.get("type", 4)
            text = params.get("message", "")
            if level <= 2:  # Error or warning
                logger.warning(f"LSP: {text}")
    
    # ========== Public API ==========
    
    async def open_document(self, file_path: Path) -> None:
        """Notify server that a document is open."""
        uri = f"file://{file_path}"
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            content = ""
        
        # Determine language ID
        suffix = file_path.suffix.lower()
        language_id_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescriptreact",
            ".js": "javascript",
            ".jsx": "javascriptreact",
            ".kt": "kotlin",
            ".kts": "kotlin",
        }
        language_id = language_id_map.get(suffix, "plaintext")
        
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })
    
    async def close_document(self, file_path: Path) -> None:
        """Notify server that a document is closed."""
        uri = f"file://{file_path}"
        await self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })
    
    async def get_document_symbols(self, file_path: Path) -> list[Symbol]:
        """
        Get all symbols defined in a document.
        
        Returns classes, functions, variables, etc. with their locations.
        """
        await self.open_document(file_path)
        
        uri = f"file://{file_path}"
        result = await self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        
        symbols = self._parse_document_symbols(result or [], file_path)
        return symbols
    
    async def find_references(
        self,
        file_path: Path,
        line: int,
        character: int,
        include_declaration: bool = True,
    ) -> list[Reference]:
        """
        Find all references to the symbol at the given position.
        
        Critical for impact analysis and understanding usage patterns.
        """
        await self.open_document(file_path)
        
        uri = f"file://{file_path}"
        result = await self._send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration},
        })
        
        references = []
        for ref_data in result or []:
            loc = self._parse_location(ref_data)
            if loc:
                references.append(Reference(
                    location=loc,
                    symbol_name="",  # TODO: Determine symbol name
                ))
        
        return references
    
    async def get_call_hierarchy(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> tuple[list[CallHierarchyItem], list[CallHierarchyItem]]:
        """
        Get the call hierarchy for a symbol (who calls it, what it calls).
        
        Returns (incoming_calls, outgoing_calls).
        Critical for data flow analysis.
        """
        await self.open_document(file_path)
        
        uri = f"file://{file_path}"
        
        # Prepare call hierarchy
        prepare_result = await self._send_request("textDocument/prepareCallHierarchy", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })
        
        if not prepare_result:
            return [], []
        
        incoming = []
        outgoing = []
        
        for item in prepare_result:
            # Get incoming calls (who calls this)
            incoming_result = await self._send_request("callHierarchy/incomingCalls", {
                "item": item
            })
            for call_data in incoming_result or []:
                incoming.append(self._parse_call_hierarchy_item(call_data, is_incoming=True))
            
            # Get outgoing calls (what this calls)
            outgoing_result = await self._send_request("callHierarchy/outgoingCalls", {
                "item": item
            })
            for call_data in outgoing_result or []:
                outgoing.append(self._parse_call_hierarchy_item(call_data, is_incoming=False))
        
        return incoming, outgoing
    
    async def get_hover_info(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> TypeInfo | None:
        """
        Get type/hover information for a position.
        
        Returns type signatures, documentation, etc.
        """
        await self.open_document(file_path)
        
        uri = f"file://{file_path}"
        result = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })
        
        if not result or "contents" not in result:
            return None
        
        contents = result["contents"]
        if isinstance(contents, dict):
            value = contents.get("value", "")
        elif isinstance(contents, list):
            value = "\n".join(
                c.get("value", c) if isinstance(c, dict) else str(c)
                for c in contents
            )
        else:
            value = str(contents)
        
        return TypeInfo(
            type_string=value,
            is_any="any" in value.lower(),
        )
    
    async def get_definition(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> Location | None:
        """
        Go to definition of a symbol.
        
        Useful for resolving imports and understanding code structure.
        """
        await self.open_document(file_path)
        
        uri = f"file://{file_path}"
        result = await self._send_request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })
        
        if not result:
            return None
        
        # Result can be Location, Location[], or LocationLink[]
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        
        return self._parse_location(result)
    
    async def get_workspace_symbols(self, query: str = "") -> list[Symbol]:
        """
        Search for symbols across the entire workspace.
        
        Useful for finding all implementations of a pattern (e.g., all controllers).
        """
        result = await self._send_request("workspace/symbol", {
            "query": query
        })
        
        symbols = []
        for sym_data in result or []:
            loc = self._parse_location(sym_data.get("location", {}))
            if loc:
                kind_num = sym_data.get("kind", 0)
                kind = LSP_SYMBOL_KIND_MAP.get(kind_num, SymbolKind.VARIABLE)
                
                symbols.append(Symbol(
                    name=sym_data.get("name", ""),
                    kind=kind,
                    location=loc,
                    container_name=sym_data.get("containerName", ""),
                ))
        
        return symbols
    
    # ========== Parsing Helpers ==========
    
    def _parse_document_symbols(
        self,
        data: list[dict[str, Any]],
        file_path: Path,
    ) -> list[Symbol]:
        """Parse document symbols from LSP response."""
        symbols = []
        
        for sym_data in data:
            symbol = self._parse_symbol(sym_data, file_path)
            if symbol:
                symbols.append(symbol)
        
        return symbols
    
    def _parse_symbol(
        self,
        data: dict[str, Any],
        file_path: Path,
    ) -> Symbol | None:
        """Parse a single symbol from LSP response."""
        name = data.get("name", "")
        if not name:
            return None
        
        # Get location from 'range' (DocumentSymbol) or 'location' (SymbolInformation)
        if "range" in data:
            range_data = data["range"]
            location = Location(
                uri=f"file://{file_path}",
                start_line=range_data["start"]["line"],
                start_character=range_data["start"]["character"],
                end_line=range_data["end"]["line"],
                end_character=range_data["end"]["character"],
            )
        elif "location" in data:
            location = self._parse_location(data["location"])
            if not location:
                return None
        else:
            return None
        
        # Parse kind
        kind_num = data.get("kind", 0)
        kind = LSP_SYMBOL_KIND_MAP.get(kind_num, SymbolKind.VARIABLE)
        
        # Parse children (for hierarchical symbols)
        children = []
        for child_data in data.get("children", []):
            child = self._parse_symbol(child_data, file_path)
            if child:
                children.append(child)
        
        return Symbol(
            name=name,
            kind=kind,
            location=location,
            detail=data.get("detail", ""),
            children=children,
            is_deprecated=1 in data.get("tags", []),  # LSP tag 1 = deprecated
        )
    
    def _parse_location(self, data: dict[str, Any]) -> Location | None:
        """Parse a Location from LSP response."""
        if not data:
            return None
        
        uri = data.get("uri", "")
        
        # Handle both 'range' and direct position fields
        if "range" in data:
            range_data = data["range"]
        elif "targetRange" in data:  # LocationLink
            range_data = data["targetRange"]
            uri = data.get("targetUri", uri)
        else:
            return None
        
        return Location(
            uri=uri,
            start_line=range_data["start"]["line"],
            start_character=range_data["start"]["character"],
            end_line=range_data["end"]["line"],
            end_character=range_data["end"]["character"],
        )
    
    def _parse_call_hierarchy_item(
        self,
        data: dict[str, Any],
        is_incoming: bool,
    ) -> CallHierarchyItem:
        """Parse a call hierarchy item."""
        # For incoming/outgoing calls, the item is in 'from' or 'to'
        if is_incoming:
            item_data = data.get("from", data)
            call_ranges = data.get("fromRanges", [])
        else:
            item_data = data.get("to", data)
            call_ranges = data.get("fromRanges", [])
        
        uri = item_data.get("uri", "")
        range_data = item_data.get("range", {})
        
        location = Location(
            uri=uri,
            start_line=range_data.get("start", {}).get("line", 0),
            start_character=range_data.get("start", {}).get("character", 0),
            end_line=range_data.get("end", {}).get("line", 0),
            end_character=range_data.get("end", {}).get("character", 0),
        )
        
        # Parse call location if available
        call_location = None
        if call_ranges:
            first_range = call_ranges[0]
            call_location = Location(
                uri=uri,
                start_line=first_range.get("start", {}).get("line", 0),
                start_character=first_range.get("start", {}).get("character", 0),
                end_line=first_range.get("end", {}).get("line", 0),
                end_character=first_range.get("end", {}).get("character", 0),
            )
        
        kind_num = item_data.get("kind", 12)  # Default to FUNCTION
        kind = LSP_SYMBOL_KIND_MAP.get(kind_num, SymbolKind.FUNCTION)
        
        return CallHierarchyItem(
            name=item_data.get("name", ""),
            kind=kind,
            location=location,
            call_location=call_location,
            is_incoming=is_incoming,
            is_outgoing=not is_incoming,
            detail=item_data.get("detail", ""),
        )


class LSPClientManager:
    """
    Manages multiple LSP clients for different languages.
    
    Automatically selects the appropriate client based on file type.
    """
    
    def __init__(
        self,
        workspace_path: Path,
        configs: dict[str, LSPServerConfig] | None = None,
    ) -> None:
        self.workspace_path = workspace_path
        self.configs = configs or DEFAULT_SERVER_CONFIGS
        self._clients: dict[str, LSPClient] = {}
        self._started = False
    
    async def __aenter__(self) -> LSPClientManager:
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
    
    async def start(self) -> None:
        """Start all configured language servers."""
        if self._started:
            return
        
        for language, config in self.configs.items():
            try:
                client = LSPClient(config, self.workspace_path)
                await client.start()
                self._clients[language] = client
                logger.info(f"LSP server started for {language}")
            except LSPServerNotFoundError:
                logger.warning(f"LSP server for {language} not available")
            except Exception as e:
                logger.warning(f"Failed to start LSP server for {language}: {e}")
        
        self._started = True
        logger.info(f"LSP clients started: {list(self._clients.keys())}")
    
    async def stop(self) -> None:
        """Stop all language servers."""
        for client in self._clients.values():
            await client.stop()
        self._clients.clear()
        self._started = False
    
    def get_client_for_file(self, file_path: Path) -> LSPClient | None:
        """Get the appropriate LSP client for a file."""
        suffix = file_path.suffix.lower()
        
        for language, config in self.configs.items():
            if suffix in config.file_extensions:
                return self._clients.get(language)
        
        return None
    
    async def get_document_symbols(self, file_path: Path) -> list[Symbol]:
        """Get symbols for a file using the appropriate client."""
        client = self.get_client_for_file(file_path)
        if client:
            return await client.get_document_symbols(file_path)
        return []
    
    async def find_references(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> list[Reference]:
        """Find references using the appropriate client."""
        client = self.get_client_for_file(file_path)
        if client:
            return await client.find_references(file_path, line, character)
        return []
    
    async def get_call_hierarchy(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> tuple[list[CallHierarchyItem], list[CallHierarchyItem]]:
        """Get call hierarchy using the appropriate client."""
        client = self.get_client_for_file(file_path)
        if client:
            return await client.get_call_hierarchy(file_path, line, character)
        return [], []


# ========== Exceptions ==========

class LSPError(Exception):
    """Base exception for LSP errors."""
    pass


class LSPServerNotFoundError(LSPError):
    """Raised when a language server is not installed."""
    pass


class LSPConnectionError(LSPError):
    """Raised when connection to language server fails."""
    pass


class LSPTimeoutError(LSPError):
    """Raised when an LSP request times out."""
    pass
