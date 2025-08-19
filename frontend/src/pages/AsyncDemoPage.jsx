import React, { useState } from 'react';
import { useAsyncBackend } from '../hooks/useAsyncBackend';

export default function AsyncDemoPage() {
  const [message, setMessage] = useState('');
  const [conversationId, setConversationId] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState(null);
  
  const {
    sendAsyncMessage,
    cancelTask,
    loading,
    taskStatus,
    taskResponse,
    taskProgress,
    error,
  } = useAsyncBackend();

  const handleSendMessage = async () => {
    if (!message.trim()) return;
    
    try {
      const result = await sendAsyncMessage(message, conversationId);
      setCurrentTaskId(result.task_id);
      setConversationId(result.conversation_id);
    } catch (err) {
      console.error('Send message error:', err);
    }
  };

  const handleCancel = () => {
    if (currentTaskId) {
      cancelTask(currentTaskId);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-yellow-600';
      case 'running': return 'text-blue-600';
      case 'completed': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'cancelled': return 'text-gray-600';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🚀 EspressoBot Async Processing Demo
        </h1>
        <p className="text-gray-600 mb-8">
          Test the new async background processing - no more blocking! Multiple tabs can work simultaneously.
        </p>

        {/* Input Section */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Message
          </label>
          <div className="flex gap-4">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask me anything... (e.g., 'check sales today and traffic')"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !message.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Send Async'}
            </button>
          </div>
          
          {conversationId && (
            <p className="text-sm text-gray-500 mt-2">
              Conversation ID: {conversationId}
            </p>
          )}
        </div>

        {/* Status Section */}
        {(taskStatus || error) && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Status</h3>
            
            <div className="bg-gray-50 rounded-lg p-4">
              {error ? (
                <div className="text-red-600">
                  <strong>Error:</strong> {error}
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className={`font-semibold ${getStatusColor(taskStatus)}`}>
                        Status: {taskStatus?.toUpperCase() || 'UNKNOWN'}
                      </span>
                      {currentTaskId && (
                        <span className="text-sm text-gray-500">
                          Task ID: {currentTaskId}
                        </span>
                      )}
                    </div>
                    
                    {taskStatus === 'running' && (
                      <button
                        onClick={handleCancel}
                        className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                      >
                        Cancel
                      </button>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {taskStatus === 'running' && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{Math.round(taskProgress * 100)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${taskProgress * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {/* Response */}
                  {taskResponse && (
                    <div className="mt-4">
                      <h4 className="font-semibold text-gray-900 mb-2">Response:</h4>
                      <div className="bg-white border rounded-lg p-4 text-gray-800 whitespace-pre-wrap">
                        {taskResponse}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* Demo Instructions */}
        <div className="bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">🧪 How to Test</h3>
          <div className="space-y-2 text-blue-800">
            <p><strong>1. Single Tab Test:</strong> Send a message and watch real-time progress updates</p>
            <p><strong>2. Multiple Tab Test:</strong> Open this page in multiple browser tabs and send messages simultaneously</p>
            <p><strong>3. Cross-Tab Test:</strong> While a task runs in one tab, try using the dashboard or conversations in another tab</p>
            <p><strong>4. Cancel Test:</strong> Start a task and cancel it mid-processing</p>
          </div>
          
          <div className="mt-4 p-4 bg-white rounded border">
            <h4 className="font-semibold text-gray-900 mb-2">Try these example messages:</h4>
            <div className="space-y-1 text-sm text-gray-600">
              <div>• "Check sales today and website traffic"</div>
              <div>• "Find products with inventory issues"</div>
              <div>• "Analyze pricing for espresso machines"</div>
              <div>• "Test multiple agent coordination"</div>
            </div>
          </div>
        </div>

        {/* Technical Info */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">⚡ Performance Benefits</h3>
          <div className="grid md:grid-cols-2 gap-6 text-sm">
            <div>
              <h4 className="font-semibold text-green-600 mb-2">✅ With Async Processing</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Response time: ~0.004s</li>
                <li>• Multiple tabs work simultaneously</li>
                <li>• Background task processing</li>
                <li>• Real-time progress updates</li>
                <li>• No browser blocking</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-red-600 mb-2">❌ Before (Blocking)</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Response time: 6+ seconds</li>
                <li>• Only one tab usable at a time</li>
                <li>• Browser freezes during processing</li>
                <li>• No progress feedback</li>
                <li>• Database connection conflicts</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}