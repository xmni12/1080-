import { Play, SquareSquare, StopCircle, ShieldCheck, KeyRound, Zap, Pickaxe } from 'lucide-react';
import { useLogs } from '../hooks/useLogs';
import { LogConsole } from '../components/LogConsole';
import axios from 'axios';
import { clsx } from 'clsx';

export function Tasks() {
  const { logs, isConnected, clearLogs } = useLogs('ws://127.0.0.1:8000/ws/logs');

  const startSpider = async (section: string, mode: 'new' | 'archive' = 'new') => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/spider', { section, mode });
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

  const getCfClearance = async () => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/cf_clearance');
    } catch (error) {
      console.error('Failed to trigger CF clearance:', error);
    }
  };

  const authorizeLogin = async () => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/authorize');
    } catch (error) {
      console.error('Failed to trigger authorize login:', error);
    }
  };

  const renderSectionButtons = (title: string, section: string, color: string, hoverColor: string) => (
    <div className={`flex flex-col gap-2 p-4 rounded-xl border border-${color}-100 bg-${color}-50/30`}>
      <h4 className={`text-sm font-bold text-${color}-700 text-center mb-1 uppercase tracking-wider`}>{title} 版块</h4>
      <div className="flex gap-2">
        <button 
          onClick={() => startSpider(section, 'new')}
          className={clsx(`flex-1 flex items-center justify-center gap-1.5 bg-${color}-500 hover:bg-${color}-600 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm`)}
          title="从第 1 页开始抓取，遇到连续旧贴自动刹车"
        >
          <Zap className="w-4 h-4" /> 极速追新
        </button>
        <button 
          onClick={() => startSpider(section, 'archive')}
          className={clsx(`flex-1 flex items-center justify-center gap-1.5 bg-${color}-600 hover:bg-${color}-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm`)}
          title="从历史最大页码开始深度补漏"
        >
          <Pickaxe className="w-4 h-4" /> 深度考古
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <SquareSquare className="w-5 h-5 text-primary" />
            任务调度中心
          </h3>
          <div className="flex gap-3">
            <button 
              onClick={authorizeLogin}
              className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
            >
              <KeyRound className="w-4 h-4" /> 账号登录 / 状态接管
            </button>
            <button 
              onClick={getCfClearance}
              className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
            >
              <ShieldCheck className="w-4 h-4" /> 获取长效 CF 绿卡
            </button>
            <button 
              onClick={stopSpider}
              className="flex items-center gap-2 bg-rose-500 hover:bg-rose-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
            >
              <StopCircle className="w-4 h-4" /> 强制终止当前任务
            </button>
          </div>
        </div>
        <p className="text-slate-500 mb-6 text-sm">
          在此处手动触发后台爬虫任务。<b>极速追新</b>：从第 1 页开始，连续遇到 20 个老番号自动停止；<b>深度考古</b>：从设置中的历史页码开始抓取老帖，结束时自动保存最大页码。
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {renderSectionButtons('4K 超清', '4k', 'emerald', 'emerald')}
          {renderSectionButtons('VR 视频', 'vr', 'cyan', 'cyan')}
          {renderSectionButtons('HD 高清', 'hd', 'blue', 'blue')}
          {renderSectionButtons('外挂字幕', 'sub', 'rose', 'rose')}
        </div>
      </div>

      <LogConsole logs={logs} isConnected={isConnected} onClear={clearLogs} />
    </div>
  );
}
