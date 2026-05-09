import { useState, useEffect } from 'react';
import { Search, PlusCircle, Loader2, Trash2, LayoutGrid, MonitorPlay, Film, Languages, ListFilter, ChevronLeft, ChevronRight, Copy } from 'lucide-react';
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

interface Stats {
  [key: string]: { total: number; today: number };
}

export function Database() {
  const [records, setRecords] = useState<Record[]>([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCopying, setIsCopying] = useState(false);
  
  // 筛选与分页状态
  const [filterSection, setFilterSection] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  
  // 手动录入与删除状态
  const [manualCodes, setManualCodes] = useState('');
  const [manualSection, setManualSection] = useState('4k');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 当筛选条件或页大小改变时，重置页码到1
  useEffect(() => {
    setPage(1);
  }, [filterSection, search, pageSize]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchData();
    }, 300); // 搜索防抖

    return () => clearTimeout(delayDebounceFn);
  }, [filterSection, search, page, pageSize]);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [recordsRes, statsRes] = await Promise.all([
        axios.get(`http://127.0.0.1:8000/api/records/`, { 
          params: { 
            section: filterSection,
            search: search,
            page: page,
            page_size: pageSize
          } 
        }),
        axios.get('http://127.0.0.1:8000/api/records/stats')
      ]);
      setRecords(recordsRes.data.items);
      setTotalRecords(recordsRes.data.total);
      setStats(statsRes.data);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to fetch data', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyAllCodes = async () => {
    try {
      setIsCopying(true);
      // 这里的逻辑是获取当前筛选条件下的【全量】番号，而不仅仅是当前页
      const res = await axios.get(`http://127.0.0.1:8000/api/records/`, { 
        params: { 
          section: filterSection,
          search: search,
          page: 1,
          page_size: 10000 
        } 
      });
      
      const allCodes = res.data.items.map((r: Record) => r.code).join('\n');
      await navigator.clipboard.writeText(allCodes);
      alert(`已成功复制该版块下共 ${res.data.items.length} 个番号到剪贴板！`);
    } catch (error) {
      console.error('Failed to copy codes', error);
      alert('复制失败，请重试');
    } finally {
      setIsCopying(false);
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
      fetchData();
    } catch (error) {
      console.error('Failed to add manual records', error);
      alert('录入失败，请检查后端运行状态。');
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
    if (selectedIds.size === records.length && records.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(records.map(r => r.id)));
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
      fetchData();
    } catch (error) {
      console.error('Failed to delete records', error);
      alert('删除失败，请检查后端运行状态。');
    } finally {
      setIsDeleting(false);
    }
  };

  const totalPages = Math.ceil(totalRecords / pageSize);

  const StatCard = ({ title, sectionKey, icon: Icon, colorClass, bgClass }: { title: string, sectionKey: string, icon: any, colorClass: string, bgClass: string }) => {
    const data = stats?.[sectionKey] || { total: 0, today: 0 };
    const isActive = filterSection === sectionKey;
    
    return (
      <div 
        onClick={() => setFilterSection(isActive ? 'all' : sectionKey)}
        className={clsx(
          "flex-1 p-4 rounded-2xl border transition-all cursor-pointer",
          isActive 
            ? `ring-2 ring-offset-2 ${colorClass.replace('text-', 'ring-')} ${bgClass} border-transparent shadow-md` 
            : "bg-white border-slate-100 hover:border-slate-300 hover:shadow-sm"
        )}
      >
        <div className="flex items-center justify-between mb-3">
          <div className={clsx("p-2 rounded-xl", bgClass)}>
            <Icon className={clsx("w-5 h-5", colorClass)} />
          </div>
          {data.today > 0 && (
            <span className="text-xs font-semibold bg-emerald-100 text-emerald-600 px-2 py-1 rounded-full">
              今日 +{data.today}
            </span>
          )}
        </div>
        <h4 className="text-slate-500 text-sm font-medium mb-1">{title} 库存</h4>
        <div className="text-2xl font-bold text-slate-800">{data.total} <span className="text-sm font-normal text-slate-400">部</span></div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full gap-6">
      
      {/* 顶部：数据大盘概览卡片 */}
      <div className="flex gap-4">
        <StatCard title="VR 虚拟现实" sectionKey="vr" icon={MonitorPlay} colorClass="text-purple-600" bgClass="bg-purple-100" />
        <StatCard title="4K 超高清" sectionKey="4k" icon={LayoutGrid} colorClass="text-blue-600" bgClass="bg-blue-100" />
        <StatCard title="HD 高清有码" sectionKey="hd" icon={Film} colorClass="text-amber-600" bgClass="bg-amber-100" />
        <StatCard title="Sub 外挂字幕" sectionKey="sub" icon={Languages} colorClass="text-emerald-600" bgClass="bg-emerald-100" />
      </div>

      <div className="flex gap-6 h-full min-h-0">
        {/* 左侧：手动录入 */}
        <div className="w-1/4 bg-white rounded-2xl p-5 shadow-sm border border-slate-100 flex flex-col h-fit">
          <h3 className="text-md font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <PlusCircle className="w-4 h-4 text-primary" />
            快速补录
          </h3>
          <div className="space-y-4 flex-1 flex flex-col">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-slate-500">归属版块</label>
              <select 
                value={manualSection}
                onChange={e => setManualSection(e.target.value)}
                className="w-full p-2 text-sm bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary"
              >
                <option value="4k">4K 超清</option>
                <option value="vr">VR 视频</option>
                <option value="hd">高清有码</option>
                <option value="sub">外挂字幕</option>
              </select>
            </div>
            <div className="flex flex-col gap-2 flex-1">
              <label className="text-xs font-medium text-slate-500">番号列表 (每行一个)</label>
              <textarea 
                value={manualCodes}
                onChange={(e) => setManualCodes(e.target.value)}
                className="w-full flex-1 p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none min-h-[150px]"
                placeholder="例如：&#10;SSNI-123&#10;MIDE-456"
              />
            </div>
            <button 
              onClick={handleManualSubmit}
              disabled={isSubmitting || !manualCodes.trim()}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-blue-600 disabled:bg-slate-300 text-white py-2 rounded-xl text-sm font-medium transition-colors shadow-sm mt-2"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "确 认 录 入"}
            </button>
          </div>
        </div>

        {/* 右侧：全能筛选表格 */}
        <div className="w-3/4 flex flex-col bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          
          {/* 表格工具栏 */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200">
                <ListFilter className="w-4 h-4 text-slate-400" />
                <select 
                  value={filterSection}
                  onChange={(e) => setFilterSection(e.target.value)}
                  className="bg-transparent text-sm font-medium text-slate-700 outline-none cursor-pointer"
                >
                  <option value="all">所有版块记录</option>
                  <option value="vr">VR 专属记录</option>
                  <option value="4k">4K 专属记录</option>
                  <option value="hd">HD 专属记录</option>
                  <option value="sub">字幕 专属记录</option>
                </select>
              </div>
              
              <div className="relative w-56">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="text"
                  placeholder="搜索番号或帖子标题..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button 
                onClick={handleCopyAllCodes}
                disabled={totalRecords === 0 || isCopying}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-indigo-100"
                title="一键提取并复制当前筛选结果下的所有番号"
              >
                {isCopying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Copy className="w-3.5 h-3.5" />}
                批量提取
              </button>

              <button 
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0 || isDeleting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors border border-rose-100"
              >
                {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                删除 ({selectedIds.size})
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
                      className="w-3.5 h-3.5 text-primary rounded border-gray-300 focus:ring-primary cursor-pointer"
                    />
                  </th>
                  <th className="px-5 py-3 font-medium">核心番号</th>
                  <th className="px-5 py-3 font-medium">版块</th>
                  <th className="px-5 py-3 font-medium">原始帖子标题</th>
                  <th className="px-5 py-3 font-medium">入库时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-12 text-center text-slate-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 opacity-50 text-primary" />
                      正在加载数据...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-12 text-center text-slate-400 italic">
                      没有找到对应的档案记录
                    </td>
                  </tr>
                ) : (
                  records.map(record => (
                    <tr 
                      key={record.id} 
                      onClick={() => toggleSelect(record.id)}
                      className={clsx(
                        "transition-colors cursor-pointer",
                        selectedIds.has(record.id) ? "bg-blue-50/40" : "hover:bg-slate-50/80"
                      )}
                    >
                      <td className="px-5 py-3 text-center">
                        <input 
                          type="checkbox"
                          checked={selectedIds.has(record.id)}
                          onChange={() => toggleSelect(record.id)}
                          onClick={e => e.stopPropagation()}
                          className="w-3.5 h-3.5 text-primary rounded border-gray-300 focus:ring-primary cursor-pointer"
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
                      <td className="px-5 py-3 text-slate-600 truncate max-w-[200px]" title={record.title}>
                        {record.title || '-'}
                      </td>
                      <td className="px-5 py-3 text-slate-400 text-xs">
                        {new Date(record.download_time).toLocaleString()}
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
                共 <span className="font-semibold text-slate-700">{totalRecords}</span> 条记录
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">每页显示</span>
                <select 
                  value={pageSize}
                  onChange={e => setPageSize(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-md px-2 py-1 outline-none focus:border-primary cursor-pointer"
                >
                  <option value={10}>10</option>
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
    </div>
  );
}
