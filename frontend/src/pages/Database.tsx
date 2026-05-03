import { useState, useEffect } from 'react';
import { Search, Database as DatabaseIcon, DownloadCloud, PlusCircle, Loader2, Trash2 } from 'lucide-react';
import axios from 'axios';
import { clsx } from 'clsx';

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
  
  const [manualCodes, setManualCodes] = useState('');
  const [manualSection, setManualSection] = useState('4k');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('http://127.0.0.1:8000/api/records/');
      setRecords(response.data);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to fetch records', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualSubmit = async () => {
    if (!manualCodes.trim()) return;
    setIsSubmitting(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/records/manual', {
        codes: manualCodes,
        section: manualSection
      });
      alert(`成功录入了 ${response.data.added} 个番号！`);
      setManualCodes('');
      fetchRecords();
    } catch (error) {
      console.error('Failed to add manual records', error);
      alert('录入失败，请检查后端运行状态。');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredRecords = records.filter(r => 
    r.code.toLowerCase().includes(search.toLowerCase()) || 
    (r.title && r.title.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredRecords.length && filteredRecords.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredRecords.map(r => r.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`警告：您确认要永久删除选中的 ${selectedIds.size} 个番号记录吗？此操作无法撤销！`)) return;

    setIsDeleting(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/records/delete', {
        ids: Array.from(selectedIds)
      });
      alert(`成功删除了 ${response.data.deleted} 个番号！`);
      fetchRecords();
    } catch (error) {
      console.error('Failed to delete records', error);
      alert('删除失败，请检查后端运行状态。');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex gap-6">
        <div className="w-1/3 bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex flex-col">
          <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-primary" />
            手动录入番号
          </h3>
          <div className="space-y-4 flex-1 flex flex-col">
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-slate-700 shrink-0">所属版块</label>
              <select 
                value={manualSection}
                onChange={e => setManualSection(e.target.value)}
                className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary"
              >
                <option value="4k">4K 超清</option>
                <option value="vr">VR 视频</option>
                <option value="hd">高清有码</option>
                <option value="sub">外挂字幕</option>
              </select>
            </div>
            <textarea 
              value={manualCodes}
              onChange={(e) => setManualCodes(e.target.value)}
              className="w-full flex-1 p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none resize-none min-h-[100px]"
              placeholder="支持批量录入，一行一个番号..."
            />
            <button 
              onClick={handleManualSubmit}
              disabled={isSubmitting || !manualCodes.trim()}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-blue-600 disabled:bg-slate-300 text-white py-2.5 rounded-xl font-medium transition-colors shadow-sm"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "确 认 录 入"}
            </button>
          </div>
        </div>

        <div className="w-2/3 flex flex-col justify-center bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-3 rounded-xl">
                <DatabaseIcon className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-800">本地番号仓库</h3>
                <p className="text-sm text-slate-500">共收录 {records.length} 条数据记录</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="text"
                  placeholder="搜索番号或标题..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>
              <button 
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0 || isDeleting}
                className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-medium transition-colors border border-rose-100"
                title="删除选中"
              >
                {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                批量删除 ({selectedIds.size})
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-slate-50 border-b border-slate-100 shadow-sm z-10">
              <tr className="text-slate-500 text-sm">
                <th className="px-6 py-4 font-medium w-12 text-center">
                  <input 
                    type="checkbox"
                    checked={selectedIds.size === filteredRecords.length && filteredRecords.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary cursor-pointer"
                  />
                </th>
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
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    <DownloadCloud className="w-8 h-8 animate-bounce mx-auto mb-2 opacity-50" />
                    正在加载数据...
                  </td>
                </tr>
              ) : filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400 italic">
                    没有找到匹配的记录
                  </td>
                </tr>
              ) : (
                filteredRecords.map(record => (
                  <tr 
                    key={record.id} 
                    onClick={() => toggleSelect(record.id)}
                    className={clsx(
                      "transition-colors cursor-pointer",
                      selectedIds.has(record.id) ? "bg-blue-50/50" : "hover:bg-slate-50/80"
                    )}
                  >
                    <td className="px-6 py-4 text-center">
                      <input 
                        type="checkbox"
                        checked={selectedIds.has(record.id)}
                        onChange={() => toggleSelect(record.id)}
                        onClick={e => e.stopPropagation()}
                        className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary cursor-pointer"
                      />
                    </td>
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