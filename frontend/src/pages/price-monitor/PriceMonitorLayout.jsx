import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { StackedLayout } from '@common/stacked-layout';
import { Navbar, NavbarItem, NavbarSection, NavbarSpacer, NavbarLabel } from '@common/navbar';
import { Sidebar, SidebarHeader, SidebarBody, SidebarItem, SidebarLabel, SidebarSection } from '@common/sidebar';
import {
  HomeIcon,
  BuildingStorefrontIcon,
  ClipboardDocumentListIcon,
  Square2StackIcon,
  ExclamationTriangleIcon,
  Cog6ToothIcon,
  PresentationChartLineIcon,
  QuestionMarkCircleIcon
} from '@heroicons/react/20/solid';

// Import pages (will create these next)
import PriceMonitorDashboard from './PriceMonitorDashboard';
import CompetitorsPage from './CompetitorsPage';
import ProductMatchesPage from './ProductMatchesPage';
import PriceAlertsPage from './PriceAlertsPage';
import MonitorSettingsPage from './MonitorSettingsPage';
import PriceMonitorHelp from './PriceMonitorHelp';

const navigation = [
  { name: 'Dashboard', href: '/price-monitor', icon: HomeIcon, exact: true },
  { name: 'Competitors', href: '/price-monitor/competitors', icon: BuildingStorefrontIcon },
  { name: 'Product Matches', href: '/price-monitor/matches', icon: Square2StackIcon },
  { name: 'Price Alerts', href: '/price-monitor/alerts', icon: ExclamationTriangleIcon },
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
      navbar={
        <Navbar>
          <NavbarSection>
            <div className="flex items-center gap-3">
              <PresentationChartLineIcon className="h-6 w-6 text-indigo-600" />
              <NavbarLabel className="text-lg font-semibold">Price Monitor</NavbarLabel>
            </div>
          </NavbarSection>
          <NavbarSpacer />
          <NavbarSection>
            {navigation.map((item) => (
              <NavbarItem
                key={item.name}
                href={item.href}
                current={isActive(item)}
              >
                <item.icon />
                <NavbarLabel className="hidden sm:block">{item.name}</NavbarLabel>
              </NavbarItem>
            ))}
          </NavbarSection>
        </Navbar>
      }
      sidebar={
        <Sidebar>
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
                >
                  <item.icon />
                  <SidebarLabel>{item.name}</SidebarLabel>
                </SidebarItem>
              ))}
            </SidebarSection>
          </SidebarBody>
        </Sidebar>
      }
    >
      <Routes>
        <Route path="/" element={<PriceMonitorDashboard />} />
        <Route path="/competitors" element={<CompetitorsPage />} />
        <Route path="/matches" element={<ProductMatchesPage />} />
        <Route path="/alerts" element={<PriceAlertsPage />} />
        <Route path="/settings" element={<MonitorSettingsPage />} />
        <Route path="/help" element={<PriceMonitorHelp />} />
      </Routes>
    </StackedLayout>
  );
}