import React, { useRef, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
// import rehypeSanitize from 'rehype-sanitize';

import clsx from "clsx";
import { Button } from "../../components/common/button";
import { Text, Code } from "../../components/common/text";

const SimpleCodeBlock = React.memo(({ language, children }) => {
  const codeRef = useRef(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (codeRef.current && children) {
      navigator.clipboard.writeText(String(children));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      ref={codeRef}
      className="relative my-5 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700"
    >
      <div className="flex justify-between items-center bg-zinc-200 dark:bg-zinc-800 px-4 py-2 text-xs text-zinc-800 dark:text-zinc-200">
        <span className="font-mono font-medium">{language}</span>
        <Button
          plain
          onClick={handleCopy}
          className={`text-xs px-3 py-1 rounded transition-colors ${
            copied
              ? "bg-green-100 text-green-800 dark:bg-green-800/30 dark:text-green-300"
              : "bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600"
          }`}
        >
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <Code>
        {String(children).replace(/\n$/, "")}
      </Code>
    </div>
  );
});

export const MarkdownRenderer = React.memo(function MarkdownRenderer({
  children: rawMarkdownContent,
  className = "",
}) {
  let processedMarkdown = rawMarkdownContent;
  if (typeof rawMarkdownContent === "string") {
    processedMarkdown = rawMarkdownContent
      .replace(
        /<THINKING>/g,
        '<div class="mb-2 bg-zinc-200 dark:bg-zinc-800 p-2 rounded-lg shadow-sm"><span class="text-xs text-zinc-500 dark:text-zinc-400" data-custom-tag="thinking-block-start">🤔',
      )
      .replace(/<\/THINKING>/g, "💭</span></div>");
  }
  console.log(
    "MarkdownRenderer processedMarkdown for ReactMarkdown:",
    processedMarkdown,
  );
  console.log("Type of processedMarkdown:", typeof processedMarkdown);
  const components = useMemo(
    () => ({
      // Headings
      h1: ({ node, children, ...props }) => (
        <Text
          as="h1"
          className="text-2xl font-bold mt-6 mb-4 text-zinc-900 dark:text-zinc-100"
          {...props}
        >
          {children}
        </Text>
      ),
      h2: ({ node, children, ...props }) => (
        <Text
          as="h2"
          className="text-xl font-bold mt-5 mb-3 text-zinc-900 dark:text-zinc-100"
          {...props}
        >
          {children}
        </Text>
      ),
      h3: ({ node, children, ...props }) => (
        <Text
          as="h3"
          className="text-lg font-bold mt-4 mb-2 text-zinc-900 dark:text-zinc-100"
          {...props}
        >
          {children}
        </Text>
      ),
      // Paragraphs
      p: ({ node, children, ...props }) => {
        const pRendererClassName =
          "text-base leading-relaxed my-3 whitespace-pre-wrap text-zinc-800 dark:text-zinc-200";
        // Base classes that were inside Text component for p tags
        const textComponentBaseClassName =
          "text-base/6 text-zinc-500 sm:text-sm/6 dark:text-zinc-400";
        const combinedClassName = clsx(
          pRendererClassName,
          textComponentBaseClassName,
        );

        // Directly render a <p> tag, bypassing the Text component for this case.
        // {...props} are props from ReactMarkdown for the p element (like node, sourcePosition),
        // and 'children' is the content.
        return (
          <p {...props} className={combinedClassName}>
            {children}
          </p>
        );
      },
      // Lists - renderWithThinkingBlocks is applied to <li> elements
      ul: ({ node, children, ...props }) => (
        <ul
          className="list-disc pl-6 my-4 space-y-2 text-zinc-800 dark:text-zinc-200"
          {...props}
        >
          {children}
        </ul>
      ),
      ol: ({ node, children, ...props }) => (
        <ol
          className="list-decimal pl-6 my-4 space-y-2 text-zinc-800 dark:text-zinc-200"
          {...props}
        >
          {children}
        </ol>
      ),
      li: ({ node, children, ...props }) => (
        <li className="ml-2" {...props}>
          {children}
        </li>
      ),
      // Blockquotes
      blockquote: ({ node, children, ...props }) => (
        <blockquote
          className="border-l-4 border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 pl-4 py-2 my-4 text-zinc-700 dark:text-zinc-300 italic rounded-r"
          {...props}
        >
          {children}
        </blockquote>
      ),
      // Links - children of <a> are processed if they are text nodes.
      a: ({ node, children, ...props }) => (
        <a
          className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      ),
      // Tables - content within <th> and <td> will be handled by their own renderers if they were customized
      // For now, assuming table cell content is primarily text or simple inline elements not needing deep <THINKING> recursion.
      // If <THINKING> tags are expected within table cells, th and td renderers would also need renderWithThinkingBlocks.
      table: ({ node, children, ...props }) => (
        <div className="overflow-x-auto my-6">
          <table
            className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-700 border border-zinc-200 dark:border-zinc-700 rounded-lg"
            {...props}
          >
            {children}
          </table>
        </div>
      ),
      thead: ({ node, children, ...props }) => (
        <thead className="bg-zinc-100 dark:bg-zinc-800" {...props}>
          {children}
        </thead>
      ),
      tbody: ({ node, children, ...props }) => (
        <tbody
          className="divide-y divide-zinc-200 dark:divide-zinc-700"
          {...props}
        >
          {children}
        </tbody>
      ),
      tr: ({ node, children, ...props }) => (
        <tr className="hover:bg-zinc-50 dark:hover:bg-zinc-800/70" {...props}>
          {children}
        </tr>
      ),
      th: ({ node, children, ...props }) => (
        <th
          className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({ node, children, ...props }) => (
        <td
          className="px-4 py-3 text-sm text-zinc-800 dark:text-zinc-200"
          {...props}
        >
          {children}
        </td>
      ),
      // Code blocks and inline code
      code({ node, inline, className, children, ...props }) {
        console.log("MarkdownRenderer 'code' component renderer:", {
          inline,
          className,
          children: String(children).substring(0, 100),
          nodeType: node.type,
          tagName: node.tagName,
          parentNode: node.parent ? node.parent.tagName : 'no parent',
        });

        const match = /language-(\w+)/.exec(className || "");
        const language = match ? match[1] : "text";

        // Determine if it's truly inline
        const isExplicitlyInline = inline === true;
        // If inline is undefined, and there's no language class (like language-js for blocks),
        // it's highly likely intended as inline code, especially if `node.parent` is unreliable.
        const isHeuristicallyInline = inline === undefined && !className;

        if (isExplicitlyInline || isHeuristicallyInline) {
          return (
            <Code
            > {/* Pass className for styling if present */}
              {children}
            </Code>
          );
        }
        
        // Otherwise, it's a block code.
        // This covers: 
        //   - inline === false (fenced code blocks from Markdown)
        //   - inline === undefined AND parent IS <pre> (raw HTML code block)
        return (
          <SimpleCodeBlock language={language}>
            {String(children).replace(/\n$/, "")}
          </SimpleCodeBlock>
        );
      },
      // Images
      img: ({ node, ...props }) => (
        <div className="my-4">
          <img
            className="max-w-full rounded-lg shadow-md"
            {...props}
            alt={props.alt || ""}
            loading="lazy"
          />
          {props.title && (
            <p className="text-center text-sm mt-2 text-zinc-500 dark:text-zinc-400 italic">
              {props.title}
            </p>
          )}
        </div>
      ),
      // Task lists (checkboxes)
      input: ({ node, ...props }) => (
        <input
          className="mr-1 h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-700"
          type="checkbox"
          readOnly
          {...props}
        />
      ),
      // Strikethrough
      del: ({ node, children, ...props }) => (
        <del
          className="line-through text-zinc-500 dark:text-zinc-400"
          {...props}
        >
          {children}
        </del>
      ),
      // Strong/emphasis
      strong: ({ node, children, ...props }) => (
        <strong
          className="font-bold text-zinc-900 dark:text-zinc-100"
          {...props}
        >
          {children}
        </strong>
      ),
      em: ({ node, children, ...props }) => (
        <em className="italic text-zinc-800 dark:text-zinc-200" {...props}>
          {children}
        </em>
      ),
      hr: ({ node, ...props }) => (
        <hr
          className="my-6 border-t border-zinc-200 dark:border-zinc-700"
          {...props}
        />
      ),
      pre({ node, children, ...props }) {
        // This 'pre' renderer handles <pre> tags that are not code blocks (e.g., not triple backticks).
        // Children here might be a <code> element, handled by the code renderer, or plain text.
        return (
          <pre
            className="my-2 bg-zinc-100 dark:bg-zinc-800 p-2 rounded whitespace-pre-wrap"
            {...props}
          >
            {children}
          </pre>
        );
      },
      // Add renderWithThinkingBlocks to dependency array if it were defined inside MarkdownRenderer,
      // but since it's a top-level const, components only needs to re-memoize if its direct code changes.
      // The current empty array [] means components is memoized once.
    }),
    [],
  );

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
      >
        {processedMarkdown}
      </ReactMarkdown>
    </div>
  );
});
