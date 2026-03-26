/**
 * Node.js HTTP entrypoint for @sillyl12324/xhs-mcp.
 *
 * Adds a legacy-compatible `xhs_publish_content` MCP tool on top of upstream 2.7.0,
 * while preserving the upstream tool surface and routing behavior.
 */
import http from 'node:http';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

import { initDatabase } from '@sillyl12324/xhs-mcp/dist/db/index.js';
import { getAccountPool } from '@sillyl12324/xhs-mcp/dist/core/account-pool.js';
import { executeWithMultipleAccounts } from '@sillyl12324/xhs-mcp/dist/core/multi-account.js';
import { PUBLISH_SELECTORS } from '@sillyl12324/xhs-mcp/dist/xhs/clients/constants.js';

import { accountTools, handleAccountTools } from '@sillyl12324/xhs-mcp/dist/tools/account.js';
import { authTools, handleAuthTools } from '@sillyl12324/xhs-mcp/dist/tools/auth.js';
import { contentTools, handleContentTools } from '@sillyl12324/xhs-mcp/dist/tools/content.js';
import { publishTools, handlePublishTools } from '@sillyl12324/xhs-mcp/dist/tools/publish.js';
import { interactionTools, handleInteractionTools } from '@sillyl12324/xhs-mcp/dist/tools/interaction.js';
import { statsTools, handleStatsTools } from '@sillyl12324/xhs-mcp/dist/tools/stats.js';
import { downloadTools, handleDownloadTools } from '@sillyl12324/xhs-mcp/dist/tools/download.js';
import { draftTools, handleDraftTools } from '@sillyl12324/xhs-mcp/dist/tools/draft.js';
import { creatorTools, handleCreatorTools } from '@sillyl12324/xhs-mcp/dist/tools/creator.js';
import { notificationTools, handleNotificationTools } from '@sillyl12324/xhs-mcp/dist/tools/notification.js';
import { exploreTools, handleExploreTools } from '@sillyl12324/xhs-mcp/dist/tools/explore.js';

const port = parseInt(process.env.XHS_MCP_PORT || '18060', 10);

PUBLISH_SELECTORS.publishBtn = 'button.publishBtn, div.publish-page-publish-btn button.bg-red';

const db = await initDatabase();
const pool = getAccountPool(db);

const legacyPublishTool = {
  name: 'xhs_publish_content',
  description:
    'Legacy compatibility tool for publishing image/text notes. Preserves the older tool name expected by AIInSight.',
  inputSchema: {
    type: 'object',
    properties: {
      title: { type: 'string', description: 'Note title (max 20 characters)' },
      content: { type: 'string', description: 'Note content/description' },
      images: {
        type: 'array',
        items: { type: 'string' },
        description: 'Paths or URLs to image files',
      },
      tags: {
        type: 'array',
        items: { type: 'string' },
        description: 'Optional tags/topics for the note',
      },
      scheduleTime: {
        type: 'string',
        description: 'Optional scheduled publish time (ISO 8601 format)',
      },
      account: {
        type: 'string',
        description: 'Account name or ID to use for publishing',
      },
      accounts: {
        oneOf: [
          { type: 'array', items: { type: 'string' } },
          { type: 'string', enum: ['all'] },
        ],
        description: 'Multiple accounts to publish to (array of names/IDs, or "all")',
      },
    },
    required: ['title', 'content', 'images'],
  },
};

const allTools = [
  ...accountTools,
  ...authTools,
  ...contentTools,
  ...publishTools,
  ...interactionTools,
  ...statsTools,
  ...downloadTools,
  ...draftTools,
  ...creatorTools,
  ...notificationTools,
  ...exploreTools,
  legacyPublishTool,
];

/**
 * Post-publish verification: query creator center for the newly published note.
 * Returns the matched note object if found, or null.
 */
async function verifyPublishViaCreatorCenter(client, title, timeoutMs = 15000) {
  const VERIFY_WAIT_MS = 5000;
  console.error(`[publish-verify] Waiting ${VERIFY_WAIT_MS}ms for platform sync...`);
  await new Promise((r) => setTimeout(r, VERIFY_WAIT_MS));

  try {
    console.error('[publish-verify] Querying creator center for recent notes...');
    const notes = await client.getMyPublishedNotes(0, 10, timeoutMs);
    console.error(`[publish-verify] Got ${notes.length} notes from creator center`);

    if (!notes || notes.length === 0) return null;

    const publishWindowMs = 3 * 60 * 1000; // 3 min window
    const now = Date.now();

    for (const note of notes) {
      // Title must match exactly
      if (note.title !== title) continue;

      // Check publish time is within window (if available)
      if (note.time) {
        const noteTime = new Date(note.time).getTime();
        if (now - noteTime > publishWindowMs) continue;
      }

      console.error(`[publish-verify] Matched note: id=${note.id}, title=${note.title}`);
      return note;
    }

    console.error('[publish-verify] No matching note found in creator center');
    return null;
  } catch (err) {
    console.error('[publish-verify] Creator center query failed:', err?.message || err);
    return null;
  }
}

async function handleLegacyPublishTool(args) {
  const params = z
    .object({
      title: z.string().max(20),
      content: z.string(),
      images: z.array(z.string()).min(1),
      tags: z.array(z.string()).optional(),
      scheduleTime: z.string().optional(),
      account: z.string().optional(),
      accounts: z.union([z.array(z.string()), z.literal('all')]).optional(),
    })
    .parse(args ?? {});

  const multiParams = {
    account: params.account,
    accounts: params.accounts,
  };

  const results = await executeWithMultipleAccounts(
    pool,
    db,
    multiParams,
    'publish_content',
    async (ctx) => {
      const result = await ctx.client.publishContent({
        title: params.title,
        content: params.content,
        images: params.images,
        tags: params.tags,
        scheduleTime: params.scheduleTime,
      });

      if (!result.success) {
        return result;
      }

      // --- Verification gate ---
      // If upstream already gave us a noteId, trust it.
      if (result.noteId) {
        console.error(`[publish-verify] Upstream returned noteId=${result.noteId}, skipping verification`);
        db.published.record({
          accountId: ctx.accountId,
          noteId: result.noteId,
          title: params.title,
          content: params.content,
          noteType: 'image',
          images: params.images,
          tags: params.tags,
          status: params.scheduleTime ? 'scheduled' : 'published',
        });
        return {
          success: true,
          noteId: result.noteId,
          noteUrl: `https://www.xiaohongshu.com/explore/${result.noteId}`,
        };
      }

      // Upstream didn't return noteId (the common case due to upstream bug).
      // Verify via creator center.
      const matched = await verifyPublishViaCreatorCenter(ctx.client, params.title);

      if (matched && matched.id) {
        console.error(`[publish-verify] Verified! noteId=${matched.id}`);
        db.published.record({
          accountId: ctx.accountId,
          noteId: matched.id,
          title: params.title,
          content: params.content,
          noteType: 'image',
          images: params.images,
          tags: params.tags,
          status: params.scheduleTime ? 'scheduled' : 'published',
        });
        return {
          success: true,
          noteId: matched.id,
          noteUrl: `https://www.xiaohongshu.com/explore/${matched.id}`,
          verifiedVia: 'creator_center',
        };
      }

      // Verification failed — skip db record (can't confirm publish), return error
      console.error('[publish-verify] Verification failed — returning submitted_but_unverified');
      return {
        success: false,
        error: 'submitted_but_unverified',
        message: '发布动作已提交，但未在创作者中心确认到新笔记。请在小红书 App 中手动检查。',
      };
    },
    {
      logParams: { title: params.title, imageCount: params.images.length },
      sequential: true,
    },
  );

  if (results.length === 1) {
    const r = results[0];
    if (!r.success) {
      return {
        content: [{ type: 'text', text: JSON.stringify(r, null, 2) }],
        isError: true,
      };
    }
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(
            {
              account: r.account,
              success: true,
              noteId: r.result?.noteId,
              noteUrl: r.result?.noteUrl,
              verifiedVia: r.result?.verifiedVia,
              result: r.result,
            },
            null,
            2,
          ),
        },
      ],
    };
  }

  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(
          {
            results: results.map((r) => ({
              account: r.account,
              success: r.success,
              noteId: r.success ? r.result?.noteId : undefined,
              noteUrl: r.success ? r.result?.noteUrl : undefined,
              result: r.success ? r.result : undefined,
              error: r.error,
            })),
          },
          null,
          2,
        ),
      },
    ],
  };
}

function createCompatibleMcpServer() {
  const server = new Server(
    { name: 'xhs-mcp', version: '2.0.0' },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: allTools,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const { name, arguments: args } = request.params;

      if (name === 'xhs_publish_content') {
        return await handleLegacyPublishTool(args);
      }
      if (accountTools.some((t) => t.name === name)) {
        return await handleAccountTools(name, args, pool, db);
      }
      if (authTools.some((t) => t.name === name)) {
        return await handleAuthTools(name, args, pool, db);
      }
      if (contentTools.some((t) => t.name === name)) {
        return await handleContentTools(name, args, pool, db);
      }
      if (publishTools.some((t) => t.name === name)) {
        return await handlePublishTools(name, args, pool, db);
      }
      if (interactionTools.some((t) => t.name === name)) {
        return await handleInteractionTools(name, args, pool, db);
      }
      if (statsTools.some((t) => t.name === name)) {
        return await handleStatsTools(name, args, pool, db);
      }
      if (downloadTools.some((t) => t.name === name)) {
        return await handleDownloadTools(name, args, pool, db);
      }
      if (draftTools.some((t) => t.name === name)) {
        return await handleDraftTools(name, args, pool, db);
      }
      if (creatorTools.some((t) => t.name === name)) {
        return await handleCreatorTools(name, args, pool, db);
      }
      if (notificationTools.some((t) => t.name === name)) {
        return await handleNotificationTools(name, args, pool, db);
      }
      if (exploreTools.some((t) => t.name === name)) {
        return await handleExploreTools(name, args, pool, db);
      }

      throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    } catch (error) {
      if (error instanceof z.ZodError) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid arguments: ${error.message}`,
        );
      }
      throw error;
    }
  });

  return server;
}

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Expose-Headers', 'Mcp-Session-Id');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Mcp-Session-Id');
}

const httpServer = http.createServer(async (req, res) => {
  setCorsHeaders(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://localhost:${port}`);

  if (url.pathname === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', server: 'xhs-mcp', version: '2.0.0' }));
    return;
  }

  if (url.pathname === '/' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        name: 'xhs-mcp',
        version: '2.0.0',
        description: 'Xiaohongshu MCP Server (Node.js)',
        endpoints: { mcp: '/mcp', health: '/health' },
      }),
    );
    return;
  }

  if (url.pathname === '/mcp' && req.method === 'POST') {
    let transport;
    let mcpServer;
    try {
      transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      mcpServer = createCompatibleMcpServer();
      await mcpServer.connect(transport);

      const body = await new Promise((resolve, reject) => {
        const chunks = [];
        req.on('data', (chunk) => chunks.push(chunk));
        req.on('end', () => {
          try {
            resolve(JSON.parse(Buffer.concat(chunks).toString()));
          } catch (e) {
            reject(e);
          }
        });
        req.on('error', reject);
      });

      req.body = body;
      await transport.handleRequest(req, res, body);
    } catch (error) {
      console.error('MCP request error:', error);
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            jsonrpc: '2.0',
            error: { code: -32603, message: 'Internal server error' },
            id: null,
          }),
        );
      }
    } finally {
      if (transport) await transport.close().catch(() => {});
      if (mcpServer) await mcpServer.close().catch(() => {});
    }
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

const shutdown = async () => {
  console.error('Shutting down...');
  await pool.closeAll();
  db.close();
  httpServer.close();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

httpServer.listen(port, () => {
  console.error(`Starting HTTP server on port ${port}...`);
  console.error(`MCP endpoint: http://localhost:${port}/mcp`);
  console.error(`HTTP server running on http://localhost:${port}`);
});
