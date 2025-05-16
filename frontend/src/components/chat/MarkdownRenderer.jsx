import React, { useRef, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Button } from '../../components/common/button';
import { Text, Code } from '../../components/common/text';

function processContent(content) {
  if (!content) return { processedContent: '' };
  
  const lines = content.split('\n');
  const processedLines = [];
  let inThinkingBlock = false;
  
  for (const line of lines) {
    if (line.trim() === '<THINKING>') {
      inThinkingBlock = true;
    } else if (line.trim() === '</THINKING>') {
      inThinkingBlock = false;
    } else if (inThinkingBlock) {
      // Skip empty lines after these blocks
      if (line.trim() === '' && (
        processedLines[processedLines.length - 1]?.startsWith(':::') ||
        processedLines[processedLines.length - 1]?.trim() === ''
      )) continue;
      
      processedLines.push(line);
    } else {
      processedLines.push(line);
    }
    
    // Close the block if we hit an empty line after it
    if (inThinkingBlock && line.trim() === '') {
      inThinkingBlock = false;
      processedLines.push(':::');
    }
  }
  
  return {
    processedContent: processedLines.join('\n'),
    hasSpecialBlocks: inThinkingBlock 
  };
}

const CodeBlock = ({ language, children }) => {
  const codeRef = useRef(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (codeRef.current) {
      navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div ref={codeRef} className="relative my-5 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700">
      <div className="flex justify-between items-center bg-zinc-100 dark:bg-zinc-800 px-4 py-2 text-xs text-zinc-800 dark:text-zinc-200">
        <span className="font-mono font-medium">{language}</span>
        <Button
         plain
          onClick={handleCopy}
          className={`text-xs px-3 py-1 rounded transition-colors ${
            copied 
              ? 'bg-green-100 text-green-800 dark:bg-green-800/30 dark:text-green-300' 
              : 'bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600'
          }`}
        >
          {copied ? 'Copied!' : 'Copy'}
        </Button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language || 'text'}
        customStyle={{
          margin: 0,
          padding: '1rem',
          background: 'rgb(24 24 27)', // Tailwind zinc-900
          borderRadius: 0,
          fontSize: '0.875rem'
        }}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    </div>
  );
};

export function MarkdownRenderer({ children, className = '' }) {
  const { processedContent, hasSpecialBlocks } = useMemo(
    () => processContent(children),
    [children]
  );

  const components = useMemo(() => ({
    // Headings
    h1: ({ node, children, ...props }) => (
      <Text as="h1" className="text-2xl font-bold mt-6 mb-4 text-zinc-900 dark:text-zinc-100" {...props}>{children}</Text>
    ),
    h2: ({ node, children, ...props }) => (
      <Text as="h2" className="text-xl font-bold mt-5 mb-3 text-zinc-900 dark:text-zinc-100" {...props}>{children}</Text>
    ),
    h3: ({ node, children, ...props }) => (
      <Text as="h3" className="text-lg font-bold mt-4 mb-2 text-zinc-900 dark:text-zinc-100" {...props}>{children}</Text>
    ),
    // Paragraphs
    p: ({ node, children, ...props }) => (
      <Text className="text-base leading-relaxed my-3 whitespace-pre-wrap text-zinc-800 dark:text-zinc-200" {...props}>{children}</Text>
    ),
    // Lists
    ul: ({ node, children, ...props }) => (
      <ul className="list-disc pl-6 my-4 space-y-2 text-zinc-800 dark:text-zinc-200" {...props}>{children}</ul>
    ),
    ol: ({ node, children, ...props }) => (
      <ol className="list-decimal pl-6 my-4 space-y-2 text-zinc-800 dark:text-zinc-200" {...props}>{children}</ol>
    ),
    li: ({ node, children, ...props }) => (
      <li className="ml-2" {...props}>{children}</li>
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
    // Links
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
    // Tables
    table: ({ node, children, ...props }) => (
      <div className="overflow-x-auto my-6">
        <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-700 border border-zinc-200 dark:border-zinc-700 rounded-lg" {...props}>{children}</table>
      </div>
    ),
    thead: ({ node, children, ...props }) => (
      <thead className="bg-zinc-100 dark:bg-zinc-800" {...props}>{children}</thead>
    ),
    tbody: ({ node, children, ...props }) => (
      <tbody className="divide-y divide-zinc-200 dark:divide-zinc-700" {...props}>{children}</tbody>
    ),
    tr: ({ node, children, ...props }) => (
      <tr className="hover:bg-zinc-50 dark:hover:bg-zinc-800/70" {...props}>{children}</tr>
    ),
    th: ({ node, children, ...props }) => (
      <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider" {...props}>{children}</th>
    ),
    td: ({ node, children, ...props }) => (
      <td className="px-4 py-3 text-sm text-zinc-800 dark:text-zinc-200" {...props}>{children}</td>
    ),
    // Code blocks and inline code
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : 'text';
      if (inline) {
        return (
          <Code className="bg-zinc-100 dark:bg-zinc-700 rounded px-1.5 py-0.5 text-sm font-mono">
            {children}
          </Code>
        );
      }
      return (
        <CodeBlock language={language}>
          {String(children).replace(/\n$/, '')}
        </CodeBlock>
      );
    },
    // Images
    img: ({ node, ...props }) => (
      <div className="my-4">
        <img className="max-w-full rounded-lg shadow-md" {...props} alt={props.alt || ''} loading="lazy" />
        {props.title && <p className="text-center text-sm mt-2 text-zinc-500 dark:text-zinc-400 italic">{props.title}</p>}
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
      <del className="line-through text-zinc-500 dark:text-zinc-400" {...props}>{children}</del>
    ),
    // Strong/emphasis
    strong: ({ node, children, ...props }) => (
      <strong className="font-bold text-zinc-900 dark:text-zinc-100" {...props}>{children}</strong>
    ),
    em: ({ node, children, ...props }) => (
      <em className="italic text-zinc-800 dark:text-zinc-200" {...props}>{children}</em>
    ),
    hr: ({ node, ...props }) => (
      <hr className="my-6 border-t border-zinc-200 dark:border-zinc-700" {...props} />
    ),
    // Pre (wrapper for code blocks)
    pre({ node, children, ...props }) {
      return <div className="my-2">{children}</div>;
    },
  }), []);

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}

