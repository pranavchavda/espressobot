"use client";

import { PanelSection } from "./panel-section";
import { Card, CardContent } from "@/components/ui/card";
import { BookText } from "lucide-react";

interface ConversationContextProps {
  context: {
    store_name?: string;
    product_id?: string;
    product_title?: string;
    sku?: string;
    search_query?: string;
    selected_products?: string[];
    order_id?: string;
    customer_email?: string;
    last_operation?: string;
    [key: string]: any;
  };
}

export function ConversationContext({ context }: ConversationContextProps) {
  return (
    <PanelSection
      title="Conversation Context"
      icon={<BookText className="h-4 w-4 text-amber-700" />}
    >
      <Card className="bg-gradient-to-r from-white to-gray-50 border-gray-200 shadow-sm">
        <CardContent className="p-3">
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(context).map(([key, value]) => {
              // Skip complex objects that we don't want to display
              if (key === 'filter_criteria' || key === 'task_context' || key === 'operation_results') {
                return null;
              }
              
              // Format the value for display
              let displayValue = value;
              if (Array.isArray(value)) {
                displayValue = value.length > 0 ? value.join(', ') : 'none';
              } else if (typeof value === 'object' && value !== null) {
                displayValue = JSON.stringify(value);
              } else if (value === null || value === undefined || value === '') {
                displayValue = 'null';
              }
              
              return (
                <div
                  key={key}
                  className="flex items-center gap-2 bg-white p-2 rounded-md border border-gray-200 shadow-sm transition-all"
                >
                  <div className="w-2 h-2 rounded-full bg-amber-600"></div>
                  <div className="text-xs">
                    <span className="text-zinc-500 font-light">{key.replace(/_/g, ' ')}:</span>{" "}
                    <span
                      className={
                        value && value !== 'null'
                          ? "text-zinc-900 font-light"
                          : "text-gray-400 italic"
                      }
                    >
                      {displayValue}
                    </span>
                  </div>
                </div>
              );
            }).filter(Boolean)}
          </div>
        </CardContent>
      </Card>
    </PanelSection>
  );
}