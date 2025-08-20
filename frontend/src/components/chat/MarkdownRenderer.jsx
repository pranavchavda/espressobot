import React, { useMemo, useEffect, useRef } from "react";
import MarkdownIt from "markdown-it";

import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';
import attrs from 'markdown-it-attrs';
import footnote from 'markdown-it-footnote';
import multimdTable from 'markdown-it-multimd-table';
import './MarkdownRenderer.css';

// Create MarkdownIt instance with plugins
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  // Treat single newlines as <br> to improve streaming readability
  breaks: true,
}).use(attrs).use(footnote).use(multimdTable, { multiline: true, rowspan: true, headerless: true });

// Custom plugin to add Tailwind classes to lists and tables
// DISABLED: This was causing styling issues as complex Tailwind classes weren't applying properly on first render
// md.core.ruler.push('add_tailwind_classes', (state) => {
//   state.tokens.forEach((token) => {
//     switch (token.type) {
//       case 'bullet_list_open':
//         token.attrJoin('class', 'list-disc pl-6 my-4 space-y-2');
//         break;
//       case 'ordered_list_open':
//         token.attrJoin('class', 'list-decimal pl-6 my-4 space-y-2');
//         break;
//       case 'list_item_open':
//         token.attrJoin('class', 'ml-1');
//         break;
//       case 'table_open':
//         token.attrJoin('class', 'min-w-full divide-y divide-zinc-200 dark:divide-zinc-700 border border-zinc-200 dark:border-zinc-700 rounded-lg');
//         break;
//       case 'thead_open':
//         token.attrJoin('class', 'bg-zinc-100 dark:bg-zinc-800');
//         break;
//       case 'tbody_open':
//         token.attrJoin('class', 'divide-y divide-zinc-200 dark:divide-zinc-700');
//         break;
//       case 'tr_open':
//         token.attrJoin('class', 'hover:bg-zinc-50 dark:hover:bg-zinc-800/70');
//         break;
//       case 'th_open':
//         token.attrJoin('class', 'px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider');
//         break;
//       case 'td_open':
//         token.attrJoin('class', 'px-4 py-3 text-sm text-zinc-800 dark:text-zinc-200');
//         break;
//       default:
//         break;
//     }
//   });
// });

const copyIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-clipboard"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>
`;

const copiedIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check"><path d="M20 6 9 17l-5-5"/></svg>
`;

// Debug flag helper: enable verbose logs when ?mdDebug=1 or localStorage.mdDebug === '1'
function isMdDebugEnabled() {
  try {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    const q = params.get('mdDebug');
    if (q === '1' || q === 'true') return true;
    const ls = window.localStorage?.getItem('mdDebug');
    if (ls === '1' || ls === 'true') return true;
  } catch {}
  return false;
}

const mdDebugLog = (...args) => {
  try {
    if (isMdDebugEnabled()) console.log(...args);
  } catch {}
};

// Decode escaped newlines (\n) and handle markdown two-space line breaks
// Many backends occasionally send mixed real and escaped newlines mid-stream.
// This is the most fundamental fix for compressed markdown.
function decodeEscapedNewlinesAndSpaces(input) {
  try {
    // First, handle the most basic case: convert literal \n strings to actual newlines
    let processed = input.replace(/\\n/g, '\n');
    
    // Handle Windows line endings
    processed = processed.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Handle markdown two-space line breaks (convert to actual newlines)
    processed = processed.replace(/  +\n/g, '\n');
    processed = processed.replace(/  +$/gm, '\n');
    
    // Now process line by line, being careful about code fences
    const lines = processed.split('\n');
    let inFence = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const fenceMatch = line.match(/^\s*(```|~~~)/);
      if (fenceMatch) {
        inFence = !inFence; // toggle on open/close fence
        continue;
      }
      if (!inFence) {
        // For very long lines (potential compressed markdown), try to split intelligently
        if (line.length > 200) {
          // Add newlines before common markdown patterns
          let longLine = line;
          longLine = longLine.replace(/(\S)\s+(#{1,6}\s)/g, '$1\n$2');  // Before headers
          longLine = longLine.replace(/(\S)\s+([*-]\s)/g, '$1\n$2');    // Before bullets
          longLine = longLine.replace(/(\S)\s+(\d+\.\s)/g, '$1\n$2');   // Before numbers
          longLine = longLine.replace(/(\S)\s+(```)/g, '$1\n$2');       // Before code
          
          // If still very long, split on sentence boundaries
          if (longLine.length > 400) {
            longLine = longLine.replace(/([.!?])\s+([A-Z])/g, '$1\n$2');
          }
          
          lines[i] = longLine;
        }
        
        // Handle escaped characters outside code fences
        lines[i] = lines[i].replace(/\\t/g, '\t');
      }
    }
    return lines.join('\n');
  } catch (e) {
    console.warn('[MarkdownRenderer] decodeEscapedNewlinesAndSpaces failed', e);
    return input;
  }
}

// If we have a potential markdown table header row at the end of the current input but
// no header separator line yet (---, :---, ---:, :---:), synthesize a temporary separator
// so the table renders immediately during streaming.
function synthesizeTableHeaderSeparatorForRender(input) {
  try {
    const lines = input.split('\n');
    let inFence = false;
    const isSep = (s) => /^\s*\|?\s*(:?-{3,}:?\s*\|\s*)+(:?-{3,}:?)\s*\|?\s*$/.test(s);
    const isRow = (s) => /^\s*\|.*\|.*$/.test(s);

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const fenceToggle = /^\s*(```+|~~~+)/.test(line);
      if (fenceToggle) { inFence = !inFence; continue; }
      if (inFence) continue;

      if (isRow(line)) {
        const next = lines[i + 1];
        if (next == null || (!isSep(next) && next.trim() !== '')) {
          // We only synthesize if either there is no next line yet, or the next line exists but isn't a separator
          // Count columns from header row
          const parts = line.split('|').map(s => s.trim()).filter(s => s.length > 0);
          const colCount = parts.length;
          if (colCount >= 2 && (next == null || !isSep(next))) {
            const sep = '|' + Array.from({ length: colCount }).map(() => ' --- ').join('|') + '|';
            // Insert after current line
            lines.splice(i + 1, 0, sep);
            // Skip over inserted line
            i++;
          }
        }
      }
    }
    return lines.join('\n');
  } catch (e) {
    console.warn('[MarkdownRenderer] synthesizeTableHeaderSeparatorForRender failed', e);
    return input;
  }
}

// Temporarily close an unbalanced fenced code block at end-of-input (for streaming display only).
// If the stream currently ends inside an open fence, we append a matching fence marker so
// markdown-it can parse the rest of the content correctly immediately. This does NOT mutate state.
function temporarilyCloseOpenFenceForRender(input) {
  try {
    const lines = input.split('\n');
    let inFence = false;
    let lastFenceMarker = null; // '```' or '~~~'
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const m = line.match(/^\s*(```+|~~~+)/);
      if (m) {
        const marker = m[1];
        const markerBase = marker[0] === '`' ? '```' : '~~~';
        // If the same marker also appears at end of trimmed line, treat as open+close on same line (net zero)
        const trimmed = line.trim();
        const closesSameLine = trimmed.length > marker.length && trimmed.endsWith(marker);
        if (!closesSameLine) {
          inFence = !inFence;
          lastFenceMarker = markerBase;
        }
      }
    }
    if (inFence && lastFenceMarker) {
      return input + (input.endsWith('\n') ? '' : '\n') + lastFenceMarker + '\n';
    }
    return input;
  } catch (e) {
    console.warn('[MarkdownRenderer] temporarilyCloseOpenFenceForRender failed', e);
    return input;
  }
}

// Ensure a single blank line before block-level constructs (headings, lists, quotes, fences, tables)
// but DO NOT insert blank lines between consecutive table rows.
function ensureBlankLinesBeforeBlocksOutsideCode(input) {
  try {
    const lines = input.split('\n');
    const out = [];
    let inFence = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const fenceToggle = /^\s*(```|~~~)/.test(line);
      if (fenceToggle) {
        inFence = !inFence;
        // Ensure fence starts on a new paragraph
        const prev = out[out.length - 1] || '';
        if (!inFence && prev.trim() !== '') {
          // closing fence - no need to force blank
        } else if (inFence && prev.trim() !== '') {
          out.push('');
        }
        out.push(line);
        continue;
      }

      if (!inFence) {
        const isHeading = /^\s*#{1,6}\s+/.test(line);
        const isBlockquote = /^\s*>\s+/.test(line);
        const isList = /^\s*(?:[-+*]\s+|\d+\.\s+)/.test(line);
        const isTable = /^\s*\|.*\|.*$/.test(line);

        const prev = out[out.length - 1] || '';
        const prevIsBlank = prev.trim() === '';
        const prevIsTable = /^\s*\|.*\|.*$/.test(prev);

        if ((isHeading || isBlockquote || isList) && !prevIsBlank) {
          out.push('');
        }
        if (isTable && !prevIsBlank && !prevIsTable) {
          out.push('');
        }
      }

      out.push(line);
    }
    return out.join('\n');
  } catch (e) {
    console.warn('[MarkdownRenderer] ensureBlankLinesBeforeBlocksOutsideCode failed', e);
    return input;
  }
}

// Split run-on markdown table rows that were emitted on a single visual line
// Example: "| A | B ||---|---|| 1 | 2 |" -> becomes three lines
function splitRunOnTableRowsOutsideCode(input) {
  try {
    const lines = input.split('\n');
    let inFence = false;
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      const fenceMatch = line.match(/^\s*(```|~~~)/);
      if (fenceMatch) {
        inFence = !inFence;
        continue;
      }
      if (!inFence) {
        const trimmed = line.trimStart();
        if (trimmed.startsWith('|') && /\|\s*\|\s*/.test(line)) {
          // Insert newlines between adjacent rows glued with a single pipe
          line = line.replace(/\|\s*\|\s*/g, '|\n|');
          lines[i] = line;
        }
      }
    }
    return lines.join('\n');
  } catch (e) {
    console.warn('[MarkdownRenderer] splitRunOnTableRowsOutsideCode failed', e);
    return input;
  }
}

// Insert a newline before block-level starters that appear mid-line (outside code fences).
// Handles patterns like: "... — ### Heading" or "in: | Item | Status |" so they render immediately.
function insertNewlineBeforeBlocksOutsideCode(input) {
  try {
    const lines = input.split('\n');
    let inFence = false;
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      const fenceMatch = line.match(/^\s*(```|~~~)/);
      if (fenceMatch) {
        inFence = !inFence;
        continue;
      }
      if (!inFence) {
        // Insert a hard newline before likely block starters when preceded by punctuation or dash
        // Starters: table row (|...|...), headings (#{1,6}), blockquote (>), lists (-,+,*, 1.) and code fences
        line = line.replace(/([.:;!?—–\-])\s+(?=(\|[^\n]*\|[^\n]*|#{1,6}\s+|>\s+|[-+*]\s+\S|\d+\.\s+\S|```|~~~))/g, '$1\n');

        // Also split when a heading token (#{1,6}) appears mid-line after any non-space char
        line = line.replace(/(\S)\s+(?=(#{1,6}\s+))/g, '$1\n');
        
        // Add newlines before headers that directly follow other content (no whitespace requirement)
        line = line.replace(/(\S)(#{1,6}\s)/g, '$1\n$2');
        
        // Add newlines before list items that directly follow other content
        line = line.replace(/(\S)([*-]\s)/g, '$1\n$2');
        line = line.replace(/(\S)(\d+\.\s)/g, '$1\n$2');
        
        // Add newlines before code blocks that directly follow other content
        line = line.replace(/(\S)(```)/g, '$1\n$2');

        // If a heading line contains a list starter after the heading text, split there too
        line = line.replace(/(#{1,6}\s+[^\n]+?)\s+((?:[-+*]\s+\S|\d+\.\s+\S))/g, '$1\n$2');

        // Split before list starters that appear after a letter or closing bracket/paren to avoid math like "10 - 5"
        line = line.replace(/([A-Za-z\]\)])\s+((?:[-+*]\s+\S|\d+\.\s+\S))/g, '$1\n$2');
        lines[i] = line;
      }
    }
    return lines.join('\n');
  } catch (e) {
    console.warn('[MarkdownRenderer] insertNewlineBeforeBlocksOutsideCode failed', e);
    return input;
  }
}

// Override the default fence renderer to add syntax highlighting and a copy button.
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const content = token.content.trim();
  const langInfo = token.info ? md.utils.unescapeAll(token.info).trim() : "";
  const langName = langInfo.split(/(\s+)/g)[0];

  const highlightedContent = langName && hljs.getLanguage(langName)
    ? hljs.highlight(content, { language: langName, ignoreIllegals: true }).value
    : md.utils.escapeHtml(content);

  const langClass = langName ? `language-${langName}` : '';

  return `
    <div class="code-block-wrapper my-6 rounded-lg border bg-zinc-950/70 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-1.5 bg-zinc-100/80 dark:bg-zinc-800/50 border-b border-zinc-200 dark:border-zinc-700/60">
        <span class="font-mono text-xs text-zinc-500">${langName || 'text'}</span>
        <button class="copy-btn flex items-center gap-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white transition-colors">
          ${copyIconSvg}
          <span>Copy</span>
        </button>
      </div>
      <pre class="m-0 p-4 overflow-x-auto"><code class="hljs ${langClass}">${highlightedContent}</code></pre>
    </div>
  `;
};

export const MarkdownRenderer = function MarkdownRenderer({
  children: rawMarkdownContent,
  className = "max-w-none not-prose",
}) {
  mdDebugLog('[MarkdownRenderer] Component called with content length:', rawMarkdownContent?.length);
  const containerRef = useRef(null);

  const processedMarkdown = useMemo(() => {
    if (typeof rawMarkdownContent !== "string") {
      mdDebugLog('[MarkdownRenderer] Content is not a string:', typeof rawMarkdownContent, rawMarkdownContent);
      return "";
    }
    mdDebugLog('[MarkdownRenderer] Processing markdown, length:', rawMarkdownContent.length);
    // Normalize newlines to help markdown-it close block constructs (tables, lists, fences)
    let normalized = rawMarkdownContent.replace(/\r\n?/g, "\n");
    // Always decode escaped newlines and two-space breaks (safe for markdown and tables)
    normalized = decodeEscapedNewlinesAndSpaces(normalized);

    // Insert newline before inline block starters so markdown can parse immediately
    normalized = insertNewlineBeforeBlocksOutsideCode(normalized);

    // If table rows were glued together, split them into separate lines
    normalized = splitRunOnTableRowsOutsideCode(normalized);

    // Heuristic repair: if a markdown table is run-on in one line, insert newlines between rows
    // Trigger only when there are no real newlines and the string looks like a table
    if (
      normalized.indexOf('\n') === -1 &&
      /^\s*\|/.test(normalized) &&
      /\|\s*\|\s*/.test(normalized)
    ) {
      normalized = normalized.replace(/\|\s*\|\s*/g, '|\n|');
    }

    // Ensure blank line separation before block-level constructs, but not between table rows
    normalized = ensureBlankLinesBeforeBlocksOutsideCode(normalized);

    // Ensure a trailing newline so final blocks are recognized at end-of-input during streaming
    if (!/\n\s*$/.test(normalized)) {
      normalized += "\n";
    }

    return normalized
      .replace(
        /<THINKING>/g,
        '<div class="mb-2 bg-zinc-200 dark:bg-zinc-800 p-2 rounded-lg shadow-sm"><span class="text-xs text-zinc-500 dark:text-zinc-400" data-custom-tag="thinking-block-start">🤔</span>',
      )
      .replace(/<\/THINKING>/g, "</div>");
  }, [rawMarkdownContent]);

  // Compute HTML directly from latest markdown to avoid memoization issues
  // Close any open fence temporarily at render time so streaming doesn't look like one big code block
  const displayMarkdown = synthesizeTableHeaderSeparatorForRender(
    temporarilyCloseOpenFenceForRender(processedMarkdown)
  );
  const renderedHtml = md.render(displayMarkdown);
  // Debug: peek at processed markdown and rendered HTML
  try {
    mdDebugLog('[MarkdownRenderer] processedMarkdown (first 200):', processedMarkdown.slice(0, 200).replace(/\n/g, '\\n'));
    mdDebugLog('[MarkdownRenderer] displayMarkdown (first 200):', displayMarkdown.slice(0, 200).replace(/\n/g, '\\n'));
    mdDebugLog('[MarkdownRenderer] renderedHtml (first 200):', renderedHtml.slice(0, 200).replace(/\n/g, '\\n'));
  } catch {}

  // Apply HTML directly to avoid any reconciliation edge-cases where dangerouslySetInnerHTML may not update immediately
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    try {
      container.innerHTML = renderedHtml;
      container.setAttribute('data-rendered-len', String(renderedHtml.length));
    } catch (e) {
      console.warn('[MarkdownRenderer] Failed to set innerHTML directly', e);
    }
  }, [renderedHtml]);

  // Debug: Check what's actually in the DOM after rendering
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    
    mdDebugLog('[MarkdownRenderer] DOM after render - innerHTML length:', container.innerHTML.length);
    mdDebugLog('[MarkdownRenderer] DOM after render - first 200 chars:', container.innerHTML.substring(0, 200));
    mdDebugLog('[MarkdownRenderer] DOM className:', container.className);
    
    // Check if we have proper HTML elements
    const paragraphs = container.querySelectorAll('p');
    const tables = container.querySelectorAll('table');
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    mdDebugLog('[MarkdownRenderer] Elements found - paragraphs:', paragraphs.length, 'tables:', tables.length, 'headings:', headings.length);
    
  }, [renderedHtml]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleCopyClick = (e) => {
      const copyButton = e.target.closest('.copy-btn');
      if (copyButton) {
        const wrapper = copyButton.closest(".code-block-wrapper");
        if (wrapper) {
          const code = wrapper.querySelector("code").innerText;
          navigator.clipboard.writeText(code);

          copyButton.innerHTML = `${copiedIconSvg} <span>Copied!</span>`;
          copyButton.disabled = true;
          
          setTimeout(() => {
            copyButton.innerHTML = `${copyIconSvg} <span>Copy</span>`;
            copyButton.disabled = false;
          }, 2000);
        }
      }
    };

    container.addEventListener("click", handleCopyClick);

    return () => {
      container.removeEventListener("click", handleCopyClick);
    };
  }, [renderedHtml]); // Rerun if html changes, to re-attach listeners to new DOM

  return (
    <div
      ref={containerRef}
      className={`markdown-content ${className}`}
      style={{
        lineHeight: '1.6',
        fontSize: '14px'
      }}
    />
  );
};
