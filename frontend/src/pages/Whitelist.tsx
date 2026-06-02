import { useState, useEffect } from 'react';
import { Search, PlusCircle, Trash2, Heart, ChevronLeft, ChevronRight, ShieldCheck, Loader2, Download } from 'lucide-react';
import { clsx } from 'clsx';
import axios from 'axios';

interface WhitelistActor {
  id: number;
  name: string;
  aliases: string;
  avatar_url: string | null;
  added_time: string;
}

export function Whitelist() {
  const [actors, setActors] = useState<WhitelistActor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // 分页与筛选
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalRecords, setTotalRecords] = useState(0);
  
  // 录入状态
  const [manualNames, setManualNames] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
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
      const res = await axios.get(`http://127.0.0.1:8000/api/whitelist/`, { 
        params: { search, page, page_size: pageSize } 
      });
      setActors(res.data.items);
      setTotalRecords(res.data.total);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to fetch whitelist', error);
    } finally {
      setIsLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));

  const handleManualSubmit = async () => {
    if (!manualNames.trim()) return;
    setIsSubmitting(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/whitelist/add', {
        names: manualNames
      });
      const added = response.data.added || 0;
      const skipped = response.data.skipped || 0;
      alert(`录入完成！\n✅ 成功添加：${added} 位演员\n🚧 重复跳过：${skipped} 位演员`);
      setManualNames('');
      fetchData();
    } catch (error: any) {
      console.error('Failed to add to whitelist', error);
      alert(`录入失败，请检查后端状态。\n错误详情: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === actors.length && actors.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(actors.map(a => a.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确认要将选中的 ${selectedIds.size} 位演员从白名单中移除吗？`)) return;

    setIsDeleting(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/whitelist/delete', {
        ids: Array.from(selectedIds)
      });
      alert(`成功移除了 ${response.data.deleted} 位演员。`);
      fetchData();
    } catch (error) {
      console.error('Failed to delete from whitelist', error);
      alert('删除失败，请重试。');
    } finally {
      setIsDeleting(false);
    }
  };

  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const res = await axios.get(`http://127.0.0.1:8000/api/whitelist/`, { 
        params: { search: '', page: 1, page_size: 10000 } 
      });
      const lines = res.data.items.map((actor: WhitelistActor) => {
        return actor.aliases ? `${actor.name},${actor.aliases}` : actor.name;
      }).join('\n');
      
      await navigator.clipboard.writeText(lines);
      alert(`成功导出 ${res.data.items.length} 个目标到剪贴板！可以直接粘贴到任意文本中备份。`);
    } catch (error) {
      console.error('Failed to export whitelist', error);
      alert('导出失败，请重试。');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      
      {/* 顶部说明面板 */}
      <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 rounded-2xl p-6 shadow-md text-white flex items-center justify-between">
         <div className="flex items-start gap-4">
            <div className="bg-white/10 p-3 rounded-xl border border-white/20">
               <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
               <h3 className="text-xl font-bold mb-1 tracking-wide">心动演员最高豁免权 (Whitelist)</h3>
               <p className="text-emerald-100/80 text-sm">
                  当爬虫解析到多名参演女优时，只要其中包含以下白名单库中的演员，系统将直接赋予该番号最高优先级，无视并越过所有黑名单拦截机制，强制绿灯入库下载！
               </p>
            </div>
         </div>
         <div className="flex flex-col items-end">
            <span className="text-3xl font-black text-emerald-400">{totalRecords}</span>
            <span className="text-xs font-medium text-emerald-200/80 tracking-wider">已设豁免目标</span>
         </div>
      </div>

      <div className="flex gap-6 h-full min-h-0">
        {/* 左侧：手动录入 */}
        <div className="w-1/4 bg-white rounded-2xl p-5 shadow-sm border border-slate-100 flex flex-col h-fit">
          <h3 className="text-md font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <PlusCircle className="w-4 h-4 text-emerald-500" />
            快速特权录入
          </h3>
          <div className="space-y-4 flex-1 flex flex-col">
            <div className="flex flex-col gap-2 flex-1">
              <label className="text-xs font-medium text-slate-500">喜爱名单 (支持批量，每行一位)</label>
              <textarea 
                value={manualNames}
                onChange={(e) => setManualNames(e.target.value)}
                className="w-full flex-1 p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 outline-none resize-none min-h-[250px]"
                placeholder="输入你特别喜欢的演员姓名...&#10;例如：&#10;三上悠亚&#10;桥本有菜"
              />
            </div>
            <button 
              onClick={handleManualSubmit}
              disabled={!manualNames.trim() || isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm mt-2"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "确 认 录 入"}
            </button>
          </div>
        </div>

        {/* 右侧：表格 */}
        <div className="w-3/4 flex flex-col bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          
          {/* 表格工具栏 */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                type="text"
                placeholder="搜索白名单演员姓名..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-200 rounded-lg outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all shadow-sm"
              />
            </div>

            <div className="flex items-center gap-3">
                <button 
                onClick={handleExport}
                disabled={totalRecords === 0 || isExporting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-emerald-100"
                title="一键导出全部白名单到剪贴板"
                >
                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                全量导出
                </button>

                <button 
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0 || isDeleting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-slate-200"
                >
                {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                取消豁免 ({selectedIds.size})
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
                      checked={selectedIds.size === actors.length && actors.length > 0}
                      onChange={toggleSelectAll}
                      className="w-3.5 h-3.5 text-emerald-500 rounded border-gray-300 focus:ring-emerald-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-5 py-3 font-medium">目标演员</th>
                  <th className="px-5 py-3 font-medium w-1/4">录入时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {isLoading ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-12 text-center text-slate-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 opacity-50 text-emerald-500" />
                      正在加载数据...
                    </td>
                  </tr>
                ) : actors.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-12 text-center text-slate-400 italic">
                      {search ? "没有找到符合条件的记录" : "白名单目前为空，快去添加吧"}
                    </td>
                  </tr>
                ) : (
                  actors.map(actor => (
                    <tr 
                      key={actor.id} 
                      onClick={() => toggleSelect(actor.id)}
                      className={clsx(
                        "transition-colors cursor-pointer group",
                        selectedIds.has(actor.id) ? "bg-emerald-50/40" : "hover:bg-slate-50/80"
                      )}
                    >
                      <td className="px-5 py-3 text-center">
                        <input 
                          type="checkbox"
                          checked={selectedIds.has(actor.id)}
                          onChange={() => toggleSelect(actor.id)}
                          onClick={e => e.stopPropagation()}
                          className="w-3.5 h-3.5 text-emerald-500 rounded border-gray-300 focus:ring-emerald-500 cursor-pointer"
                        />
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                           {actor.avatar_url ? (
                             <img src={actor.avatar_url} alt={actor.name} className="w-8 h-8 rounded-full object-cover border border-slate-200 shadow-sm" />
                           ) : (
                             <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center border border-slate-200">
                               <Heart className="w-4 h-4 text-emerald-400" />
                             </div>
                           )}
                           <div className="flex flex-col">
                             <span className="font-bold text-slate-800">{actor.name}</span>
                             {actor.aliases && (
                               <span className="text-[10px] text-slate-400 max-w-[150px] truncate" title={actor.aliases}>
                                 别名: {actor.aliases}
                               </span>
                             )}
                           </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-slate-400 text-xs">
                        {new Date(actor.added_time).toLocaleString()}
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
                共 <span className="font-semibold text-slate-700">{totalRecords}</span> 个特权目标
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">每页</span>
                <select 
                  value={pageSize}
                  onChange={e => setPageSize(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-md px-2 py-1 outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
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
    </div>
  );
}