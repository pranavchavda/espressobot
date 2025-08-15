import React, { useMemo, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@common/button";
import { Divider } from "@common/divider";
import TopNavDropdown from "../common/TopNavDropdown";
import { Loader2Icon, XIcon, MessageSquarePlusIcon, PinIcon, PinOffIcon, MenuIcon, FileTextIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

function ConversationItem({ chat, selected, onSelect, onDelete, pinned, onTogglePin, collapsed }) {
  // When collapsed, show a compact avatar-style indicator instead of text
  if (collapsed) {
    return (
      <li className="group relative">
        <Link
          to={`/chat/${chat.id}`}
          onClick={(e) => {
            onSelect(chat.id);
          }}
          className={`block w-10 h-10 rounded-full flex items-center justify-center transition-colors border
            ${selected ? "bg-zinc-200 dark:bg-zinc-800 font-semibold border-zinc-300 dark:border-zinc-700" : "hover:bg-zinc-100 dark:hover:bg-zinc-800 border-transparent"}
          `}
          aria-current={selected ? "page" : undefined}
          title={chat.topic_title || chat.title}
        >
          <span className="text-xs font-bold">
            {(chat.topic_title || chat.title || "C").charAt(0).toUpperCase()}
          </span>
        </Link>
      </li>
    );
  }

  // Full-width item when expanded
  return (
    <li className="group relative">
      <Link
        to={`/chat/${chat.id}`}
        onClick={(e) => {
          onSelect(chat.id);
        }}
        className={`block w-full text-left px-3 py-2 rounded-lg transition-colors border
          ${selected ? "bg-zinc-200 dark:bg-zinc-800 font-semibold border-zinc-300 dark:border-zinc-700" : "hover:bg-zinc-100 dark:hover:bg-zinc-800 border-transparent"}
        `}
        aria-current={selected ? "page" : undefined}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate flex items-center gap-1">
              {pinned && <PinIcon className="h-3.5 w-3.5 text-zinc-500 dark:text-zinc-400 shrink-0" />}
              {chat.topic_title ? (
                <span>{chat.topic_title}</span>
              ) : (
                <span style={{ opacity: 0.85 }}>{chat.title}</span>
              )}
            </div>
            {chat.last_message_preview && (
              <div className="text-[11px] text-zinc-500 truncate mt-0.5">
                {chat.last_message_preview}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 ml-2">
            <button
              type="button"
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity p-1 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onTogglePin(chat.id, !pinned);
              }}
              title={pinned ? "Unpin" : "Pin"}
              aria-label={pinned ? "Unpin conversation" : "Pin conversation"}
            >
              {pinned ? <PinOffIcon className="h-4 w-4 text-zinc-500" /> : <PinIcon className="h-4 w-4 text-zinc-500" />}
            </button>
            <button
              type="button"
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity p-1 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete(chat.id);
              }}
              title="Delete conversation"
              aria-label="Delete conversation"
            >
              <XIcon className="h-4 w-4 text-zinc-500" />
            </button>
          </div>
        </div>
      </Link>
    </li>
  );
}

export default function SidebarNav({
  user,
  onLogout,
  conversations,
  selectedChat,
  loading,
  onSelectConversation,
  onDeleteConversation,
  onNewChat,
  onOpenScratchpad,
  collapsible = true,
  collapsed,
  onToggleCollapsed
}) {
  const [pinnedIds, setPinnedIds] = useState(() => {
    try {
      const val = localStorage.getItem("pinned-conversations");
      return val ? JSON.parse(val) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try { localStorage.setItem("pinned-conversations", JSON.stringify(pinnedIds)); } catch {}
  }, [pinnedIds]);

  const pinnedSet = useMemo(() => new Set(pinnedIds), [pinnedIds]);

  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    if (!Array.isArray(conversations)) return [];
    const base = query.trim()
      ? conversations.filter(c => (c.topic_title || c.title || "").toLowerCase().includes(query.trim().toLowerCase()))
      : conversations;
    const pinned = base.filter(c => pinnedSet.has(c.id));
    const unpinned = base.filter(c => !pinnedSet.has(c.id));
    return [...pinned, ...unpinned];
  }, [conversations, query, pinnedSet]);

  const handleTogglePin = useCallback((id, nextPinned) => {
    setPinnedIds(prev => {
      const set = new Set(prev);
      if (nextPinned) set.add(id); else set.delete(id);
      return Array.from(set);
    });
  }, []);

  const handleSelect = useCallback((id) => {
    onSelectConversation?.(id);
  }, [onSelectConversation]);

  return (
    <aside
      className={`relative flex flex-col h-[93vh] sm:h-full transition-[width] duration-200`}
      style={{ width: collapsed ? 88 : 304, minWidth: collapsed ? 88 : 304, maxWidth: collapsed ? 88 : 304 }}
    >
      {/* Visual rail to make the sidebar distinct and clearly wider */}
      <div className="absolute inset-0 dark:bg-zinc-900/95 border-r border-zinc-200 dark:border-zinc-800 shadow-sm bg-gradient-to-b from-zinc-100 to-zinc-200" />
      {/* Content layer */}
      <div className="relative z-10 flex flex-col h-full overflow-hidden">
        <nav className="flex-1 overflow-y-auto px-3 py-2">
        <div className="flex items-center justify-between my-2">
          {/* Always show the user dropdown, even when collapsed */}
          <TopNavDropdown user={user} onLogout={onLogout} collapsed={collapsed} className={`w-full cursor-pointer ${collapsed ? "justify-center " : ""}`} />
          {collapsible && (
            <button
              type="button"
              className={`p-2 rounded border border-transparent hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:border-zinc-200 dark:hover:border-zinc-700 ${collapsed ? "" : "ml-2"}`}
              onClick={onToggleCollapsed}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <ChevronRightIcon className="h-5 w-5" /> : <ChevronLeftIcon className="h-4 w-4" />}
            </button>
          )}
        </div>

        {/* Actions */}
        <div className={`flex ${collapsed ? "flex-col items-center space-y-2" : "flex-row space-x-2"} mb-3 overflow-x-hidden`}>
          <Button 
            className={`cursor-pointer ${collapsed ? "w-10 h-10 justify-center" : "flex-1"}`}
            color="steel-blue"
            outline
            onClick={onNewChat}
            title="New chat"
            aria-label="New chat"
          >
            <MessageSquarePlusIcon className="h-4 w-4" />
            {!collapsed && <span className="ml-1">New</span>}
          </Button>
          <Button 
            className={`cursor-pointer ${collapsed ? "w-10 h-10 justify-center" : "flex-1"}`}
            color="steel-blue"
            outline
            onClick={onOpenScratchpad}
            title="Scratchpad"
            aria-label="Open scratchpad"
          >
            <FileTextIcon className="h-4 w-4" />
            {!collapsed && <span className="ml-1">Scratchpad</span>}
          </Button>
        </div>

        {/* Optional search */}
        {!collapsed && (
          <div className="mb-3 overflow-x-hidden">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search conversations"
              className="w-full px-2 py-1.5 text-sm rounded border border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800"
              aria-label="Search conversations"
            />
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-2">
            <Loader2Icon className="animate-spin h-16 w-16 text-zinc-400" />
          </div>
        ) : (
          <>
            <ul className={`flex flex-col max-h-[70vh] overflow-y-auto h-[70vh] overflow-x-hidden ${collapsed ? "items-center space-y-2" : ""}`}>
              {filtered.map((chat) => (
                <ConversationItem
                  key={chat.id}
                  chat={chat}
                  selected={selectedChat === chat.id}
                  onSelect={handleSelect}
                  onDelete={onDeleteConversation}
                  pinned={pinnedSet.has(chat.id)}
                  onTogglePin={handleTogglePin}
                  collapsed={collapsed}
                />
              ))}
              {filtered.length === 0 && (
                <li className={`text-zinc-400 px-3 py-2 ${collapsed ? "text-center" : ""}`}>{query ? "No conversations found" : "No conversations yet"}</li>
              )}
            </ul>
          </>
        )}

        <Divider soft="true" />
        <Link to="/price-monitor" className={`group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800 overflow-x-hidden ${collapsed ? "justify-center" : ""}`}>
          <span className="h-5 w-5 inline-flex items-center justify-center text-zinc-500 dark:text-zinc-400">📈</span>
          {!collapsed && <span className="text-zinc-700 dark:text-zinc-300">Price Monitor</span>}
        </Link>
        <Divider soft="true" />
        </nav>
        {/* Footer utilities */}
        <div className={`mt-auto p-2 border-t border-zinc-200/80 dark:border-zinc-800/80 ${collapsed ? "flex flex-col items-center gap-2" : "flex items-center justify-between"} overflow-x-hidden`}>
          {!collapsed && (
            <button
              type="button"
              onClick={onLogout}
              className="px-2 py-1.5 rounded border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-sm w-full"
            >
              Logout
            </button>
          )}
        </div>
      </div>
    </aside>

  );
}
