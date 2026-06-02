import { useState } from 'react';
import { Target, Search, Loader2, Download, ExternalLink, Clock, HardDrive, ListFilter } from 'lucide-react';
import { clsx } from 'clsx';
import axios from 'axios';

interface SniperResult {
  title: string;
  href: string;
  forum: string;
  date: string;
  size: string;
}

export function Sniper() {
  const [code, setCode] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SniperResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [downloadingUrl, setDownloadingUrl] = useState<string | null>(null);

  const handleSearch = async (searchCode: string = code) => {
    if (!searchCode.trim()) return;
    
    setIsSearching(true);
    setHasSearched(true);
    setResults([]);
    
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/tasks/sniper/search?code=${encodeURIComponent(searchCode.trim())}`);
      if (res.data.status === 'success') {
        setResults(res.data.results);
      } else {
        alert('搜索失败: ' + res.data.message);
      }
    } catch (error: any) {
      console.error('Sniper search error', error);
      alert('请求超时或网络异常，请确保论坛后端正常连通。');
    } finally {
      setIsSearching(false);
    }
  };

  const handleDownload = async (result: SniperResult) => {
    if (!confirm(`【定点狙击确认】\n\n即将对以下目标执行 100% 物理突破下载：\n${result.title}\n\n该操作将派发给底层的死链特遣队执行，是否继续？`)) {
      return;
    }
    
    setDownloadingUrl(result.href);
    try {
      let section = '4k';
      const forumText = result.forum.toLowerCase();
      const titleText = result.title.toLowerCase();
      
      if (forumText.includes('4k') || titleText.includes('4k')) section = '4k';
      else if (forumText.includes('vr') || titleText.includes('vr')) section = 'vr';
      else if (forumText.includes('字') || titleText.includes('字')) section = 'sub';
      else section = 'hd';
      
      const res = await axios.post(`http://127.0.0.1:8000/api/tasks/sniper/download`, {
        href: result.href,
        code: code.trim(),
        title: result.title,
        section: section
      });
      
      if (res.data.status === 'started') {
        alert(res.data.message + '\n\n请前往【任务调度中心】的日志大盘查看物理下载实况！');
      }
    } catch (error: any) {
      alert('发送狙击指令失败: ' + error.message);
    } finally {
      setDownloadingUrl(null);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      
      {/* 顶部作战面板 */}
      <div className="bg-slate-900 rounded-2xl p-8 shadow-xl text-white relative overflow-hidden flex flex-col items-center text-center justify-center min-h-[220px]">
         {/* 瞄准镜背景特效 */}
         <div className="absolute inset-0 opacity-[0.03] pointer-events-none flex items-center justify-center">
            <div className="w-96 h-96 border-[4px] border-emerald-500 rounded-full flex items-center justify-center">
               <div className="w-full h-[1px] bg-emerald-500 absolute"></div>
               <div className="h-full w-[1px] bg-emerald-500 absolute"></div>
               <div className="w-64 h-64 border-[2px] border-emerald-500 rounded-full border-dashed"></div>
            </div>
         </div>
         
         <div className="relative z-10 flex flex-col items-center w-full max-w-2xl">
             <div className="bg-rose-500/20 text-rose-300 p-3 rounded-full mb-4 ring-1 ring-rose-500/30">
               <Target className="w-8 h-8" />
             </div>
             <h2 className="text-2xl font-black mb-2 tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-orange-300">
               精准狙击中心 (SNIPER CONSOLE)
             </h2>
             <p className="text-slate-400 text-sm mb-8 w-3/4">
               剥夺爬虫的自动仲裁权。直接连通论坛深层检索网络，将所有压制版本平铺于眼前，由你这名终极收藏家来行使最终的生杀大权。
             </p>
             
             <div className="flex items-center w-full bg-white/5 border border-white/10 rounded-xl p-1.5 shadow-2xl backdrop-blur-md focus-within:ring-2 focus-within:ring-rose-500/50 transition-all">
                <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0" />
                <input 
                   type="text"
                   value={code}
                   onChange={e => setCode(e.target.value.toUpperCase())}
                   onKeyDown={e => e.key === 'Enter' && handleSearch()}
                   placeholder="请输入目标番号 (例如: IPZZ-856) ..."
                   className="flex-1 bg-transparent border-none outline-none text-white px-4 py-3 placeholder:text-slate-500 font-mono tracking-wider"
                />
                <button 
                   onClick={() => handleSearch()}
                   disabled={!code.trim() || isSearching}
                   className="flex items-center gap-2 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white px-8 py-3 rounded-lg font-bold tracking-widest transition-all disabled:opacity-50 disabled:grayscale shadow-[0_0_15px_rgba(225,29,72,0.4)] hover:shadow-[0_0_25px_rgba(225,29,72,0.6)]"
                >
                   {isSearching ? <Loader2 className="w-5 h-5 animate-spin" /> : 'LOCK ON'}
                </button>
             </div>
         </div>
      </div>

      {/* 搜索结果展示区 */}
      {hasSearched && (
        <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
               <ListFilter className="w-5 h-5 text-slate-400" />
               <h3 className="font-bold text-slate-700">战术雷达扫描报告</h3>
            </div>
            <div className="text-sm text-slate-500">
               发现 <span className="font-bold text-rose-500">{results.length}</span> 个疑似目标
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2">
            {isSearching ? (
               <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-4">
                 <Loader2 className="w-10 h-10 animate-spin text-rose-500" />
                 <div className="animate-pulse tracking-widest text-sm">正在深度接驳论坛检索网络...</div>
               </div>
            ) : results.length === 0 ? (
               <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                 <Target className="w-12 h-12 opacity-20 mb-2" />
                 <div className="font-medium">目标已丢失或不存在</div>
                 <div className="text-xs opacity-70">雷达未能扫描到任何相关的论坛发帖记录</div>
               </div>
            ) : (
               <div className="grid grid-cols-1 gap-3 p-4">
                 {results.map((res, idx) => (
                   <div key={idx} className="group bg-white border border-slate-200 hover:border-rose-300 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all shadow-sm hover:shadow-md">
                      <div className="flex-1 min-w-0 flex flex-col gap-2">
                         <a 
                           href={res.href.startsWith('http') ? res.href : `https://x999x.me/${res.href}`} 
                           target="_blank" 
                           rel="noreferrer"
                           className="font-bold text-slate-800 hover:text-blue-600 truncate transition-colors flex items-center gap-2"
                         >
                           {res.title}
                           <ExternalLink className="w-3.5 h-3.5 opacity-50 shrink-0" />
                         </a>
                         
                         <div className="flex flex-wrap items-center gap-3 text-xs">
                            <span className={clsx(
                              "px-2.5 py-1 rounded-md font-semibold tracking-wider",
                              res.forum.includes("4K") ? "bg-amber-100 text-amber-700 border border-amber-200" :
                              res.forum.includes("VR") ? "bg-purple-100 text-purple-700 border border-purple-200" :
                              "bg-blue-100 text-blue-700 border border-blue-200"
                            )}>
                              {res.forum}
                            </span>
                            
                            {res.size && (
                              <span className="flex items-center gap-1 text-slate-500 bg-slate-100 px-2 py-1 rounded border border-slate-200">
                                <HardDrive className="w-3.5 h-3.5" />
                                {res.size}
                              </span>
                            )}
                            
                            <span className="flex items-center gap-1 text-slate-400">
                              <Clock className="w-3.5 h-3.5" />
                              {res.date || "未知时间"}
                            </span>
                         </div>
                      </div>
                      
                      <div className="shrink-0 flex items-center justify-end">
                         <button
                           onClick={() => handleDownload(res)}
                           disabled={downloadingUrl === res.href}
                           className="flex items-center gap-2 px-6 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                         >
                           {downloadingUrl === res.href ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                           狙击下载
                         </button>
                      </div>
                   </div>
                 ))}
               </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}