import { execFile } from 'child_process';
import { buildCleanEnv } from './env';

export interface ReppitTask {
  id: string;
  title: string;
  status: string; // 'open' | 'in_progress' | 'completed'
}

export interface TaskPollResult {
  tasks: ReppitTask[];
  total: number;
  completed: number;
}

/**
 * Poll Claude Code tasks by spawning a CLI query.
 * Used when taskMode is 'poll'. Returns gracefully on failure.
 */
export function pollTasks(claudePath: string, cwd?: string): Promise<TaskPollResult> {
  const empty: TaskPollResult = { tasks: [], total: 0, completed: 0 };

  return new Promise((resolve) => {
    const args = [
      '--dangerously-skip-permissions',
      '--output-format', 'json',
      '--no-chrome',
      '-p', 'Use TaskList to list all current tasks. Output ONLY a JSON array of objects with fields: id, title, status. No other text.',
    ];

    execFile(claudePath, args, {
      cwd,
      env: buildCleanEnv(),
      timeout: 15_000,
    }, (err, stdout) => {
      if (err) {
        resolve(empty);
        return;
      }

      try {
        const parsed = JSON.parse(stdout.trim());
        // CLI json output wraps result in { result: "..." }
        const text = typeof parsed === 'string' ? parsed : parsed.result || stdout;
        const tasks = extractTasks(typeof text === 'string' ? text : JSON.stringify(text));
        resolve({
          tasks,
          total: tasks.length,
          completed: tasks.filter(t => t.status === 'completed').length,
        });
      } catch {
        resolve(empty);
      }
    });
  });
}

/** Try to extract task data from CLI output (JSON array or embedded in text). */
function extractTasks(text: string): ReppitTask[] {
  // Try direct JSON array parse
  try {
    const arr = JSON.parse(text);
    if (Array.isArray(arr)) {
      return arr
        .filter((t: any) => t && (t.title || t.id))
        .map((t: any) => ({
          id: String(t.id || t.title || ''),
          title: String(t.title || t.id || ''),
          status: String(t.status || 'open'),
        }));
    }
  } catch {
    // Not a JSON array
  }

  // Try to find a JSON array embedded in the text
  const match = text.match(/\[[\s\S]*?\]/);
  if (match) {
    try {
      const arr = JSON.parse(match[0]);
      if (Array.isArray(arr)) {
        return arr
          .filter((t: any) => t && (t.title || t.id))
          .map((t: any) => ({
            id: String(t.id || t.title || ''),
            title: String(t.title || t.id || ''),
            status: String(t.status || 'open'),
          }));
      }
    } catch {
      // Embedded JSON parse failed
    }
  }

  return [];
}
