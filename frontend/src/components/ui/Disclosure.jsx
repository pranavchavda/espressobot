import React, { useState } from 'react';
import { ChevronRightIcon } from 'lucide-react';

export function Disclosure({ title, children, color, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const toggleDisclosure = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="my-2 text-sm">
      <button
        onClick={toggleDisclosure}
        className="flex items-center gap-1.5 text-xs font-medium w-full text-left focus:outline-none"
        style={{ color: color || '#3b82f6' }}
      >
        <ChevronRightIcon
          size={14}
          className={`transition-transform ${isOpen ? 'rotate-90' : ''}`}
        />
        {title}
      </button>
      {isOpen && (
        <div className="pl-5 pt-1 pb-1 text-xs text-zinc-500 dark:text-zinc-400 border-l border-zinc-200 dark:border-zinc-700 ml-1.5 mt-1">
          {children}
        </div>
      )}
    </div>
  );
}
