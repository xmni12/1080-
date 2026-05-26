import { useEffect, useRef, useState, useCallback } from 'react';
import type { LogMessage } from '../hooks/useLogs';
import { clsx } from 'clsx';
import { Terminal, Trash2, Search, Lock, Unlock } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';

interface LogConsoleProps {
  logs: LogMessage[];
  onClear: () => void;
  isConnected: boolean;
}

type FilterType = 'all' | 'error' | 'success' | 'warn';

export function LogConsole({ logs, onClear, isConnected }: LogConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // 智能冻结滚动状态
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  const filteredLogs = logs.filter(log => {
    if (searchQuery.trim() !== '') {
      if (!log.content.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
    }
    if (filter === 'all') return true;
    if (filter === 'error') return log.level === 'error';
    if (filter === 'success') return log.level === 'success';
    if (filter === 'warn') return log.level === 'warn';
    return true;
  });

  // 虚拟滚动配置
  const rowVirtualizer = useVirtualizer({
    count: filteredLogs.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 24, // 预估单行高度，提升计算性能
    overscan: 10,
  });

  // 监听日志更新并自动滚动
  useEffect(() => {
    if (isAutoScroll && filteredLogs.length > 0) {
      rowVirtualizer.scrollToIndex(filteredLogs.length - 1, { align: 'end' });
    }
  }, [filteredLogs.length, isAutoScroll, rowVirtualizer]);

  // 监听用户手动滚动以触发冻结
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    
    // 如果用户向上滚动超过 20px，则锁定冻结；如果拉到了最底部，则解除冻结恢复自动跟随
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 20;
    if (isAtBottom && !isAutoScroll) {
      setIsAutoScroll(true);
    } else if (!isAtBottom && isAutoScroll) {
      setIsAutoScroll(false);
    }
  }, [isAutoScroll]);

  return (
    <div className="flex flex-col bg-[#1e1e1e] rounded-xl overflow-hidden shadow-lg border border-slate-700 h-[500px]">
      <div className="flex items-center justify-between px-4 py-3 bg-[#2d2d2d] border-b border-slate-700">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">实时任务日志控制台</span>
            <span className={clsx(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            )}></span>
          </div>
          
          <div className="relative flex items-center ml-4">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-slate-500" />
            <input 
              type="text"
              placeholder="雷达搜索 (例如 HTM-108)..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs bg-[#1e1e1e] text-slate-300 border border-slate-600 rounded-md outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all w-56 placeholder-slate-600"
            />
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
                setIsAutoScroll(!isAutoScroll);
                if (!isAutoScroll && filteredLogs.length > 0) {
                    rowVirtualizer.scrollToIndex(filteredLogs.length - 1, { align: 'end' });
                }
            }}
            className={clsx(
                "flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-md transition-colors border",
                !isAutoScroll 
                    ? "bg-amber-500/20 text-amber-400 border-amber-500/50 shadow-[0_0_8px_rgba(245,158,11,0.2)] animate-pulse" 
                    : "bg-transparent text-slate-400 border-transparent hover:text-slate-200"
            )}
            title={!isAutoScroll ? "目前已冻结画面，点击恢复自动跟随" : "自动跟随中 (向上滚动滚轮可自动冻结)"}
          >
            {!isAutoScroll ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
            {!isAutoScroll ? "日志已冻结 (防刷屏)" : "跟随最新"}
          </button>

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
              仅报错 ❌
            </button>
            <button
              onClick={() => setFilter('success')}
              className={clsx(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                filter === 'success' ? "bg-green-500/20 text-green-400" : "text-slate-400 hover:text-green-300"
              )}
            >
              仅成功 ✅
            </button>
            <button
              onClick={() => setFilter('warn')}
              className={clsx(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                filter === 'warn' ? "bg-amber-500/20 text-amber-400" : "text-slate-400 hover:text-amber-300"
              )}
            >
              仅拦截/跳过 🚧
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
      
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm relative"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 italic flex h-full items-center justify-center">
            {logs.length === 0 ? "等待任务日志输出..." : "当前筛选条件下无日志"}
          </div>
        ) : (
          <div
            style={{
              height: `${rowVirtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const log = filteredLogs[virtualRow.index];
              return (
                <div
                  key={virtualRow.key}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className="flex gap-3 hover:bg-white/5 px-2 rounded transition-colors group items-center"
                >
                  <span className="text-slate-500 shrink-0">[{log.timestamp}]</span>
                  <span className={clsx(
                    "shrink-0 font-semibold w-12",
                    log.level === 'info' && "text-blue-400",
                    log.level === 'warn' && "text-amber-400",
                    log.level === 'error' && "text-red-400",
                    log.level === 'success' && "text-green-400"
                  )}>
                    {log.level.toUpperCase()}
                  </span>
                  <span className={clsx(
                    "break-all flex-1",
                    log.level === 'error' && "text-red-300",
                    log.level === 'warn' && "text-amber-300",
                    log.level !== 'error' && log.level !== 'warn' && "text-slate-300"
                  )}>
                    {log.content}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}