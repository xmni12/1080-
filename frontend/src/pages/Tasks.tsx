import { useState, useEffect } from 'react';
import { SquareSquare, StopCircle, ShieldCheck, KeyRound, Zap, Pickaxe, ListOrdered, XCircle, Loader2, Globe } from 'lucide-react';
import { useLogs } from '../hooks/useLogs';
import { LogConsole } from '../components/LogConsole';
import axios from 'axios';
import { clsx } from 'clsx';

export function Tasks() {
  const [queueStatus, setQueueStatus] = useState<{ running: any[], queued: any[] }>({ running: [], queued: [] });
  const { logs, isConnected, clearLogs } = useLogs('ws://127.0.0.1:8000/ws/logs', (data) => {
    setQueueStatus(data);
  });

  useEffect(() => {
    fetchQueueStatus();
    // Optional: we can still poll as a fallback, but let's reduce frequency since WS handles it instantly
    const interval = setInterval(fetchQueueStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchQueueStatus = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/tasks/queue');
      setQueueStatus(res.data);
    } catch (error) {
      console.error('Failed to fetch queue status', error);
    }
  };

  const removeQueuedTask = async (section: string, mode: string) => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/queue/remove', { section, mode });
      fetchQueueStatus();
    } catch (error) {
      console.error('Failed to remove task from queue', error);
    }
  };

  const startSpider = async (section: string, mode: 'new' | 'archive' = 'new') => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/spider', { section, mode });
      fetchQueueStatus();
    } catch (error) {
      console.error('Failed to start spider:', error);
    }
  };

  const stopSpider = async () => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/stop');
      fetchQueueStatus();
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

  const openSandbox = async () => {
    try {
      await axios.post('http://127.0.0.1:8000/api/tasks/sandbox');
    } catch (error) {
      console.error('Failed to trigger sandbox browser:', error);
    }
  };

  const colorMap: Record<string, any> = {
    emerald: {
      wrapper: "border-emerald-100 bg-emerald-50/30",
      title: "text-emerald-700",
      btn1: "bg-emerald-500 hover:bg-emerald-600",
      btn2: "bg-emerald-600 hover:bg-emerald-700"
    },
    cyan: {
      wrapper: "border-cyan-100 bg-cyan-50/30",
      title: "text-cyan-700",
      btn1: "bg-cyan-500 hover:bg-cyan-600",
      btn2: "bg-cyan-600 hover:bg-cyan-700"
    },
    blue: {
      wrapper: "border-blue-100 bg-blue-50/30",
      title: "text-blue-700",
      btn1: "bg-blue-500 hover:bg-blue-600",
      btn2: "bg-blue-600 hover:bg-blue-700"
    },
    rose: {
      wrapper: "border-rose-100 bg-rose-50/30",
      title: "text-rose-700",
      btn1: "bg-rose-500 hover:bg-rose-600",
      btn2: "bg-rose-600 hover:bg-rose-700"
    }
  };

  const renderSectionButtons = (title: string, section: string, color: string) => {
    const theme = colorMap[color] || colorMap.blue;
    return (
    <div className={`flex flex-col gap-2 p-4 rounded-xl border ${theme.wrapper}`}>
      <h4 className={`text-sm font-bold ${theme.title} text-center mb-1 uppercase tracking-wider`}>{title} 版块</h4>
      <div className="flex gap-2">
        <button 
          onClick={() => startSpider(section, 'new')}
          className={clsx(`flex-1 flex items-center justify-center gap-1.5 ${theme.btn1} text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm`)}
          title="从第 1 页开始抓取，设定深度内自动停止"
        >
          <Zap className="w-4 h-4" /> 极速追新
        </button>
        <button 
          onClick={() => startSpider(section, 'archive')}
          className={clsx(`flex-1 flex items-center justify-center gap-1.5 ${theme.btn2} text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm`)}
          title="从历史最大页码开始深度补漏"
        >
          <Pickaxe className="w-4 h-4" /> 深度考古
        </button>
      </div>
    </div>
  )};

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <SquareSquare className="w-5 h-5 text-primary" />
            任务调度中心
          </h3>
          <div className="flex flex-wrap gap-3">
            <button 
              onClick={openSandbox}
              className="flex items-center gap-2 bg-sky-500 hover:bg-sky-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
              title="纯净沙盒模式：无时间限制、无干预，用于挂机养号或手动过盾"
            >
              <Globe className="w-4 h-4" /> 开启指纹浏览器漫游
            </button>
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
          在此处手动触发后台爬虫任务。<b>极速追新</b>：从第 1 页开始，按设置深度自动停止；<b>深度考古</b>：从设置中的历史页码开始，结束时自动保存最大水位。手动触发的任务拥有 <b>VIP 优先插队权</b>。
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {renderSectionButtons('4K 超清', '4k', 'emerald')}
          {renderSectionButtons('VR 视频', 'vr', 'cyan')}
          {renderSectionButtons('HD 高清', 'hd', 'blue')}
          {renderSectionButtons('外挂字幕', 'sub', 'rose')}
        </div>
      </div>

      {/* 可视化任务列车大屏 */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <ListOrdered className="w-5 h-5 text-primary" />
          任务列车大屏
        </h3>
        
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-bold text-slate-500 mb-2">正在运行</h4>
            <div className="flex flex-wrap gap-3">
              {queueStatus.running.length === 0 ? (
                <div className="text-sm text-slate-400 italic bg-slate-50 px-4 py-2 rounded-lg border border-slate-100">当前没有正在运行的爬虫</div>
              ) : (
                queueStatus.running.map((task, i) => (
                  <div key={i} className="flex items-center gap-2 bg-primary/10 border border-primary/20 text-primary px-4 py-2 rounded-lg font-medium text-sm animate-pulse">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    [{task.section_key}] 版块作业中...
                  </div>
                ))
              )}
            </div>
          </div>
          
          <div className="pt-2 border-t border-slate-100">
            <h4 className="text-sm font-bold text-slate-500 mb-2">排队等待中</h4>
            <div className="flex flex-col gap-2">
              {queueStatus.queued.length === 0 ? (
                <div className="text-sm text-slate-400 italic bg-slate-50 px-4 py-2 rounded-lg border border-slate-100">排队队列为空</div>
              ) : (
                queueStatus.queued.map((task, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-slate-400 bg-white border border-slate-200 px-2 py-0.5 rounded-md">#{i + 1}</span>
                      <span className="font-bold text-slate-700 uppercase">[{task.section_key}]</span>
                      <span className="text-sm text-slate-600">{task.mode === 'new' ? '极速追新' : '深度考古'}</span>
                      {task.is_vip && <span className="text-xs font-bold text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded shadow-sm">⭐ VIP 插队</span>}
                    </div>
                    <button 
                      onClick={() => removeQueuedTask(task.section_key, task.mode)}
                      className="text-slate-400 hover:text-rose-500 transition-colors"
                      title="从队列中踢出该任务"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <LogConsole logs={logs} isConnected={isConnected} onClear={clearLogs} />
    </div>
  );
}
