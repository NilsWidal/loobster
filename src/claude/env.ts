/** Env var whitelist safe for spawning Claude CLI from the extension host. */
const SAFE_ENV_KEYS = [
  'PATH', 'HOME', 'USER', 'SHELL', 'LANG', 'LC_ALL', 'LC_CTYPE',
  'TERM', 'TMPDIR', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME',
  'SSH_AUTH_SOCK', 'SSH_AGENT_PID',
  'ANTHROPIC_API_KEY', 'CLAUDE_API_KEY',
  'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY',
  'http_proxy', 'https_proxy', 'no_proxy',
  'NVM_DIR', 'NVM_BIN', 'NVM_INC',
];

/**
 * Build a clean env with only essential vars.
 * The extension host inherits many vars from Cursor/IDE
 * (CLAUDECODE, CLAUDE_CODE_SSE_PORT, VSCODE_*, ELECTRON_*,
 * NODE_OPTIONS, etc.) that interfere with a fresh CLI spawn.
 */
export function buildCleanEnv(): Record<string, string> {
  const clean: Record<string, string> = {};
  for (const key of SAFE_ENV_KEYS) {
    if (process.env[key]) {
      clean[key] = process.env[key]!;
    }
  }
  return clean;
}
