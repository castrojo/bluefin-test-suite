import Converter from 'ansi-to-html';

const converter = new Converter({
  fg: 'var(--terminal-fg, #e2e8f0)',
  bg: 'var(--terminal-bg, #0f172a)',
  newline: true,
  escapeXML: true,
  stream: false,
  colors: {
    0: 'var(--terminal-black, #1e293b)',
    1: 'var(--terminal-red, #f43f5e)',
    2: 'var(--terminal-green, #10b981)',
    3: 'var(--terminal-yellow, #f59e0b)',
    4: 'var(--terminal-blue, #3b82f6)',
    5: 'var(--terminal-magenta, #d946ef)',
    6: 'var(--terminal-cyan, #06b6d4)',
    7: 'var(--terminal-white, #f8fafc)'
  }
});

/**
 * Converts a raw terminal log string with ANSI escape codes into styled, safe HTML.
 * @param {string} rawLogs - Raw log data.
 * @returns {string} Fully rendered HTML.
 */
export function parseAnsiToHtml(rawLogs) {
  if (!rawLogs) return '';
  return converter.toHtml(rawLogs);
}