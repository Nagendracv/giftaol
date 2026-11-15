// Local MCP server over stdio, e.g. for Claude Desktop: { "command": "node", "args": ["scripts/mcp-stdio.js"] }
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { buildMcpServer } from '../src/feed/mcp.js';
import { loadCatalog } from '../src/data.js';

await buildMcpServer(loadCatalog()).connect(new StdioServerTransport());
