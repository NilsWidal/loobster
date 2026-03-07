import { execFile } from 'child_process';

/**
 * Detect whether the Claude CLI has Linear MCP tools available.
 * Runs `claude mcp list` and checks for a "linear" server.
 */
export function detectLinearMcp(claudePath: string): Promise<boolean> {
  return new Promise((resolve) => {
    execFile(claudePath, ['mcp', 'list'], { timeout: 5000 }, (err, stdout) => {
      if (err) {
        resolve(false);
        return;
      }
      // Look for "linear" in the MCP server list
      resolve(stdout.toLowerCase().includes('linear'));
    });
  });
}
