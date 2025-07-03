import React from 'react';
import { Button } from '@common/button';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

/**
 * ApprovalRequest Component
 * 
 * Displays a pending operation that requires user approval.
 * Implements the human-in-the-loop pattern from OpenAI Agents JS.
 */
export function ApprovalRequest({ 
  operation, 
  onApprove, 
  onReject, 
  isProcessing = false 
}) {
  const { 
    type, 
    description, 
    impact, 
    details,
    riskLevel = 'medium' 
  } = operation;

  const getRiskIcon = () => {
    switch (riskLevel) {
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default:
        return <CheckCircle className="w-5 h-5 text-blue-500" />;
    }
  };

  const getRiskBorderColor = () => {
    switch (riskLevel) {
      case 'high':
        return 'border-red-300 bg-red-50';
      case 'medium':
        return 'border-yellow-300 bg-yellow-50';
      default:
        return 'border-blue-300 bg-blue-50';
    }
  };

  return (
    <div className={`border rounded-lg p-4 mb-4 ${getRiskBorderColor()}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 mt-1">
          {getRiskIcon()}
        </div>
        <div className="flex-grow">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Approval Required: {type}
          </h3>
          <p className="text-sm text-gray-700 mb-2">
            {description}
          </p>
          
          {impact && (
            <div className="text-sm text-gray-600 mb-2">
              <span className="font-medium">Impact:</span> {impact}
            </div>
          )}
          
          {details && (
            <div className="mt-2 p-2 bg-white bg-opacity-50 rounded border border-gray-200">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                {typeof details === 'string' ? details : JSON.stringify(details, null, 2)}
              </pre>
            </div>
          )}
          
          <div className="flex space-x-2 mt-3">
            <Button
              onClick={onApprove}
              disabled={isProcessing}
              className="flex items-center space-x-1 bg-green-600 hover:bg-green-700 text-white"
              size="sm"
            >
              <CheckCircle className="w-4 h-4" />
              <span>Approve</span>
            </Button>
            <Button
              onClick={onReject}
              disabled={isProcessing}
              className="flex items-center space-x-1 bg-red-600 hover:bg-red-700 text-white"
              size="sm"
            >
              <XCircle className="w-4 h-4" />
              <span>Reject</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ApprovalHistory Component
 * 
 * Shows a compact history of recent approvals/rejections
 */
export function ApprovalHistory({ history }) {
  if (!history || history.length === 0) return null;

  return (
    <div className="text-xs text-gray-500 mt-2">
      <div className="flex items-center space-x-2">
        <span>Recent decisions:</span>
        {history.slice(-3).map((item, idx) => (
          <span key={idx} className="flex items-center">
            {item.approved ? (
              <CheckCircle className="w-3 h-3 text-green-500" />
            ) : (
              <XCircle className="w-3 h-3 text-red-500" />
            )}
          </span>
        ))}
      </div>
    </div>
  );
}