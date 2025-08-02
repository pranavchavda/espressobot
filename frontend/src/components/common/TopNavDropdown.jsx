import React from 'react';
import { Menu, MenuButton, MenuItems, MenuItem, Transition } from '@headlessui/react';
import { Link } from 'react-router-dom';
import { ChevronDownIcon, InformationCircleIcon, Cog8ToothIcon, ArrowLeftStartOnRectangleIcon, UserCircleIcon, ChartBarIcon, PresentationChartLineIcon, ArrowPathIcon } from '@heroicons/react/20/solid';
import md5 from 'js-md5';
import { Avatar } from './avatar';

function TopNavDropdown({ user, onLogout, collapsed }) {
  if (!user) {
    return null;
  }

  const gravatarUrl = `https://www.gravatar.com/avatar/${md5(user.email.trim().toLowerCase())}?d=mp&s=80`;

  const handleCacheRefresh = () => {
    // Show confirmation for nuclear cache clear
    const confirmed = window.confirm(
      'Clear Cache & Refresh:\n\n' +
      '• This will force a complete cache refresh\n' +
      '• Helpful for Vivaldi/Chromium when you see old content\n' +
      '• Your login session will be preserved\n' +
      '• Only use this if you\'re seeing cached/outdated content\n\n' +
      'Continue with cache refresh?'
    );
    
    if (!confirmed) return;
    
    console.log('[TopNav] User manually triggered cache refresh');
    
    if (window.espressoBotCacheBuster) {
      window.espressoBotCacheBuster.refresh();
    } else {
      // Fallback with nuclear approach
      console.log('[TopNav] Cache buster not available, using fallback nuclear approach');
      
      // Clear everything possible BUT preserve auth
      try {
        // Backup auth tokens
        const authToken = localStorage.getItem('authToken');
        const userInfo = localStorage.getItem('userInfo');
        const googleTokens = localStorage.getItem('googleTokens');
        
        // Clear localStorage selectively
        Object.keys(localStorage).forEach(key => {
          if (!['authToken', 'userInfo', 'googleTokens'].includes(key)) {
            localStorage.removeItem(key);
          }
        });
        
        sessionStorage.clear();
        
        // Clear cookies selectively
        const authCookiePatterns = ['connect.sid', 'session', 'auth', 'token', 'passport'];
        document.cookie.split(";").forEach(c => {
          const eqPos = c.indexOf("=");
          const name = eqPos > -1 ? c.substr(0, eqPos).trim() : c.trim();
          // Don't clear auth-related cookies (be more permissive with matching)
          const isAuthCookie = authCookiePatterns.some(pattern => 
            name.toLowerCase().includes(pattern.toLowerCase())
          );
          
          if (!isAuthCookie) {
            console.log('[TopNav] Clearing non-auth cookie:', name);
            document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
          } else {
            console.log('[TopNav] Preserving auth cookie:', name);
          }
        });
        
        console.log('[TopNav] Preserved auth tokens during cache clear');
      } catch (e) {
        console.warn('Storage clearing failed:', e);
      }
      
      // Force refresh with cache busting
      const timestamp = Date.now();
      const random = Math.random().toString(36).substr(2, 15);
      const baseUrl = window.location.origin + window.location.pathname;
      const bustUrl = `${baseUrl}?nuclear=${timestamp}&vivaldi=true&r=${random}&nocache=1`;
      
      window.location.replace(bustUrl);
    }
  };

  return (
    <Menu as="div" className="relative">
      <MenuButton className="flex items-center gap-x-4 p-1.5 text-sm/6 font-semibold text-zinc-950 dark:text-white focus:outline-none data-[active]:bg-zinc-100 dark:data-[active]:bg-zinc-800 data-[hover]:bg-zinc-100 dark:data-[hover]:bg-zinc-800 data-[open]:bg-zinc-100 dark:data-[open]:bg-zinc-800 rounded-lg">
        <Avatar src={gravatarUrl} alt={user.name} initials={user.name?.[0]} className="h-8 w-8" />
        {!collapsed && <span className="hidden lg:block">{user.name}</span>}
        {!collapsed && <ChevronDownIcon className="w-5 h-5 text-zinc-500 dark:text-zinc-400" />}
      </MenuButton>
      <Transition
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <MenuItems
          anchor="bottom end"
          className="w-64 origin-top-right rounded-xl border border-zinc-950/5 bg-white p-1 text-sm/6 text-zinc-950 [--anchor-gap:var(--spacing-1)] focus:outline-none dark:border-white/10 dark:bg-zinc-900 dark:text-white"
        >
          <div className="p-2.5">
            <p className="text-sm/6 font-semibold">{user.name}</p>
            <p className="mt-0.5 text-xs/6 text-zinc-500 dark:text-zinc-400">{user.email}</p>
          </div>
          <div className="h-px bg-zinc-950/5 dark:bg-white/10" />
          <MenuItem>
            <Link to="/profile" className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800">
              <UserCircleIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              My account
            </Link>
          </MenuItem>
          <MenuItem>
            <Link to="/dashboard" className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800">
              <ChartBarIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              Dashboard
            </Link>
          </MenuItem>
          <MenuItem>
            <Link to="/price-monitor" className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800">
              <PresentationChartLineIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              Price Monitor
            </Link>
          </MenuItem>
          <MenuItem>
            <Link to="/about" className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800">
              <InformationCircleIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              About
            </Link>
          </MenuItem>
          {user.is_admin && (
            <MenuItem>
              <Link to="/admin" className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800">
                <Cog8ToothIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
                Admin
              </Link>
            </MenuItem>
          )}
          <div className="h-px bg-zinc-950/5 dark:bg-white/10" />
          <MenuItem>
            <button
              onClick={handleCacheRefresh}
              className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800"
              title="Clear cache and refresh app (helpful for Vivaldi/Chromium browsers)"
            >
              <ArrowPathIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              Clear Cache & Refresh
            </button>
          </MenuItem>
          <MenuItem>
            <button
              onClick={onLogout}
              className="group flex w-full items-center gap-x-2.5 rounded-lg p-2.5 data-[focus]:bg-zinc-100 dark:data-[focus]:bg-zinc-800"
            >
              <ArrowLeftStartOnRectangleIcon className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
              Sign out
            </button>
          </MenuItem>
        </MenuItems>
      </Transition>
    </Menu>
  );
}

export default TopNavDropdown;
