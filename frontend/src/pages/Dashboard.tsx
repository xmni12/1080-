import { useState, useEffect } from 'react';
import { MonitorPlay, Film, Tv, FileText, Activity, Loader2 } from 'lucide-react';
import { QuotaCard } from '../components/QuotaCard';
import axios from 'axios';

export function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [statsRes, settingsRes] = await Promise.all([
          axios.get('http://127.0.0.1:8000/api/records/stats'),
          axios.get('http://127.0.0.1:8000/api/settings')
        ]);
        setStats(statsRes.data);
        setSettings(settingsRes.data);
      } catch (error) {
        console.error('Failed to fetch dashboard data', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const getQuotaData = (sectionKey: string) => {
    const current = stats?.[sectionKey]?.today || 0;
    const max = settings?.sections?.[sectionKey]?.daily_limit || 55;
    return { current, max };
  };

  const quota4K = getQuotaData('4k');
  const quotaVR = getQuotaData('vr');
  const quotaHD = getQuotaData('hd');
  const quotaSub = getQuotaData('sub');

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {isLoading ? (
          <div className="col-span-full py-12 flex justify-center items-center text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="ml-3 font-medium">正在实时加载系统大盘数据...</span>
          </div>
        ) : (
          <>
            <QuotaCard 
              title="4K 超清" 
              current={quota4K.current} 
              max={quota4K.max} 
              icon={MonitorPlay}
              colorClass="text-emerald-500"
              bgClass="bg-emerald-50"
            />
            <QuotaCard 
              title="VR 视频" 
              current={quotaVR.current} 
              max={quotaVR.max} 
              icon={Tv}
              colorClass="text-cyan-500"
              bgClass="bg-cyan-50"
            />
            <QuotaCard 
              title="高清有码" 
              current={quotaHD.current} 
              max={quotaHD.max} 
              icon={Film}
              colorClass="text-blue-500"
              bgClass="bg-blue-50"
            />
            <QuotaCard 
              title="外挂字幕" 
              current={quotaSub.current} 
              max={quotaSub.max} 
              icon={FileText}
              colorClass="text-rose-500"
              bgClass="bg-rose-50"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
         <div className="xl:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                 <Activity className="w-5 h-5 text-primary" />
                 系统状态趋势
              </h3>
            </div>
            <div className="h-64 flex items-center justify-center bg-slate-50 rounded-xl border border-dashed border-slate-200 text-slate-400">
               {/* 这里后续可以集成 Recharts 展示图表 */}
               图表数据采集中...
            </div>
         </div>
         
         <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">服务健康检查</h3>
            <div className="space-y-4">
               <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600 font-medium">FastAPI 后端</span>
                  <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-md">Online</span>
               </div>
               <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600 font-medium">SQLite 数据库</span>
                  <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-md">Connected</span>
               </div>
               <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600 font-medium">DrissionPage 内核</span>
                  <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-md">Online</span>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
}
