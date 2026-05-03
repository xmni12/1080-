import { useEffect, useRef } from 'react';
import type { LogMessage } from '../hooks/useLogs';
import { clsx } from 'clsx';
import { Terminal, Trash2 } from 'lucide-react';

interface LogConsoleProps {
  logs: LogMessage[];
  onClear: () => void;
  isConnected: boolean;
}

export function LogConsole({ logs, onClear, isConnected }: LogConsoleProps) {
  const endOfLogsRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    endOfLogsRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

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
        <button 
          onClick={onClear}
          className="text-slate-400 hover:text-white transition-colors"
          title="清空日志"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
        {logs.length === 0 ? (
          <div className="text-slate-500 italic">等待任务日志输出...</div>
        ) : (
          <div className="space-y-1.5">
            {logs.map(log => (
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
