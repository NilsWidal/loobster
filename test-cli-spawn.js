#!/usr/bin/env node
/**
 * Diagnostic: test multiple claude -p spawn configurations.
 * Run from a FRESH terminal (not inside Cursor/Claude Code):
 *   node test-cli-spawn.js
 */
const { spawn, execFileSync } = require('child_process');

const claudePath = process.argv[2] || 'claude';

// Clean env — only essentials
const SAFE_KEYS = ['PATH', 'HOME', 'USER', 'SHELL', 'LANG', 'TMPDIR', 'NVM_DIR', 'NVM_BIN', 'NVM_INC'];
const clean = {};
for (const key of SAFE_KEYS) {
  if (process.env[key]) clean[key] = process.env[key];
}

// Also test with full env minus Claude vars
const stripped = { ...process.env };
delete stripped.CLAUDECODE;
delete stripped.CLAUDE_CODE_SSE_PORT;
delete stripped.CLAUDE_CODE_ENTRYPOINT;

console.log('=== Claude CLI Diagnostic ===');
console.log('Claude path:', claudePath);

// Check version
try {
  const version = execFileSync(claudePath, ['--version'], { env: clean, timeout: 5000 }).toString().trim();
  console.log('Version:', version);
} catch (e) {
  console.log('ERROR: Cannot get version:', e.message);
}

// Check auth
try {
  const auth = execFileSync(claudePath, ['auth', 'status'], { env: clean, timeout: 5000 }).toString().trim();
  console.log('Auth status:', auth);
} catch (e) {
  console.log('Auth check failed:', e.message);
}

console.log('\nInherited CLAUDE* vars:', Object.keys(process.env).filter(k => k.startsWith('CLAUDE')).join(', ') || '(none)');
console.log('Inherited VSCODE* vars:', Object.keys(process.env).filter(k => k.startsWith('VSCODE')).join(', ') || '(none)');
console.log('');

const tests = [
  {
    name: 'A: clean env + stream-json + no-chrome',
    args: ['--output-format', 'stream-json', '--no-chrome', '-p', 'Respond with just the word OK'],
    env: clean,
  },
  {
    name: 'B: clean env + stream-json + no-chrome + acceptEdits',
    args: ['--output-format', 'stream-json', '--no-chrome', '--permission-mode', 'acceptEdits', '-p', 'Respond with just the word OK'],
    env: clean,
  },
  {
    name: 'C: clean env + text output + no-chrome',
    args: ['--output-format', 'text', '--no-chrome', '-p', 'Respond with just the word OK'],
    env: clean,
  },
  {
    name: 'D: stripped env (full minus CLAUDE*) + stream-json + no-chrome',
    args: ['--output-format', 'stream-json', '--no-chrome', '-p', 'Respond with just the word OK'],
    env: stripped,
  },
  {
    name: 'E: clean env + json output + no-chrome',
    args: ['--output-format', 'json', '--no-chrome', '-p', 'Respond with just the word OK'],
    env: clean,
  },
];

let testIndex = 0;

function runNext() {
  if (testIndex >= tests.length) {
    console.log('\n=== All tests complete ===');
    process.exit(0);
    return;
  }

  const test = tests[testIndex++];
  console.log(`--- Test ${test.name} ---`);

  const child = spawn(claudePath, test.args, {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: test.env,
  });

  let stdout = '';
  let stderr = '';
  let gotOutput = false;
  const startTime = Date.now();

  child.stdout.on('data', (chunk) => {
    gotOutput = true;
    stdout += chunk.toString();
  });

  child.stderr.on('data', (chunk) => {
    gotOutput = true;
    stderr += chunk.toString();
  });

  const timeout = setTimeout(() => {
    if (!gotOutput) {
      console.log(`  TIMEOUT: No output after 20s — killing`);
      // Check if process is still alive
      try {
        process.kill(child.pid, 0); // signal 0 = check if alive
        console.log(`  Process ${child.pid} is still alive (hanging)`);
      } catch {
        console.log(`  Process ${child.pid} already dead`);
      }
    }
    child.kill('SIGTERM');
  }, 20000);

  child.on('close', (code, signal) => {
    clearTimeout(timeout);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`  PID: ${child.pid}, Exit: code=${code} signal=${signal}, Time: ${elapsed}s`);
    if (stdout) console.log(`  STDOUT (${stdout.length} chars): ${stdout.substring(0, 200)}`);
    if (stderr) console.log(`  STDERR (${stderr.length} chars): ${stderr.substring(0, 200)}`);
    if (!stdout && !stderr) console.log(`  NO OUTPUT AT ALL`);
    console.log('');
    runNext();
  });

  child.on('error', (err) => {
    clearTimeout(timeout);
    console.log(`  SPAWN ERROR: ${err.message}`);
    console.log('');
    runNext();
  });
}

runNext();
