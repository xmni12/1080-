import { useEffect, useRef, useState } from 'react';
import type { LogMessage } from '../hooks/useLogs';
import { clsx } from 'clsx';
import { Terminal, Trash2 } from 'lucide-react';

interface LogConsoleProps {
  logs: LogMessage[];
  onClear: () => void;
  isConnected: boolean;
}

type FilterType = 'all' | 'error' | 'success';

export function LogConsole({ logs, onClear, isConnected }: LogConsoleProps) {
  const endOfLogsRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<FilterType>('all');

  // 自动滚动到底部
  useEffect(() => {
    endOfLogsRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, filter]);

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    if (filter === 'error') return log.level === 'error' || log.level === 'warn';
    if (filter === 'success') return log.level === 'success';
    return true;
  });

  return (
    <div className="flex flex-col bg-[#1e1e1e] rounded-xl overflow-hidden shadow-lg border border-slate-700 h-[500px]">
      <div className="flex items-center justify-between px-4 py-3 bg-[#2d2d2d] border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">实时任务日志控制台</span>
          <span className={clsx(
            "ml-2 w-2 h-2 rounded-full",
            isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
          )}></span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center bg-[#1e1e1e] rounded-lg p-1 border border-slate-600">
            <button
              onClick={() => setFilter('all')}
              className={clsx(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                filter === 'all' ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
              )}
            >
              全部
            </button>
            <button
              onClick={() => setFilter('error')}
              className={clsx(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                filter === 'error' ? "bg-red-500/20 text-red-400" : "text-slate-400 hover:text-red-300"
              )}
            >
              仅警告/错误
            </button>
            <button
              onClick={() => setFilter('success')}
              className={clsx(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                filter === 'success' ? "bg-green-500/20 text-green-400" : "text-slate-400 hover:text-green-300"
              )}
            >
              仅成功
            </button>
          </div>
          <button 
            onClick={onClear}
            className="text-slate-400 hover:text-white transition-colors"
            title="清空日志"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 italic">
            {logs.length === 0 ? "等待任务日志输出..." : "当前筛选条件下无日志"}
          </div>
        ) : (
          <div className="space-y-1.5">
            {filteredLogs.map(log => (
              <div key={log.id} className="flex gap-3 hover:bg-white/5 px-2 py-0.5 rounded transition-colors">
                <span className="text-slate-500 shrink-0">[{log.timestamp}]</span>
                <span className={clsx(
                  "shrink-0 font-semibold w-12",
                  log.level === 'info' && "text-blue-400",
                  log.level === 'warn' && "text-yellow-400",
                  log.level === 'error' && "text-red-400",
                  log.level === 'success' && "text-green-400"
                )}>
                  {log.level.toUpperCase()}
                </span>
                <span className={clsx(
                  "break-all",
                  log.level === 'error' ? "text-red-300" : "text-slate-300"
                )}>
                  {log.content}
                </span>
              </div>
            ))}
            <div ref={endOfLogsRef} />
          </div>
        )}
      </div>
    </div>
  );
}