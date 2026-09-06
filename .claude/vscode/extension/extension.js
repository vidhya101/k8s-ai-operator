// DevOps Hive · VS Code Context Publisher
//
// Watches for file switches / selection changes / workspace changes and writes
// the current IDE state to ~/DevOpsHive/state/vscode-context.md so any agent
// (Claude Code, Munder-spawned peer, an Obsidian reader) can Read that one
// file to know what you're looking at right now.
//
// Zero external deps — only `vscode` API + Node built-ins, so no `npm install`
// step at load time. Fails silent on every write path: publishing your context
// must NEVER crash the IDE.
'use strict';

const vscode = require('vscode');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const DEFAULT_PATH = path.join(os.homedir(), 'DevOpsHive', 'state', 'vscode-context.md');
const MAX_SEL_BYTES = 2000; // truncate selection text

let debounceTimer = null;

/** Read the effective config each call — the user may change it live. */
function config() {
  const c = vscode.workspace.getConfiguration('devopsHive');
  const out = c.get('contextPath', '');
  return {
    outPath: out && typeof out === 'string' ? out : DEFAULT_PATH,
    debounceMs: c.get('debounceMs', 500),
    includeSelection: c.get('includeSelection', true),
  };
}

function activate(context) {
  // Ensure the state dir exists; if we can't create it, log and bail. We do
  // not throw — a broken publish target must not crash IDE startup.
  try {
    fs.mkdirSync(path.dirname(config().outPath), { recursive: true });
  } catch (e) {
    console.error('[devops-hive] cannot create context dir:', e && e.message);
  }

  // Publish on activation so the file reflects reality the moment VS Code opens.
  publish();

  // Any of these events warrants a fresh publish. Debounced so rapid changes
  // (typing → selection updates every keystroke) coalesce.
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(schedulePublish),
    vscode.window.onDidChangeTextEditorSelection(schedulePublish),
    vscode.workspace.onDidChangeWorkspaceFolders(schedulePublish),
    vscode.workspace.onDidOpenTextDocument(schedulePublish),
    vscode.workspace.onDidCloseTextDocument(schedulePublish),

    // Manual triggers — useful for testing + for the command palette.
    vscode.commands.registerCommand('devopsHive.publishContextNow', publish),
    vscode.commands.registerCommand('devopsHive.openContextFile', openContextFile),
  );
}

function schedulePublish() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(publish, config().debounceMs);
}

function publish() {
  try {
    const cfg = config();
    const editor = vscode.window.activeTextEditor;
    const activeFile = editor && editor.document.uri.scheme === 'file'
      ? editor.document.uri.fsPath
      : null;

    const workspaceRoots = (vscode.workspace.workspaceFolders || [])
      .map((f) => f.uri.fsPath);

    // Only real files on disk — skip untitled, output panes, etc.
    const openFiles = vscode.workspace.textDocuments
      .filter((d) => d.uri.scheme === 'file')
      .map((d) => d.uri.fsPath);

    // Selection (start/end line & column, plus a truncated text preview).
    let selectionMeta = null;
    let selectionText = '';
    if (cfg.includeSelection && editor && !editor.selection.isEmpty) {
      const s = editor.selection;
      selectionMeta = {
        start_line: s.start.line + 1,
        end_line: s.end.line + 1,
        start_col: s.start.character + 1,
        end_col: s.end.character + 1,
      };
      const raw = editor.document.getText(s);
      selectionText = raw.length > MAX_SEL_BYTES
        ? raw.slice(0, MAX_SEL_BYTES) + `\n… (truncated: +${raw.length - MAX_SEL_BYTES} chars)`
        : raw;
    }

    const language = editor && editor.document ? editor.document.languageId : '';
    const dirty = editor && editor.document ? editor.document.isDirty : false;

    const now = new Date().toISOString();

    // Frontmatter — Obsidian's dataview + our obsidian-sync read these fields.
    const fm = [
      '---',
      'type: vscode-context',
      `active_file: ${jsonOrNull(activeFile)}`,
      `active_language: ${JSON.stringify(language || '')}`,
      `active_dirty: ${dirty}`,
      `open_files_count: ${openFiles.length}`,
      `workspace_folders: [${workspaceRoots.map((w) => JSON.stringify(w)).join(', ')}]`,
      'selection:',
      selectionMeta
        ? `  lines: [${selectionMeta.start_line}, ${selectionMeta.end_line}]`
        : '  null',
      `updated_at: ${now}`,
      '---',
      '',
    ];

    const body = [
      '# VS Code — current context',
      '',
      `**Active file:** \`${activeFile || '(none)'}\`  \n`,
      `**Language:** \`${language || '?'}\`   **Dirty:** ${dirty}`,
      '',
      '## Workspace roots',
      '',
      workspaceRoots.length
        ? workspaceRoots.map((w) => `- \`${w}\``).join('\n')
        : '_(no workspace folders open)_',
      '',
      '## Open tabs',
      '',
      openFiles.length
        ? openFiles.slice(0, 40).map((f) => `- \`${f}\``).join('\n')
          + (openFiles.length > 40 ? `\n- _(+${openFiles.length - 40} more)_` : '')
        : '_(no file tabs open)_',
      '',
    ];

    if (selectionText) {
      body.push(
        '## Current selection',
        '',
        '```' + (language || ''),
        selectionText,
        '```',
        '',
      );
    }

    const content = fm.concat(body).join('\n');

    // Atomic write via tmp + rename so a partial write never lands.
    const tmp = cfg.outPath + '.tmp';
    fs.writeFileSync(tmp, content, 'utf8');
    fs.renameSync(tmp, cfg.outPath);
  } catch (e) {
    console.error('[devops-hive] publish error:', e && e.message);
  }
}

function openContextFile() {
  const p = config().outPath;
  vscode.workspace.openTextDocument(p).then((doc) => vscode.window.showTextDocument(doc));
}

function jsonOrNull(v) {
  return v == null ? 'null' : JSON.stringify(v);
}

function deactivate() {
  if (debounceTimer) clearTimeout(debounceTimer);
}

module.exports = { activate, deactivate };
