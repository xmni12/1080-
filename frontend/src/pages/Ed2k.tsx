import { useState, useCallback } from 'react';
import { UploadCloud, Link as LinkIcon, Download, Trash2, Copy, FileText } from 'lucide-react';
import { clsx } from 'clsx';

interface Ed2kLink {
  file: string;
  link: string;
}

export function Ed2k() {
  const [links, setLinks] = useState<Ed2kLink[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const readFileAsText = (file: File, encoding: string): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string || '');
      reader.readAsText(file, encoding);
    });
  };

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.txt'));
    if (files.length === 0) return;

    setIsProcessing(true);
    const newLinks: Ed2kLink[] = [];
    const header = "115視頻格式離綫下載地址：";
    
    for (const file of files) {
      let content = await readFileAsText(file, 'utf-8');
      if (!content.includes(header)) {
        content = await readFileAsText(file, 'gbk');
      }

      if (content.includes(header)) {
        const parts = content.split(header).slice(1);
        for (const part of parts) {
          const lines = part.split('\n').map(l => l.trim());
          for (const line of lines) {
            if (line.toLowerCase().startsWith('ed2k://')) {
              // 简单去重
              if (!newLinks.some(l => l.link === line) && !links.some(l => l.link === line)) {
                newLinks.push({ file: file.name, link: line });
              }
            } else if (!line) {
              continue;
            } else {
              break; // 遇到非空且非 ed2k 链接则结束提取该部分
            }
          }
        }
      }
    }
    
    if (newLinks.length > 0) {
      setLinks(prev => [...prev, ...newLinks]);
    }
    setIsProcessing(false);
  }, [links]);

  const handleDownload = () => {
    if (links.length === 0) return;
    const content = links.map(l => l.link).join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ed2k提取结果.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopy = () => {
    if (links.length === 0) return;
    const content = links.map(l => l.link).join('\n');
    navigator.clipboard.writeText(content).then(() => {
      alert('已成功复制到剪贴板！');
    });
  };

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex gap-6">
        {/* 控制面板 */}
        <div className="w-1/3 bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-primary/10 p-3 rounded-xl">
              <LinkIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-800">ED2K 链接提取</h3>
              <p className="text-sm text-slate-500">纯前端安全解析，无需经过服务器</p>
            </div>
          </div>
          
          <div className="space-y-4 flex-1 flex flex-col justify-end">
             <div className="p-4 bg-blue-50 text-blue-700 rounded-xl text-sm border border-blue-100">
               <p className="mb-2"><strong>工作原理：</strong></p>
               <p>1. 拖入含有 115 离线格式的 txt 文本文件。</p>
               <p>2. 系统自动识别 UTF-8 或 GBK 编码。</p>
               <p>3. 提取特征字符串下方的所有 ed2k 链接并去重。</p>
             </div>
             
             <div className="flex gap-3 pt-4 border-t border-slate-100">
                <button 
                  onClick={handleDownload}
                  disabled={links.length === 0}
                  className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-blue-600 disabled:bg-slate-300 text-white py-2.5 rounded-xl font-medium transition-colors shadow-sm"
                >
                  <Download className="w-4 h-4" /> 导出文件
                </button>
                <button 
                  onClick={handleCopy}
                  disabled={links.length === 0}
                  className="flex items-center justify-center bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 px-4 rounded-xl transition-colors"
                  title="复制全部"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => setLinks([])}
                  disabled={links.length === 0}
                  className="flex items-center justify-center bg-rose-50 hover:bg-rose-100 disabled:opacity-50 text-rose-600 px-4 rounded-xl transition-colors"
                  title="清空表格"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
             </div>
          </div>
        </div>

        {/* 拖拽与表格区 */}
        <div className="w-2/3 flex flex-col gap-6">
          <div 
            onDragOver={onDragOver}
            onDrop={onDrop}
            className={clsx(
              "h-32 border-2 border-dashed border-slate-300 rounded-2xl bg-slate-50 flex flex-col items-center justify-center hover:bg-slate-100 hover:border-primary transition-colors cursor-pointer",
              isProcessing ? "opacity-50" : ""
            )}
          >
            <UploadCloud className="w-8 h-8 text-slate-400 mb-2" />
            <p className="text-slate-500">{isProcessing ? '正在极速解析中...' : '将含有链接的 .txt 文件拖拽到此处'}</p>
          </div>

          <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
              <h3 className="font-semibold text-slate-800">提取结果 ({links.length} 条)</h3>
            </div>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-slate-50 border-b border-slate-100 shadow-sm z-10">
                  <tr className="text-slate-500 text-sm">
                    <th className="px-6 py-3 font-medium w-1/4">来源文件</th>
                    <th className="px-6 py-3 font-medium">ED2K 链接</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {links.length === 0 ? (
                    <tr>
                      <td colSpan={2} className="px-6 py-12 text-center text-slate-400 italic">
                        暂无提取记录，请拖入文件
                      </td>
                    </tr>
                  ) : (
                    links.map((item, index) => (
                      <tr key={index} className="hover:bg-slate-50 transition-colors group">
                        <td className="px-6 py-3">
                          <span className="flex items-center gap-2 text-slate-600 text-sm">
                            <FileText className="w-4 h-4 text-slate-400" />
                            {item.file}
                          </span>
                        </td>
                        <td className="px-6 py-3">
                          <code className="text-sm text-slate-700 break-all bg-slate-50 px-2 py-1 rounded group-hover:bg-white border border-transparent group-hover:border-slate-200 transition-colors">
                            {item.link}
                          </code>
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
