import React from 'react';

export function Text({ children, className = '', ...props }) {
  return (
    <p className={`text-zinc-800 dark:text-zinc-200 ${className}`} {...props}>
      {children}
    </p>
  );
}

export function TextLink({ href, children, className = '', ...props }) {
  return (
    <a 
      href={href}
      className={`text-blue-600 dark:text-blue-400 hover:underline ${className}`}
      target={href.startsWith('http') ? "_blank" : undefined}
      rel={href.startsWith('http') ? "noopener noreferrer" : undefined}
      {...props}
    >
      {children}
    </a>
  );
}

export function Strong({ children, className = '', ...props }) {
  return (
    <strong className={`font-semibold ${className}`} {...props}>
      {children}
    </strong>
  );
}
