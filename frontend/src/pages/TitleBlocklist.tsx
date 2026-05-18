import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, ShieldAlert, Loader2, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';
import axios from 'axios';

interface BlocklistItem {
  id: number;
  keyword: string;
  added_time: string;
}

export function TitleBlocklist() {
  const [items, setItems] = useState<BlocklistItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  
  // 添加屏蔽词
  const [newKeywords, setNewKeywords] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/title_blocklist/', {
        params: { page, page_size: 50, search: search.trim() }
      });
      setItems(res.data.items);
      setTotal(res.data.total);
    } catch (error) {
      console.error('Failed to fetch blocklist', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [page, search]);

  const handleAdd = async () => {
    if (!newKeywords.trim()) return;
    setIsAdding(true);
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/title_blocklist/add', { keywords: newKeywords });
      alert(`成功添加 ${res.data.added} 个屏蔽词`);
      setNewKeywords('');
      fetchItems();
    } catch (error) {
      console.error('Failed to add blocklist', error);
      alert('添加失败，请检查网络或格式');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确定要移除选中的 ${selectedIds.size} 个屏蔽词吗？`)) return;

    try {
      const ids = Array.from(selectedIds);
      await axios.post('http://127.0.0.1:8000/api/title_blocklist/delete', { ids });
      setSelectedIds(new Set());
      fetchItems();
    } catch (error) {
      console.error('Failed to delete items', error);
      alert('移除失败');
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map(i => i.id)));
    }
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-8 shadow-lg text-white">
         <div className="flex items-start gap-4">
            <div className="bg-rose-500/20 p-3 rounded-2xl border border-rose-500/30">
               <ShieldAlert className="w-8 h-8 text-rose-400" />
            </div>
            <div>
               <h3 className="text-2xl font-bold mb-2">标题屏蔽词库 (Title Blocklist)</h3>
               <p className="text-slate-300 text-sm max-w-2xl leading-relaxed">
                  构建你的绝对防御网。爬虫在抓取论坛帖子时，一旦发现帖子标题中包含这里的任何词汇（如：VR、中文字幕、NTR 等），
                  将直接在最前端斩杀丢弃，**不再发起后续的 AVBase 查询请求**，极大提升整体刮削速度与过滤精准度。
               </p>
            </div>
         </div>
      </div>

      {/* 录入控制台 */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex flex-col md:flex-row gap-4 items-start md:items-end">
        <div className="flex-1 w-full space-y-2">
            <label className="text-sm font-bold text-slate-700">录入新屏蔽词 (支持批量)</label>
            <div className="flex items-center gap-2">
                <input 
                    type="text" 
                    value={newKeywords}
                    onChange={e => setNewKeywords(e.target.value)}
                    placeholder="例如: VR, 无码流出, 解禁 (多个词用逗号隔开)"
                    className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all font-mono"
                    onKeyDown={e => e.key === 'Enter' && handleAdd()}
                />
                <button 
                    onClick={handleAdd}
                    disabled={isAdding || !newKeywords.trim()}
                    className="flex items-center gap-2 bg-rose-600 hover:bg-rose-700 disabled:bg-rose-300 text-white px-6 py-2.5 rounded-lg font-medium transition-colors whitespace-nowrap"
                >
                    {isAdding ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
                    拦截它们
                </button>
            </div>
        </div>
      </div>

      {/* 数据列表 */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/50">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="搜索屏蔽词..."
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
                className="pl-9 pr-4 py-2 w-64 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white"
              />
            </div>
            <span className="text-sm font-medium text-slate-500 bg-white px-3 py-1 rounded-full border border-slate-200">
              词库总量: <span className="text-rose-600 font-bold">{total}</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchItems}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
              刷新
            </button>
            <button
              onClick={handleDelete}
              disabled={selectedIds.size === 0}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-lg transition-all",
                selectedIds.size > 0 
                  ? "bg-rose-100 text-rose-700 hover:bg-rose-200 border border-rose-200"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-100"
              )}
            >
              <Trash2 className="w-4 h-4" />
              移除选中 ({selectedIds.size})
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-100">
              <tr>
                <th className="px-6 py-4 w-12">
                  <input
                    type="checkbox"
                    checked={items.length > 0 && selectedIds.size === items.length}
                    onChange={toggleSelectAll}
                    className="rounded border-slate-300 text-rose-600 focus:ring-rose-600 cursor-pointer"
                  />
                </th>
                <th className="px-6 py-4">屏蔽关键词 (Keyword)</th>
                <th className="px-6 py-4">收录时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-rose-400" />
                    正在拉取词库...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center text-slate-500">
                    <ShieldAlert className="w-8 h-8 mx-auto mb-3 text-slate-300" />
                    <p>你的词库空空如也，爬虫没有任何前置拦截规则。</p>
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr 
                    key={item.id} 
                    className={clsx(
                      "hover:bg-slate-50 transition-colors",
                      selectedIds.has(item.id) && "bg-rose-50/50"
                    )}
                  >
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        className="rounded border-slate-300 text-rose-600 focus:ring-rose-600 cursor-pointer"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-slate-800 bg-slate-100 px-3 py-1 rounded-md border border-slate-200 font-mono text-base">
                            {item.keyword}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-500 font-mono text-xs">
                      {new Date(item.added_time).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        {total > 0 && (
          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              显示 {(page - 1) * 50 + 1} 到 {Math.min(page * 50, total)} 条
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm bg-white border border-slate-200 rounded-md disabled:opacity-50 hover:bg-slate-50"
              >
                上一页
              </button>
              <span className="text-sm font-medium text-slate-700 px-2">第 {page} 页</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * 50 >= total}
                className="px-3 py-1 text-sm bg-white border border-slate-200 rounded-md disabled:opacity-50 hover:bg-slate-50"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}