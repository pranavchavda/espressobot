import React from 'react';
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/react';
import { Link } from 'react-router-dom';
import { ChevronDown, UserCircle, BookMarked, LogOut } from 'lucide-react';
import md5 from 'js-md5';
import { Avatar } from './avatar';


function UserProfileDropdown({ user, onLogout }) {
  if (!user) {
    return null;
  }

  const gravatarUrl = `https://www.gravatar.com/avatar/${md5(user.email.trim().toLowerCase())}?d=mp&s=80`;

  return (
    <div className="mt-auto p-2 border-t border-zinc-200 dark:border-zinc-700">
      <Menu as="div" className="relative w-full">
        <MenuButton className="group w-full flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75">
          <div className="flex items-center">
            <Avatar src={gravatarUrl} alt={user.name} initials={user.name?.[0]} className="h-8 w-8 mr-3" />
            <div className="text-left">
              <span className="block truncate font-semibold">{user.name}</span>
              <span className="block truncate text-xs text-zinc-500 dark:text-zinc-400">{user.email}</span>
            </div>
          </div>
          <ChevronDown
            className="ml-2 h-5 w-5 text-zinc-400 group-hover:text-zinc-500 transition-transform duration-150 ease-in-out group-aria-expanded:rotate-180"
            aria-hidden="true"
          />
        </MenuButton>
        <MenuItems className="absolute bottom-full mb-2 w-full origin-bottom-right rounded-md bg-white dark:bg-zinc-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
          <div className="px-1 py-1">
            <MenuItem as={Link} to="/profile" className={({ active }) =>
              `${active ? 'bg-zinc-100 dark:bg-zinc-700 text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300'}
              group flex w-full items-center rounded-md px-2 py-2 text-sm`
            }>
              <UserCircle className="mr-2 h-5 w-5" aria-hidden="true" />
              My account
            </MenuItem>
            <MenuItem as={Link} to="/tasks" className={({ active }) =>
              `${active ? 'bg-zinc-100 dark:bg-zinc-700 text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300'}
              group flex w-full items-center rounded-md px-2 py-2 text-sm`
            }>
              <BookMarked className="mr-2 h-5 w-5" aria-hidden="true" />
              Tasks
            </MenuItem>
            <MenuItem as="button" onClick={onLogout} className={({ active }) =>
              `${active ? 'bg-zinc-100 dark:bg-zinc-700 text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300'}
              group flex w-full items-center rounded-md px-2 py-2 text-sm`
            }>
              <LogOut className="mr-2 h-5 w-5" aria-hidden="true" />
              Sign out
            </MenuItem>
          </div>
        </MenuItems>
      </Menu>
    </div>
  );
}

export default UserProfileDropdown;
