import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
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

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

export default function PriceMonitorLayout() {
  const location = useLocation();

  const isActive = (item) => {
    if (item.exact) {
      return location.pathname === item.href;
    }
    return location.pathname.startsWith(item.href);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex">
        {/* Sidebar */}
        <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 md:top-16">
          <div className="flex-1 flex flex-col min-h-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
            <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
              <div className="flex items-center flex-shrink-0 px-4">
                <PresentationChartLineIcon className="h-8 w-8 text-indigo-600" />
                <span className="ml-2 text-xl font-semibold text-gray-900 dark:text-white">
                  Price Monitor
                </span>
              </div>
              <nav className="mt-8 flex-1 px-2 space-y-1">
                {navigation.map((item) => {
                  const current = isActive(item);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={classNames(
                        current
                          ? 'bg-indigo-50 border-indigo-500 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200'
                          : 'border-transparent text-gray-900 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white',
                        'group flex items-center px-3 py-2 text-sm font-medium border-l-4 rounded-md'
                      )}
                    >
                      <item.icon
                        className={classNames(
                          current ? 'text-indigo-500 dark:text-indigo-200' : 'text-gray-400 group-hover:text-gray-500 dark:text-gray-400 dark:group-hover:text-gray-300',
                          'mr-3 flex-shrink-0 h-5 w-5'
                        )}
                      />
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="md:pl-64 flex flex-col flex-1">
          <main className="flex-1">
            <div className="py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                <Routes>
                  <Route path="/" element={<PriceMonitorDashboard />} />
                  <Route path="/competitors" element={<CompetitorsPage />} />
                  <Route path="/matches" element={<ProductMatchesPage />} />
                  <Route path="/alerts" element={<PriceAlertsPage />} />
                  <Route path="/settings" element={<MonitorSettingsPage />} />
                  <Route path="/help" element={<PriceMonitorHelp />} />
                </Routes>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}