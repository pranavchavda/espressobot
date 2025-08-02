import React from "react";
import { Button } from "@common/button";
import { Text } from "@common/text";
import { LayoutPanelLeft, Terminal, Loader2 } from "lucide-react";

export default function TopBar({
  title,
  user,
  onLogout,
  onToggleLogs,
  onGlobalSearch,
  onToggleTheme,
  isDark = false,
  className = ""
}) {
  // Theme toggle and global search temporarily disabled per request

  return (
    <div className={`w-full h-12 flex items-center justify-between gap-2 py-2 px-2 sm:px-3 border-b border-zinc-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-zinc-900/60 ${className}`}>
      <div className="flex items-center gap-2 min-w-0">
        <span className="inline-flex items-center px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-xs text-zinc-600 dark:text-zinc-300">
          <LayoutPanelLeft className="h-4 w-4 mr-1 opacity-80" />
          EspressoBot
        </span>
        {title ? (
          <Text className="truncate ml-1 font-medium text-zinc-800 dark:text-zinc-100">{title}</Text>
        ) : (
          <Text className="truncate ml-1 text-zinc-600 dark:text-zinc-300">Ready</Text>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <Button
          plain
          className="h-9 w-9 rounded-full"
          title="Toggle log drawer (Ctrl/Cmd + Shift + L)"
          onClick={onToggleLogs}
          aria-label="Toggle logs"
        >
          <Terminal className="h-5 w-5" />
        </Button>

        {user ? (
          <div className="ml-1 inline-flex items-center gap-2 pl-2">
            <span className="text-xs text-zinc-600 dark:text-zinc-300 truncate max-w-[120px] sm:hidden" title={user.email || user.name}>
              {user.name || user.email || "User"}
            </span>
            <Button outline size="sm" className="h-8 sm:hidden" onClick={onLogout}>
              Logout
            </Button>
          </div>
        ) : (
          <div className="ml-1 inline-flex items-center gap-2 pl-2 text-xs text-zinc-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading user...
          </div>
        )}
      </div>
    </div>
  );
}
