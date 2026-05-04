import { Play, SquareSquare, StopCircle } from 'lucide-react';
import { useLogs } from '../hooks/useLogs';
import { LogConsole } from '../components/LogConsole';
import axios from 'axios';

export function Tasks() {
  const { logs, isConnected, clearLogs } = useLogs('ws://127.0.0.1:8000/ws/logs');

  const startSpider = async (section: string) => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/spider', { section });
    } catch (error) {
      console.error('Failed to start spider:', error);
    }
  };

  const stopSpider = async () => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/stop');
    } catch (error) {
      console.error('Failed to stop spider:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <SquareSquare className="w-5 h-5 text-primary" />
            任务调度中心
          </h3>
          <button 
            onClick={stopSpider}
            className="flex items-center gap-2 bg-rose-500 hover:bg-rose-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
          >
            <StopCircle className="w-4 h-4" /> 强制终止当前任务
          </button>
        </div>
        <p className="text-slate-500 mb-6 text-sm">
          在此处手动触发后台爬虫任务。任务将在服务器后台异步运行，不阻塞当前页面。
        </p>

        <div className="flex flex-wrap gap-4">
          <button 
            onClick={() => startSpider('4k')}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
          >
            <Play className="w-4 h-4" /> 启动 4K 爬取
          </button>
          <button 
            onClick={() => startSpider('vr')}
            className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
          >
            <Play className="w-4 h-4" /> 启动 VR 爬取
          </button>
          <button 
            onClick={() => startSpider('hd')}
            className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
          >
            <Play className="w-4 h-4" /> 启动 HD 爬取
          </button>
          <button 
            onClick={() => startSpider('sub')}
            className="flex items-center gap-2 bg-rose-500 hover:bg-rose-600 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
          >
            <Play className="w-4 h-4" /> 启动字幕爬取
          </button>
        </div>
      </div>

      <LogConsole logs={logs} isConnected={isConnected} onClear={clearLogs} />
    </div>
  );
}
