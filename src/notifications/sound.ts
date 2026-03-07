import { exec } from 'child_process';
import * as os from 'os';

export function playGateSound(): void {
  playSound('/System/Library/Sounds/Glass.aiff');
}

export function playCompletionSound(): void {
  playSound('/System/Library/Sounds/Hero.aiff');
}

function playSound(macPath: string): void {
  const platform = os.platform();

  if (platform === 'darwin') {
    exec(`afplay "${macPath}" &`);
  } else if (platform === 'win32') {
    // Windows: use PowerShell to play a system sound
    exec(
      `powershell -c "(New-Object Media.SoundPlayer 'C:\\Windows\\Media\\notify.wav').PlaySync()"`
    );
  } else {
    // Linux: terminal bell as fallback
    exec("printf '\\a'");
  }
}
