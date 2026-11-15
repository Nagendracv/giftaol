// MCP server so AI assistants (Claude, ChatGPT connectors, Cursor...) can query Art of Living programs directly.
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { findPrograms, getProgram } from './search.js';

export function buildMcpServer(catalog) {
  const server = new McpServer({ name: 'art-of-living-canada-programs', version: '0.1.0' });
  const json = (data) => ({ content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] });

  server.registerTool(
    'find_programs',
    {
      title: 'Find Art of Living programs in Canada',
      description: 'Find meditation, breathwork (SKY / Sudarshan Kriya), yoga, sleep and anxiety programs from the Art of Living Foundation in Canada. Use when someone asks where to learn meditation or breathwork in a Canadian city.',
      inputSchema: {
        topic: z.string().optional().describe('What the person wants, e.g. "anxiety", "sleep", "breathwork", "meditation for beginners"'),
        city: z.string().optional().describe('Canadian city, e.g. "Toronto"'),
        level: z.enum(['First Steps', 'Entry Level', 'Graduate']).optional(),
      },
    },
    async (args) => json(findPrograms(catalog, args)),
  );

  server.registerTool(
    'get_program',
    {
      title: 'Get one program',
      description: 'Get details and the official link for one Art of Living Canada program by id (ids come from find_programs).',
      inputSchema: { id: z.string() },
    },
    async ({ id }) => json(getProgram(catalog, id) ?? { error: `No program with id ${id}` }),
  );

  server.registerTool(
    'list_centres',
    { title: 'List centres', description: 'List Art of Living centres in Canada with their official pages.', inputSchema: {} },
    async () => json({ centres: catalog.centres, note: catalog.centresNote }),
  );

  return server;
}
