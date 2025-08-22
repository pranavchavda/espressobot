import React, { useMemo, useEffect, useRef } from "react";
import MarkdownIt from "markdown-it";

import hljs from "highlight.js";
import "highlight.js/styles/atom-one-dark.css";
import attrs from "markdown-it-attrs";
import footnote from "markdown-it-footnote";
import multimdTable from "markdown-it-multimd-table";
import "./MarkdownRenderer.css";

// Create MarkdownIt instance with plugins
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  // Treat single newlines as <br> to improve streaming readability
  breaks: false,
})
  .use(attrs)
  .use(footnote)
  .use(multimdTable, { multiline: true, rowspan: true, headerless: true });

// Configure syntax highlighting
md.options.highlight = function (str, lang) {
  if (lang && hljs.getLanguage(lang)) {
    try {
      const highlighted = hljs.highlight(str, { language: lang });
      const copyBtn = `<button class="copy-btn absolute top-2 right-2 px-2 py-1 text-xs bg-zinc-700 hover:bg-zinc-600 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">${copyIconSvg} <span>Copy</span></button>`;
      return `<div class="code-block-wrapper relative group"><pre class="hljs language-${lang} bg-zinc-900 text-zinc-100 p-4 rounded-lg overflow-x-auto text-sm"><code class="hljs language-${lang}">${highlighted.value}</code></pre>${copyBtn}</div>`;
    } catch (__) {}
  }

  // Fallback for unknown languages or highlighting failures
  const escaped = md.utils.escapeHtml(str);
  const copyBtn = `<button class="copy-btn absolute top-2 right-2 px-2 py-1 text-xs bg-zinc-700 hover:bg-zinc-600 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">${copyIconSvg} <span>Copy</span></button>`;
  return `<div class="code-block-wrapper relative group"><pre class="hljs bg-zinc-900 text-zinc-100 p-4 rounded-lg overflow-x-auto text-sm"><code>${escaped}</code></pre>${copyBtn}</div>`;
};

const copyIconSvg = `<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>`;

const copiedIconSvg = `<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;

// Debug helper function
function isMdDebugEnabled() {
  try {
    return (
      typeof window !== "undefined" &&
      (window.location.search.includes("md_debug=true") ||
        localStorage.getItem("md_debug") === "true")
    );
  } catch {
    return false;
  }
}

const mdDebugLog = (...args) => {
  if (isMdDebugEnabled()) {
    console.log("[MD_DEBUG]", ...args);
  }
};

// Simple function to temporarily close open fence for render (keep this as it's useful for streaming)
function temporarilyCloseOpenFenceForRender(input) {
  try {
    const lines = input.split("\n");
    let fenceCount = 0;
    let lastFenceIndex = -1;

    for (let i = 0; i < lines.length; i++) {
      if (/^\s*(```|~~~)/.test(lines[i])) {
        fenceCount++;
        lastFenceIndex = i;
      }
    }

    // If odd fence count, temporarily close the last one
    if (fenceCount % 2 !== 0 && lastFenceIndex >= 0) {
      const lastFenceLine = lines[lastFenceIndex];
      const fenceType = lastFenceLine.includes("```") ? "```" : "~~~";
      return input + "\n" + fenceType;
    }

    return input;
  } catch (e) {
    console.warn(
      "[MarkdownRenderer] temporarilyCloseOpenFenceForRender failed",
      e,
    );
    return input;
  }
}

// Simple function to add table header separators (keep this as it's useful for tables)
function synthesizeTableHeaderSeparatorForRender(input) {
  try {
    const lines = input.split("\n");
    const out = [];
    let inFence = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const fenceToggle = /^\s*(```|~~~)/.test(line);
      if (fenceToggle) {
        inFence = !inFence;
        out.push(line);
        continue;
      }

      if (!inFence && /^\s*\|.*\|/.test(line)) {
        const nextLine = i + 1 < lines.length ? lines[i + 1] : "";
        const isNextLineHeader = /^\s*\|[\s:|-]*\|/.test(nextLine);

        if (!isNextLineHeader) {
          const cells = line.split("|").length - 1;
          if (cells > 0) {
            out.push(line);
            out.push("|" + " --- |".repeat(cells));
            continue;
          }
        }
      }

      out.push(line);
    }

    return out.join("\n");
  } catch (e) {
    console.warn(
      "[MarkdownRenderer] synthesizeTableHeaderSeparatorForRender failed",
      e,
    );
    return input;
  }
}

export const MarkdownRenderer = function MarkdownRenderer({
  children: rawMarkdownContent,
  className = "max-w-none not-prose",
}) {
  mdDebugLog(
    "[MarkdownRenderer] Component called with content length:",
    rawMarkdownContent?.length,
  );
  const containerRef = useRef(null);

  const processedMarkdown = useMemo(() => {
    if (typeof rawMarkdownContent !== "string") {
      mdDebugLog(
        "[MarkdownRenderer] Content is not a string:",
        typeof rawMarkdownContent,
        rawMarkdownContent,
      );
      return "";
    }

    mdDebugLog(
      "[MarkdownRenderer] Processing markdown, length:",
      rawMarkdownContent.length,
    );

    // Simple normalization - just handle line endings
    let normalized = rawMarkdownContent.replace(/\r\n?/g, "\n");

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

  // Compute HTML directly from latest markdown
  // Keep the helpful functions for streaming and table rendering
  const displayMarkdown = synthesizeTableHeaderSeparatorForRender(
    temporarilyCloseOpenFenceForRender(processedMarkdown),
  );
  const renderedHtml = md.render(displayMarkdown);

  // Debug logging
  try {
    mdDebugLog(
      "[MarkdownRenderer] processedMarkdown (first 200):",
      processedMarkdown.slice(0, 200).replace(/\n/g, "\\n"),
    );
    mdDebugLog(
      "[MarkdownRenderer] displayMarkdown (first 200):",
      displayMarkdown.slice(0, 200).replace(/\n/g, "\\n"),
    );
    mdDebugLog(
      "[MarkdownRenderer] renderedHtml (first 200):",
      renderedHtml.slice(0, 200).replace(/\n/g, "\\n"),
    );
  } catch {}

  // Apply HTML directly to avoid reconciliation issues
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    try {
      container.innerHTML = renderedHtml;
      container.setAttribute("data-rendered-len", String(renderedHtml.length));
    } catch (e) {
      console.warn("[MarkdownRenderer] Failed to set innerHTML directly", e);
    }
  }, [renderedHtml]);

  // Copy button functionality
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleCopyClick = (e) => {
      const copyButton = e.target.closest(".copy-btn");
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
  }, [renderedHtml]);

  return (
    <div
      ref={containerRef}
      className={`markdown-content ${className}`}
      style={{
        lineHeight: "1.6",
        fontSize: "14px",
      }}
    />
  );
};
