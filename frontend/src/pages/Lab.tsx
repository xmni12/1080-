import { useState, useEffect, DragEvent } from 'react';
import { UploadCloud, Image as ImageIcon, Search, ShieldAlert, Trash2, Plus, AlertCircle, FileVideo } from 'lucide-react';
import { clsx } from 'clsx';
import axios from 'axios';

export function Lab() {
  const [isDragging, setIsDragging] = useState(false);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [result, setResult] = useState<any>(null);
  
  const [blacklist, setBlacklist] = useState<string[]>([]);
  const [newActorName, setNewActorName] = useState('');
  const [history, setHistory] = useState<{time: string, msg: string, success: boolean}[]>([]);
  const [probeStatus, setProbeStatus] = useState("正在初始化神经网络探测器...");
  
  useEffect(() => {
    fetchBlacklist();
    
    // 连接 WebSocket 接收实时状态
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/logs');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'lab_status') {
          setProbeStatus(data.message);
        }
      } catch (e) {
        // ignore non-json messages
      }
    };
    
    return () => {
      ws.close();
    };
  }, []);

  const fetchBlacklist = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/lab/blacklist');
      setBlacklist(res.data.map((item: any) => item.name));
    } catch (e) {
      console.error(e);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      simulateRecognition(file.name);
    }
  };

  const simulateRecognition = async (filename: string) => {
    setIsRecognizing(true);
    setResult(null);
    
    try {
        const res = await axios.post('http://127.0.0.1:8000/api/lab/recognize', { filename });
        setResult({
            filename: filename,
            code: res.data.code,
            actor: res.data.actor,
            cover: res.data.cover_url
        });
        setHistory(prev => [{ time: new Date().toLocaleTimeString(), msg: `[${res.data.code}] 识别成功: 演员 ${res.data.actor || '未知'}`, success: true }, ...prev].slice(0, 50));
    } catch (error: any) {
        console.error(error);
        const errMsg = error.response?.data?.detail || "刮削失败，请检查后端日志";
        setHistory(prev => [{ time: new Date().toLocaleTimeString(), msg: `解析 ${filename} 失败: ${errMsg}`, success: false }, ...prev].slice(0, 50));
    } finally {
        setIsRecognizing(false);
    }
  };

  const handleAddBlacklist = async () => {
    if (newActorName.trim() && !blacklist.includes(newActorName.trim())) {
      try {
          await axios.post('http://127.0.0.1:8000/api/lab/blacklist', { name: newActorName.trim() });
          setBlacklist([...blacklist, newActorName.trim()]);
          setNewActorName('');
      } catch (e) {
          console.error(e);
      }
    }
  };

  const handleRemoveBlacklist = async (actor: string) => {
    try {
        await axios.delete(`http://127.0.0.1:8000/api/lab/blacklist/${actor}`);
        setBlacklist(blacklist.filter(a => a !== actor));
    } catch (e) {
        console.error(e);
    }
  };

  const isBlocked = result && result.actor && blacklist.some(b => result.actor.includes(b));

  return (
    <div className="flex gap-6 h-full min-h-[calc(100vh-140px)]">
      
      {/* 左侧：拖拽识别与预览区 */}
      <div className="flex-1 flex flex-col gap-6">
        
        {/* 拖拽上传区 */}
        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={clsx(
            "h-48 rounded-3xl border-2 border-dashed flex flex-col items-center justify-center transition-all cursor-pointer relative overflow-hidden bg-white shadow-sm",
            isDragging ? "border-primary bg-primary/5 scale-[1.02]" : "border-slate-300 hover:border-primary/50 hover:bg-slate-50"
          )}
        >
          {isRecognizing ? (
            <div className="flex flex-col items-center text-primary w-full px-8">
               <Search className="w-10 h-10 animate-bounce mb-4" />
               <p className="font-bold text-xl tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-primary to-cyan-500">
                  正在深度刮削中...
               </p>
               <div className="mt-4 w-full max-w-md bg-slate-900 rounded-lg p-3 border border-slate-800 shadow-inner relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-primary animate-pulse"></div>
                  <p className="text-emerald-400 font-mono text-sm break-all">
                     <span className="text-slate-500 mr-2">{'>'}</span> 
                     {probeStatus}
                     <span className="animate-pulse ml-1 inline-block w-1.5 h-3.5 bg-emerald-400 align-middle"></span>
                  </p>
               </div>
            </div>
          ) : (
            <>
              <div className="bg-primary/10 p-4 rounded-full mb-4">
                <UploadCloud className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-xl font-bold text-slate-700 mb-1">拖拽视频压缩包到这里</h3>
              <p className="text-sm text-slate-500">支持 .rar, .zip, .mp4 等格式文件</p>
            </>
          )}
        </div>

        {/* 识别结果卡片 */}
        {result && (
          <div className={clsx(
            "flex-1 bg-white rounded-3xl shadow-sm border p-6 flex flex-col transition-all duration-500",
            isBlocked ? "border-rose-300 bg-rose-50/30" : "border-slate-100"
          )}>
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
               <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                 <FileVideo className="w-5 h-5 text-primary" />
                 刮削档案卡
               </h3>
               {isBlocked ? (
                 <div className="flex items-center gap-1.5 px-3 py-1 bg-rose-100 text-rose-700 rounded-full text-sm font-bold animate-pulse">
                   <ShieldAlert className="w-4 h-4" /> 警告：该演员在您的黑名单中！
                 </div>
               ) : (
                 <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm font-bold">
                   安全可食用
                 </div>
               )}
            </div>

            <div className="flex gap-8 flex-1">
              {/* 封面图模拟 */}
              <div className="w-64 h-full min-h-[350px] bg-slate-100 rounded-2xl border border-slate-200 overflow-hidden flex items-center justify-center relative group shadow-inner">
                {result.cover ? (
                  <img src={result.cover} alt="cover" className="w-full h-full object-cover" />
                ) : (
                  <ImageIcon className="w-12 h-12 text-slate-300" />
                )}
                {isBlocked && (
                  <div className="absolute inset-0 bg-rose-600/20 backdrop-blur-[2px] flex items-center justify-center">
                    <div className="bg-rose-600 text-white px-4 py-2 rounded-lg font-bold text-lg rotate-[-15deg] shadow-lg border-2 border-white/50 tracking-widest">
                       BLOCKED
                    </div>
                  </div>
                )}
              </div>

              {/* 详细信息 */}
              <div className="flex-1 space-y-6 pt-2">
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">原始文件名</p>
                  <p className="text-slate-600 font-medium truncate" title={result.filename}>{result.filename}</p>
                </div>
                
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">核心番号</p>
                  <p className="text-4xl font-black text-slate-800 tracking-tight">{result.code}</p>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">出镜演员</p>
                  <span className={clsx(
                    "px-4 py-1.5 rounded-lg text-lg font-bold border-2 transition-colors",
                    isBlocked 
                      ? "bg-rose-100 border-rose-400 text-rose-700 shadow-[0_0_15px_rgba(225,29,72,0.3)]" 
                      : "bg-slate-100 border-transparent text-slate-700"
                  )}>
                    {result.actor}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 识别历史记录 */}
        {history.length > 0 && (
          <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-6 flex flex-col flex-1 min-h-[200px] overflow-hidden">
            <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
              本次识别流水记录
            </h3>
            <div className="flex-1 overflow-y-auto space-y-2 pr-2">
              {history.map((h, i) => (
                <div key={i} className={clsx(
                  "px-3 py-2 rounded-lg text-sm border-l-4 font-medium flex gap-3",
                  h.success ? "bg-slate-50 border-emerald-400 text-slate-600" : "bg-rose-50 border-rose-400 text-rose-700"
                )}>
                  <span className="text-slate-400 font-mono text-xs mt-0.5">{h.time}</span>
                  <span>{h.msg}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 右侧：女优黑名单管理 */}
      <div className="w-80 bg-white rounded-3xl shadow-sm border border-slate-100 p-6 flex flex-col h-full">
        <div className="flex items-center gap-2 mb-6 text-slate-800">
           <AlertCircle className="w-5 h-5 text-rose-500" />
           <h3 className="text-lg font-bold">雷区女优黑名单</h3>
        </div>

        <div className="flex gap-2 mb-6">
          <input 
            type="text" 
            value={newActorName}
            onChange={e => setNewActorName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddBlacklist()}
            placeholder="输入名字..."
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-rose-400 focus:ring-1 focus:ring-rose-400 text-sm font-medium transition-all"
          />
          <button 
            onClick={handleAddBlacklist}
            disabled={!newActorName.trim()}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white rounded-xl transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-2 space-y-2">
          {blacklist.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-8 italic">
              黑名单为空，您是个博爱的人
            </div>
          ) : (
            blacklist.map(actor => (
              <div key={actor} className="group flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-rose-200 hover:bg-rose-50/50 transition-all">
                <span className="font-semibold text-slate-700 text-sm group-hover:text-rose-700 transition-colors">
                  {actor}
                </span>
                <button 
                  onClick={() => handleRemoveBlacklist(actor)}
                  className="text-slate-400 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}