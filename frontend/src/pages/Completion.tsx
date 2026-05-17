import { useState } from 'react';
import { Rocket, Link as LinkIcon, ShieldCheck, Film, PlayCircle, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
// import axios from 'axios'; // We'll need this when backend is ready

export function Completion() {
  const [avbaseUrl, setAvbaseUrl] = useState('https://www.avbase.net/talents/%E7%B3%B8%E4%BA%95%E7%91%A0%E8%8A%B1');
  const [isSyncing, setIsSyncing] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // 模拟的进度与对账数据
  const [syncStatus, setSyncStatus] = useState<any>(null);

  const handleStartSync = () => {
    if (!avbaseUrl.trim()) return;
    setIsSyncing(true);
    
    // 模拟数据对账过程
    setTimeout(() => {
        setSyncStatus({
            actor: '糸井瑠花',
            total_works: 50,
            emby_owned: 32,
            missing: 18,
            missing_codes: ['OFJE-632', 'SSNI-999', 'STARS-111']
        });
        setIsSyncing(false);
    }, 1500);
  };

  const handleStartSearch = () => {
    setIsSearching(true);
    // 模拟启动搜刮
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      
      {/* 顶部面板 */}
      <div className="bg-gradient-to-r from-fuchsia-900 to-purple-800 rounded-2xl p-8 shadow-md text-white flex flex-col md:flex-row items-center justify-between gap-6">
         <div className="flex items-start gap-5">
            <div className="bg-white/10 p-4 rounded-2xl border border-white/20">
               <Rocket className="w-8 h-8 text-fuchsia-300" />
            </div>
            <div>
               <h3 className="text-2xl font-bold mb-2 tracking-wide text-white">女优番号补全计划 (Emby 联动)</h3>
               <p className="text-fuchsia-100/80 text-sm max-w-xl leading-relaxed">
                  输入女优的 AVBase 主页链接。系统将自动抓取其全部作品图鉴，并调用 Emby 媒体库 API 进行底层交叉对账。
                  一键找出本地缺失的番号，并控制无人机前往论坛自动搜刮对应资源（优先级: 4K {'>'} VR {'>'} HD）。
               </p>
            </div>
         </div>
      </div>

      {/* 第一步：输入目标 */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-fuchsia-100 text-fuchsia-700 text-sm">1</span>
            锁定补全目标
        </h4>
        <div className="flex items-center gap-4">
            <div className="relative flex-1">
                <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input 
                    type="text" 
                    value={avbaseUrl}
                    onChange={(e) => setAvbaseUrl(e.target.value)}
                    placeholder="请输入 AVBase 演员主页链接 (例如: https://www.avbase.net/talents/...)"
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition-all font-mono text-sm"
                />
            </div>
            <button 
                onClick={handleStartSync}
                disabled={!avbaseUrl || isSyncing}
                className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-6 py-3 rounded-xl font-medium transition-colors shadow-sm disabled:opacity-50"
            >
                {isSyncing ? <Loader2 className="w-5 h-5 animate-spin" /> : <ShieldCheck className="w-5 h-5" />}
                开始跨界对账
            </button>
        </div>
      </div>

      {/* 第二步：对账大盘 (有数据时显示) */}
      {syncStatus && (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex items-center justify-between mb-6">
            <h4 className="font-bold text-slate-800 flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-fuchsia-100 text-fuchsia-700 text-sm">2</span>
                Emby 对账报告: {syncStatus.actor}
            </h4>
            <button 
                onClick={handleStartSearch}
                disabled={isSearching}
                className="flex items-center gap-2 bg-fuchsia-600 hover:bg-fuchsia-700 text-white px-5 py-2.5 rounded-lg font-bold transition-colors shadow-md shadow-fuchsia-500/20 disabled:opacity-50"
            >
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                立即前往论坛搜刮缺失拼图
            </button>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-5 text-center">
                <div className="text-slate-500 text-sm font-medium mb-1">AVBase 全收集图鉴</div>
                <div className="text-3xl font-black text-slate-700">{syncStatus.total_works} <span className="text-sm font-normal text-slate-400">部</span></div>
            </div>
            <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-5 text-center">
                <div className="text-emerald-600 text-sm font-medium mb-1">Emby 本地已拥有</div>
                <div className="text-3xl font-black text-emerald-600">{syncStatus.emby_owned} <span className="text-sm font-normal text-emerald-400/80">部</span></div>
            </div>
            <div className="bg-rose-50 border border-rose-100 rounded-xl p-5 text-center">
                <div className="text-rose-600 text-sm font-medium mb-1">严重缺失待补全</div>
                <div className="text-3xl font-black text-rose-600">{syncStatus.missing} <span className="text-sm font-normal text-rose-400/80">部</span></div>
            </div>
        </div>

        {/* 缺失番号展示区 */}
        <div>
            <h5 className="text-sm font-bold text-slate-500 mb-3 flex items-center gap-1.5">
                <Film className="w-4 h-4" /> 目标搜刮清单 (Top 3)
            </h5>
            <div className="flex flex-wrap gap-2">
                {syncStatus.missing_codes.map((code: string) => (
                    <span key={code} className="px-3 py-1.5 bg-slate-100 border border-slate-200 text-slate-700 rounded-md text-sm font-bold font-mono shadow-sm">
                        {code}
                    </span>
                ))}
                <span className="px-3 py-1.5 bg-transparent border border-dashed border-slate-300 text-slate-400 rounded-md text-sm font-bold">
                    ...及其他 {syncStatus.missing - 3} 部
                </span>
            </div>
        </div>
      </div>
      )}

      {/* 第三步：实况追踪大屏 (占位) */}
      <div className={clsx("bg-[#1e1e1e] rounded-xl overflow-hidden shadow-lg border border-slate-700 h-80 transition-all duration-500", !isSearching && "opacity-50 grayscale pointer-events-none")}>
        <div className="flex items-center px-4 py-3 bg-[#2d2d2d] border-b border-slate-700">
           <span className="text-sm font-bold text-slate-300">搜刮实况追踪列车</span>
        </div>
        <div className="p-4 font-mono text-sm text-slate-500 flex items-center justify-center h-full">
            {isSearching ? "搜刮雷达扫描中..." : "等待启动搜刮任务..."}
        </div>
      </div>

    </div>
  );
}