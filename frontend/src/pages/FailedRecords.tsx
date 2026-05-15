import { useState, useEffect } from 'react';
import { Trash2, RotateCcw, AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import axios from 'axios';

interface FailedRecord {
  id: number;
  section: string;
  code: string;
  title: string;
  post_url: string;
  reason: string;
  failed_time: string;
}

export function FailedRecords() {
  const [records, setRecords] = useState<FailedRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // 分页与筛选
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalRecords, setTotalRecords] = useState(0);
  
  const [isRetrying, setIsRetrying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // 选择状态
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 当筛选改变时重置页码
  useEffect(() => {
    setPage(1);
  }, [search, pageSize]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchData();
    }, 300); // 搜索防抖
    return () => clearTimeout(delayDebounceFn);
  }, [search, page, pageSize]);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const res = await axios.get(`http://127.0.0.1:8000/api/failed_records/`, { 
        params: { search, page, page_size: pageSize } 
      });
      setRecords(res.data.items);
      setTotalRecords(res.data.total);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to fetch failed records', error);
    } finally {
      setIsLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === records.length && records.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(records.map(a => a.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确认要丢弃选中的 ${selectedIds.size} 个死链记录吗？`)) return;

    setIsDeleting(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/failed_records/delete', {
        ids: Array.from(selectedIds)
      });
      alert(`成功丢弃了 ${response.data.deleted} 个死链记录。`);
      fetchData();
    } catch (error) {
      console.error('Failed to delete failed records', error);
      alert('丢弃失败，请重试。');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleBulkRetry = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确认要把选中的 ${selectedIds.size} 个记录重新压入排队引擎重试吗？`)) return;

    setIsRetrying(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/failed_records/retry', {
        ids: Array.from(selectedIds)
      });
      alert(`成功将 ${response.data.retried} 个任务压入队列，请前往【任务中心】查看大屏。`);
      fetchData();
    } catch (error) {
      console.error('Failed to retry failed records', error);
      alert('重试失败，请重试。');
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      
      {/* 顶部说明面板 */}
      <div className="bg-gradient-to-r from-orange-900 to-amber-800 rounded-2xl p-6 shadow-md text-white flex items-center justify-between">
         <div className="flex items-start gap-4">
            <div className="bg-white/10 p-3 rounded-xl border border-white/20">
               <AlertTriangle className="w-6 h-6 text-amber-400" />
            </div>
            <div>
               <h3 className="text-xl font-bold mb-1 tracking-wide">死链抢救回收站</h3>
               <p className="text-amber-100/80 text-sm">
                  这里存放着所有因网络波动、无权访问或附件损坏而导致下载失败的资源记录。<br/>
                  你可以随时全选它们，点击【一键重新压入队列】让后台重新尝试下载，再也不怕漏网之鱼。
               </p>
            </div>
         </div>
         <div className="flex flex-col items-end">
            <span className="text-3xl font-black text-amber-400">{totalRecords}</span>
            <span className="text-xs font-medium text-amber-200/80 tracking-wider">待抢救记录</span>
         </div>
      </div>

      <div className="flex flex-col bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex-1 min-h-0">
          
          {/* 表格工具栏 */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="relative w-80">
              <input 
                type="text"
                placeholder="搜索失败的番号或标题..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all shadow-sm"
              />
            </div>

            <div className="flex items-center gap-3">
                <button 
                onClick={handleBulkRetry}
                disabled={selectedIds.size === 0 || isRetrying}
                className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-bold transition-colors shadow-sm"
                >
                {isRetrying ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                一键全部重试 ({selectedIds.size})
                </button>
                <button 
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0 || isDeleting}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-slate-200"
                >
                {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                彻底丢弃 ({selectedIds.size})
                </button>
            </div>
          </div>

          {/* 表格主体 */}
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-white border-b border-slate-100 z-10 shadow-sm">
                <tr className="text-slate-500 text-xs uppercase tracking-wider">
                  <th className="px-5 py-3 font-medium w-10 text-center">
                    <input 
                      type="checkbox"
                      checked={selectedIds.size === records.length && records.length > 0}
                      onChange={toggleSelectAll}
                      className="w-3.5 h-3.5 text-amber-500 rounded border-gray-300 focus:ring-amber-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-5 py-3 font-medium w-32">番号</th>
                  <th className="px-5 py-3 font-medium w-24">版块</th>
                  <th className="px-5 py-3 font-medium">帖子标题</th>
                  <th className="px-5 py-3 font-medium">失败原因</th>
                  <th className="px-5 py-3 font-medium w-40">失败时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 opacity-50 text-amber-500" />
                      正在加载数据...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400 italic">
                      {search ? "没有找到符合条件的记录" : "回收站目前为空，系统运转良好！"}
                    </td>
                  </tr>
                ) : (
                  records.map(record => (
                    <tr 
                      key={record.id} 
                      onClick={() => toggleSelect(record.id)}
                      className={clsx(
                        "transition-colors cursor-pointer",
                        selectedIds.has(record.id) ? "bg-amber-50/40" : "hover:bg-slate-50/80"
                      )}
                    >
                      <td className="px-5 py-3 text-center">
                        <input 
                          type="checkbox"
                          checked={selectedIds.has(record.id)}
                          onChange={() => toggleSelect(record.id)}
                          onClick={e => e.stopPropagation()}
                          className="w-3.5 h-3.5 text-amber-500 rounded border-gray-300 focus:ring-amber-500 cursor-pointer"
                        />
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-bold text-slate-800">{record.code}</span>
                      </td>
                      <td className="px-5 py-3">
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[11px] font-bold uppercase">
                          {record.section}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <a href={record.post_url} target="_blank" rel="noreferrer" className="text-slate-600 hover:text-blue-500 underline truncate max-w-xs inline-block" onClick={e => e.stopPropagation()} title="点击访问原帖">
                          {record.title}
                        </a>
                      </td>
                      <td className="px-5 py-3">
                        <span className="text-red-500 text-xs font-medium bg-red-50 px-2 py-1 rounded">
                           {record.reason}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-slate-400 text-xs">
                        {new Date(record.failed_time).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* 表格分页底部 */}
          <div className="p-3 border-t border-slate-100 bg-white flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-xs text-slate-500">
                共 <span className="font-semibold text-slate-700">{totalRecords}</span> 个失败记录
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">每页</span>
                <select 
                  value={pageSize}
                  onChange={e => setPageSize(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-md px-2 py-1 outline-none focus:border-amber-500 cursor-pointer"
                >
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <span className="text-xs text-slate-500">条</span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1 || isLoading}
                className="p-1 rounded-md text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-xs font-medium text-slate-700 px-3">
                {page} / {totalPages > 0 ? totalPages : 1}
              </span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || isLoading}
                className="p-1 rounded-md text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
      </div>
    </div>
  );
}