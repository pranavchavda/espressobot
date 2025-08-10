import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { StackedLayout } from '@components/common/stacked-layout';
import { Navbar, NavbarSection, NavbarItem, NavbarLabel, NavbarSpacer } from '@components/common/navbar';
import { Sidebar, SidebarSection, SidebarItem, SidebarLabel, SidebarHeader, SidebarBody } from '@components/common/sidebar';
import { PresentationChartLineIcon } from '@heroicons/react/24/outline';
import { HomeIcon, BuildingStorefrontIcon, Square2StackIcon, ExclamationTriangleIcon, Cog6ToothIcon, QuestionMarkCircleIcon, ClockIcon } from '@heroicons/react/20/solid';

import PriceMonitorDashboard from './PriceMonitorDashboard';
import CompetitorsPage from './CompetitorsPage';
import ProductMatchesPage from './ProductMatchesPage';
import PriceAlertsPage from './PriceAlertsPage';
import ViolationHistoryPage from './ViolationHistoryPage';
import MonitorSettingsPage from './MonitorSettingsPage';
import PriceMonitorHelp from './PriceMonitorHelp';

const navigation = [
  { name: 'Dashboard', href: '/price-monitor', icon: HomeIcon, exact: true },
  { name: 'Competitors', href: '/price-monitor/competitors', icon: BuildingStorefrontIcon },
  { name: 'Product Matches', href: '/price-monitor/matches', icon: Square2StackIcon },
  { name: 'Price Alerts', href: '/price-monitor/alerts', icon: ExclamationTriangleIcon },
  { name: 'Violation History', href: '/price-monitor/history', icon: ClockIcon },
  { name: 'Settings', href: '/price-monitor/settings', icon: Cog6ToothIcon },
  { name: 'Help', href: '/price-monitor/help', icon: QuestionMarkCircleIcon },
];

export default function PriceMonitorLayout() {
  const location = useLocation();

  const isActive = (item) => {
    if (item.exact) {
      return location.pathname === item.href;
    }
    return location.pathname.startsWith(item.href);
  };

  return (
    <StackedLayout
      className="min-h-[80vh]"
      navbar={
        <Navbar className="sticky top-0 z-10 supports-[backdrop-filter]:bg-white/70 dark:supports-[backdrop-filter]:bg-zinc-900/70 backdrop-blur border-b border-zinc-200/60 dark:border-zinc-800/60 shadow-sm before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-transparent before:via-indigo-500/50 before:to-transparent">
          <NavbarSection>
            <div className="flex items-center gap-3">
              <PresentationChartLineIcon className="h-6 w-6 text-indigo-600" />
              <NavbarLabel className="text-lg font-semibold">Price Monitor</NavbarLabel>
            </div>
          </NavbarSection>
          <NavbarSpacer />

          {/* Desktop nav items */}
          <NavbarSection className="hidden lg:flex flex-wrap gap-1">
            {navigation.map((item) => (
              <NavbarItem
                key={item.name}
                href={item.href}
                current={isActive(item)}
                className={`group relative min-w-[40px] transition before:transition-all before:duration-300 ${
                  isActive(item)
                    ? 'before:content-[""] before:absolute before:inset-0 before:rounded-lg before:bg-indigo-50 before:ring-1 before:ring-indigo-200 dark:before:bg-indigo-500/10 dark:before:ring-indigo-400/20'
                    : 'hover:before:content-[""] hover:before:absolute hover:before:inset-0 hover:before:rounded-lg hover:before:bg-zinc-950/5 dark:hover:before:bg-white/5 focus-within:before:content-[""] focus-within:before:absolute focus-within:before:inset-0 focus-within:before:rounded-lg focus-within:before:ring-2 focus-within:before:ring-indigo-500/30'
                }`}
              >
                <item.icon className={isActive(item) ? 'h-5 w-5 text-indigo-600' : 'h-5 w-5 text-zinc-500 group-hover:text-zinc-900 dark:group-hover:text-white'} />
                <NavbarLabel className={`${isActive(item) ? 'text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-900 dark:group-hover:text-white'}`}>{item.name}</NavbarLabel>
              </NavbarItem>
            ))}
          </NavbarSection>

        </Navbar>
      }
      sidebar={
        <Sidebar className="lg:sticky lg:top-[56px] lg:h-[calc(100vh-56px)]">
          <SidebarHeader>
            <div className="flex items-center gap-3">
              <PresentationChartLineIcon className="h-6 w-6 text-indigo-600" />
              <SidebarLabel className="text-lg font-semibold">Price Monitor</SidebarLabel>
            </div>
          </SidebarHeader>
          <SidebarBody>
            <SidebarSection>
              {navigation.map((item) => (
                <SidebarItem
                  key={item.name}
                  href={item.href}
                  current={isActive(item)}
                  className={`group relative transition before:transition-all before:duration-300 ${
                    isActive(item)
                      ? 'before:content-[""] before:absolute before:inset-0 before:rounded-lg before:bg-indigo-50 before:ring-1 before:ring-indigo-200 dark:before:bg-indigo-500/10 dark:before:ring-indigo-400/20'
                      : 'hover:before:content-[""] hover:before:absolute hover:before:inset-0 hover:before:rounded-lg hover:before:bg-zinc-950/5 dark:hover:before:bg-white/5 focus-within:before:content-[""] focus-within:before:absolute focus-within:before:inset-0 focus-within:before:rounded-lg focus-within:before:ring-2 focus-within:before:ring-indigo-500/30'
                  }`}
                >
                  <item.icon className={isActive(item) ? 'h-5 w-5 text-indigo-600' : 'h-5 w-5 text-zinc-500 group-hover:text-zinc-900 dark:group-hover:text-white'} />
                  <SidebarLabel className={isActive(item) ? 'text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-900 dark:group-hover:text-white'}>{item.name}</SidebarLabel>
                </SidebarItem>
              ))}
            </SidebarSection>
          </SidebarBody>
        </Sidebar>
      }
    >
      <div className="p-3 sm:p-4 lg:p-6 mx-auto w-full max-w-7xl">
        <div className="grid grid-cols-1 gap-4">
          <Routes>
            <Route path="/" element={<PriceMonitorDashboard />} />
            <Route path="/competitors" element={<CompetitorsPage />} />
            <Route path="/matches" element={<ProductMatchesPage />} />
            <Route path="/alerts" element={<PriceAlertsPage />} />
            <Route path="/history" element={<ViolationHistoryPage />} />
            <Route path="/settings" element={<MonitorSettingsPage />} />
            <Route path="/help" element={<PriceMonitorHelp />} />
          </Routes>
        </div>
      </div>
    </StackedLayout>
  );
}
