import { useState, useCallback } from 'react';
import { UploadCloud, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import axios from 'axios';

interface RenameItem {
  id: string;
  originalName: string;
  path: string;
  status: 'pending' | 'processing' | 'success' | 'error';
  result?: string;
  previewUrl?: string;
}

export function Rename() {
  const [items, setItems] = useState<RenameItem[]>([]);
  const [rules, setRules] = useState('\\[1080P\\]\n广告网址\\.com');
  const [threads, setThreads] = useState(3);
  const [isProcessing, setIsProcessing] = useState(false);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // 注意：Web 环境下的 File API 无法直接获取绝对物理路径。
    // 在实际的 Electron/Tauri 或基于本地代理的应用中，这里可以通过特定 API 拿到物理路径。
    // 当前我们取其 name 和 webkitRelativePath 作为演示。
    const newItems = Array.from(e.dataTransfer.files).map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      originalName: file.name,
      path: (file as any).path || file.name, // Electron/Node 环境补丁
      status: 'pending' as const
    }));
    
    setItems(prev => [...prev, ...newItems]);
  }, []);

  const handleStartRename = async () => {
    if (items.length === 0) return;
    setIsProcessing(true);
    
    // 将状态全部设为处理中
    setItems(prev => prev.map(item => ({ ...item, status: 'processing' })));

    try {
      const payload = {
        files: items.map((item, index) => ({ row: index, name: item.originalName, path: item.path })),
        rules: rules.split('\n').filter(r => r.trim()),
        threads
      };
      
      // 触发后端任务
      await axios.post('http://127.0.0.1:8000/api/tasks/rename', payload);
      
      // 真实项目中，这里应通过 WebSocket 监听具体的进度
      // 这里为了演示流程，我们模拟一个完成状态
      setTimeout(() => {
        setItems(prev => prev.map(item => ({ 
          ...item, 
          status: 'success', 
          result: `Cleaned_${item.originalName}` 
        })));
        setIsProcessing(false);
      }, 3000);

    } catch (error) {
      console.error('Rename failed', error);
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex gap-6">
        {/* 控制面板 */}
        <div className="w-1/3 space-y-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">自定义降噪规则</h3>
            <textarea 
              value={rules}
              onChange={(e) => setRules(e.target.value)}
              className="w-full h-32 p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none resize-none"
              placeholder="每行输入一个正则或屏蔽词..."
            />
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">执行操作</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">并发线程数</span>
                <input 
                  type="number" 
                  value={threads}
                  onChange={(e) => setThreads(Number(e.target.value))}
                  className="w-16 p-2 text-center border border-slate-200 rounded-lg outline-none focus:border-primary"
                  min="1" max="10"
                />
              </div>
              <button 
                onClick={handleStartRename}
                disabled={isProcessing || items.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-blue-600 disabled:bg-slate-300 text-white py-3 rounded-xl font-medium transition-colors shadow-sm"
              >
                {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : "🚀 开始后台识别"}
              </button>
              <button 
                onClick={() => setItems([])}
                disabled={isProcessing || items.length === 0}
                className="w-full py-3 bg-rose-50 text-rose-600 hover:bg-rose-100 disabled:opacity-50 rounded-xl font-medium transition-colors"
              >
                清空待处理列表
              </button>
            </div>
          </div>
        </div>

        {/* 拖拽与表格区 */}
        <div className="w-2/3 flex flex-col gap-6">
          <div 
            onDragOver={onDragOver}
            onDrop={onDrop}
            className="h-32 border-2 border-dashed border-slate-300 rounded-2xl bg-slate-50 flex flex-col items-center justify-center text-slate-500 hover:bg-slate-100 hover:border-primary transition-colors cursor-pointer"
          >
            <UploadCloud className="w-8 h-8 text-slate-400 mb-2" />
            <p>将视频文件拖拽到此处 (支持 mp4, mkv, avi 等)</p>
          </div>

          <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="font-semibold text-slate-800">待重命名文件列表 ({items.length})</h3>
            </div>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-sm">
                    <th className="px-6 py-3 font-medium">原文件名</th>
                    <th className="px-6 py-3 font-medium">识别状态</th>
                    <th className="px-6 py-3 font-medium">预览结果</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-6 py-8 text-center text-slate-400 italic">
                        暂无文件，请拖入视频
                      </td>
                    </tr>
                  ) : (
                    items.map(item => (
                      <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-3 text-slate-700 truncate max-w-[200px]" title={item.originalName}>
                          {item.originalName}
                        </td>
                        <td className="px-6 py-3">
                          {item.status === 'pending' && <span className="text-slate-400 text-sm">等待中</span>}
                          {item.status === 'processing' && <span className="flex items-center gap-1 text-blue-500 text-sm"><Loader2 className="w-3 h-3 animate-spin" /> 识别中</span>}
                          {item.status === 'success' && <span className="flex items-center gap-1 text-green-500 text-sm"><CheckCircle2 className="w-3 h-3" /> 完成</span>}
                          {item.status === 'error' && <span className="flex items-center gap-1 text-red-500 text-sm"><XCircle className="w-3 h-3" /> 失败</span>}
                        </td>
                        <td className="px-6 py-3 text-slate-800 font-medium">
                          {item.result || '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
