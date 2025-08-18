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
  console.log('[MarkdownRenderer] Component called with content length:', rawMarkdownContent?.length);
  const containerRef = useRef(null);

  const processedMarkdown = useMemo(() => {
    if (typeof rawMarkdownContent !== "string") {
      console.log('[MarkdownRenderer] Content is not a string:', typeof rawMarkdownContent, rawMarkdownContent);
      return "";
    }
    console.log('[MarkdownRenderer] Processing markdown, length:', rawMarkdownContent.length);
    // Normalize newlines to help markdown-it close block constructs (tables, lists, fences)
    let normalized = rawMarkdownContent.replace(/\r\n?/g, "\n");

    // If content has no real newlines but has escaped \n sequences, decode them
    if (normalized.indexOf('\n') === -1 && normalized.includes('\\n')) {
      normalized = normalized.replace(/\\n/g, '\n');
    }

    // Heuristic repair: if a markdown table is run-on in one line, insert newlines between rows
    // Trigger only when there are no real newlines and the string looks like a table
    if (
      normalized.indexOf('\n') === -1 &&
      /^\s*\|/.test(normalized) &&
      /\|\s*\|\s*/.test(normalized)
    ) {
      normalized = normalized.replace(/\|\s*\|\s*/g, '|\n|');
    }

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
  const renderedHtml = md.render(processedMarkdown);

  // Debug: Check what's actually in the DOM after rendering
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    
    console.log('[MarkdownRenderer] DOM after render - innerHTML length:', container.innerHTML.length);
    console.log('[MarkdownRenderer] DOM after render - first 200 chars:', container.innerHTML.substring(0, 200));
    console.log('[MarkdownRenderer] DOM className:', container.className);
    
    // Check if we have proper HTML elements
    const paragraphs = container.querySelectorAll('p');
    const tables = container.querySelectorAll('table');
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    console.log('[MarkdownRenderer] Elements found - paragraphs:', paragraphs.length, 'tables:', tables.length, 'headings:', headings.length);
    
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
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
};
