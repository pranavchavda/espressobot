import React from 'react';
import { Button } from '@common/button';
import logo from '../../static/EspressoBotLogo.png';
import { LogOutIcon, MessageSquareIcon } from 'lucide-react';

const RestrictedPage = ({ user, onLogout }) => {
  const handleContactPranav = () => {
    window.location.href = 'mailto:pranav@idrinkcoffee.com?subject=EspressoBot Access Request&body=Hi Pranav,%0A%0AI would like to request access to EspressoBot.%0A%0AMy email: ' + user.email;
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <img
            className="mx-auto h-24 w-auto mb-8"
            src={logo}
            alt="EspressoBot"
          />
          <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-100 mb-4">
            Welcome to EspressoBot
          </h1>
          <p className="text-xl text-zinc-600 dark:text-zinc-400">
            iDrinkCoffee.com's AI-Powered E-commerce Assistant
          </p>
        </div>

        <div className="bg-white dark:bg-zinc-800 rounded-lg shadow-lg p-8 mb-8">
          <div className="text-center">
            <MessageSquareIcon className="h-16 w-16 text-indigo-500 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
              Early Access Required
            </h2>
            <p className="text-lg text-zinc-600 dark:text-zinc-400 mb-6">
              Hi {user.name || user.email.split('@')[0]}! 👋
            </p>
            <p className="text-zinc-600 dark:text-zinc-400 mb-8">
              EspressoBot is currently in limited testing with senior management. 
              We're excited to have you here, but you'll need access approval to start using the system.
            </p>
            
            <div className="space-y-4">
              <Button
                onClick={handleContactPranav}
                color="indigo"
                className="w-full sm:w-auto"
              >
                <MessageSquareIcon className="h-5 w-5 mr-2" />
                Contact Pranav for Access
              </Button>
              
              <div className="text-sm text-zinc-500 dark:text-zinc-400">
                or reach out on Slack
              </div>
            </div>
          </div>
        </div>

        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-indigo-900 dark:text-indigo-300 mb-2">
            What is EspressoBot?
          </h3>
          <ul className="space-y-2 text-indigo-800 dark:text-indigo-400">
            <li>• AI-powered assistant for managing our Shopify store</li>
            <li>• Search products, update pricing, and manage inventory</li>
            <li>• Create combos and special listings with natural language</li>
            <li>• Integrated with our tools and workflows</li>
          </ul>
        </div>

        <div className="text-center">
          <Button
            onClick={onLogout}
            outline
            small
            className="mx-auto"
          >
            <LogOutIcon className="h-4 w-4 mr-1" />
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
};

export default RestrictedPage;