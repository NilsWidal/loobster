import * as fs from 'fs';
import * as path from 'path';

interface ScaffoldResult {
  created: string[];
  skipped: string[];
}

const TEMPLATE_FILES = [
  'commands/research-codebase.md',
  'commands/make-proposals.md',
  'commands/make-plan.md',
  'commands/implement.md',
  'commands/review-code.md',
  'commands/reppit.md',
  'design_doc_template.md',
];

export async function scaffoldTemplates(
  workspaceRoot: string,
  extensionRoot: string
): Promise<ScaffoldResult> {
  const result: ScaffoldResult = { created: [], skipped: [] };
  const templateDir = path.join(extensionRoot, 'templates');
  const targetDir = path.join(workspaceRoot, '.claude');

  for (const file of TEMPLATE_FILES) {
    const src = path.join(templateDir, file);
    const dest = path.join(targetDir, file);

    if (fs.existsSync(dest)) {
      result.skipped.push(file);
      continue;
    }

    // Ensure directory exists
    const dir = path.dirname(dest);
    fs.mkdirSync(dir, { recursive: true });

    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
      result.created.push(file);
    }
  }

  return result;
}
