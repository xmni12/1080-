import { useState, useEffect } from 'react';
import { MonitorPlay, Film, Tv, FileText, Activity, Loader2 } from 'lucide-react';
import { QuotaCard } from '../components/QuotaCard';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

export function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [statsRes, settingsRes, trendRes] = await Promise.all([
          axios.get('http://127.0.0.1:8000/api/records/stats'),
          axios.get('http://127.0.0.1:8000/api/settings'),
          axios.get('http://127.0.0.1:8000/api/records/trend')
        ]);
        setStats(statsRes.data);
        setSettings(settingsRes.data);
        setTrendData(trendRes.data);
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
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                 <Activity className="w-5 h-5 text-primary" />
                 系统状态趋势 (最近 7 日抓取量)
              </h3>
            </div>
            <div className="h-64 w-full">
              {isLoading ? (
                <div className="w-full h-full flex items-center justify-center text-slate-300">
                   加载图表中...
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis 
                      dataKey="name" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fontSize: 12, fill: '#94a3b8' }} 
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fontSize: 12, fill: '#94a3b8' }} 
                    />
                    <Tooltip 
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                      cursor={{ stroke: '#3b82f6', strokeWidth: 2 }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="count" 
                      name="下载量"
                      stroke="#3b82f6" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorCount)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
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
