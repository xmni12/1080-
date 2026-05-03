import { useState, useEffect } from 'react';
import { Search, Database as DatabaseIcon, DownloadCloud } from 'lucide-react';
import axios from 'axios';

interface Record {
  id: number;
  section: string;
  code: string;
  download_time: string;
  post_url?: string;
  title?: string;
}

export function Database() {
  const [records, setRecords] = useState<Record[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('http://127.0.0.1:8000/api/records/');
      setRecords(response.data);
    } catch (error) {
      console.error('Failed to fetch records', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRecords = records.filter(r => 
    r.code.toLowerCase().includes(search.toLowerCase()) || 
    (r.title && r.title.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 p-3 rounded-xl">
            <DatabaseIcon className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">本地番号仓库</h3>
            <p className="text-sm text-slate-500">共收录 {records.length} 条数据记录</p>
          </div>
        </div>

        <div className="relative w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text"
            placeholder="搜索番号或标题..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
          />
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-slate-50 border-b border-slate-100 shadow-sm z-10">
              <tr className="text-slate-500 text-sm">
                <th className="px-6 py-4 font-medium">编号 (ID)</th>
                <th className="px-6 py-4 font-medium">核心番号</th>
                <th className="px-6 py-4 font-medium">所属版块</th>
                <th className="px-6 py-4 font-medium">原始帖子标题</th>
                <th className="px-6 py-4 font-medium">入库时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <DownloadCloud className="w-8 h-8 animate-bounce mx-auto mb-2 opacity-50" />
                    正在加载数据...
                  </td>
                </tr>
              ) : filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400 italic">
                    没有找到匹配的记录
                  </td>
                </tr>
              ) : (
                filteredRecords.map(record => (
                  <tr key={record.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 text-slate-500">#{record.id}</td>
                    <td className="px-6 py-4">
                      <span className="font-semibold text-primary">{record.code}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-md text-xs font-medium uppercase">
                        {record.section}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-700 truncate max-w-xs" title={record.title}>
                      {record.title || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">
                      {new Date(record.download_time).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
