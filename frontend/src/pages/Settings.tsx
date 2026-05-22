import { useState, useEffect } from 'react';
import { Save, Settings2, Loader2, Download, UploadCloud } from 'lucide-react';
import axios from 'axios';

export function Settings() {
  const [config, setConfig] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/settings');
      setConfig(response.data);
    } catch (error) {
      console.error('Failed to fetch settings', error);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await axios.post('http://127.0.0.1:8000/api/settings', config);
      alert('设置已成功保存并同步到后端！');
    } catch (error) {
      console.error('Failed to save settings', error);
      alert('保存失败，请检查后端运行状态。');
    } finally {
      setIsSaving(false);
    }
  };

  const handleBackup = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/settings/backup', {
        responseType: 'blob', // Important for downloading files
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'discuz_spider_backup.zip';
      if (contentDisposition) {
          const match = contentDisposition.match(/filename="?([^"]+)"?/);
          if (match && match[1]) filename = match[1];
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error: any) {
      console.error('Backup failed', error);
      alert('备份失败：' + (error.message || '未知错误'));
    }
  };

  const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!confirm('警告：导入备份将覆盖当前的系统配置和所有数据库数据！这可能会导致当前任务中断。确认要继续吗？')) {
        e.target.value = ''; // Reset input
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post('http://127.0.0.1:8000/api/settings/restore', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('数据恢复成功！强烈建议重启前后端服务以确保所有数据被正确加载。');
      fetchSettings(); // Refresh settings
    } catch (error: any) {
      console.error('Restore failed', error);
      alert('恢复失败：' + (error.response?.data?.detail || error.message));
    } finally {
        e.target.value = ''; // Reset input
    }
  };

  const updateSection = (section: string, field: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      sections: {
        ...prev.sections,
        [section]: {
          ...prev.sections[section],
          [field]: value
        }
      }
    }));
  };

  if (!config) return <div className="p-8 text-center text-slate-500 animate-pulse">正在读取系统配置...</div>;

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex items-center justify-between bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 p-3 rounded-xl">
            <Settings2 className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">系统全局设置</h3>
            <p className="text-sm text-slate-500">修改参数后点击右上角保存即可生效</p>
          </div>
        </div>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 bg-primary hover:bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors shadow-sm disabled:opacity-70"
        >
          {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          保存设置
        </button>
      </div>

      {['4k', 'vr', 'hd', 'sub'].map(section => (
        <div key={section} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <h4 className="font-semibold text-slate-800 mb-4 uppercase flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="w-1.5 h-4 bg-primary rounded-full"></span>
            {section} 版块配置
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">起始页码</label>
              <input 
                type="number" 
                value={config.sections[section]?.start_page || 1}
                onChange={e => updateSection(section, 'start_page', Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">历史进度</label>
              <input 
                type="number" 
                value={config.sections[section]?.history_page || 1}
                onChange={e => updateSection(section, 'history_page', Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">每日爬取配额 (达到数量后自动停止)</label>
              <input 
                type="number" 
                value={config.sections[section]?.daily_limit || 55}
                onChange={e => updateSection(section, 'daily_limit', Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">极速追新模式扫描深度 (页数)</label>
              <input 
                type="number" 
                value={config.sections[section]?.quick_scan_depth || 10}
                onChange={e => updateSection(section, 'quick_scan_depth', Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">文件保存绝对路径</label>
              <input 
                type="text" 
                value={config.sections[section]?.save_path || ''}
                onChange={e => updateSection(section, 'save_path', e.target.value)}
                placeholder="例如: D:\Downloads\Spider"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">白名单单人专属保存路径 (留空则存入子目录)</label>
              <input 
                type="text" 
                value={config.sections[section]?.whitelist_save_path || ''}
                onChange={e => updateSection(section, 'whitelist_save_path', e.target.value)}
                placeholder="例如: E:\Favorites (留空则默认保存在上面的路径\Favorites中)"
                className="w-full px-3 py-2 bg-emerald-50/50 border border-emerald-200 rounded-lg outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div className="space-y-2 flex items-center gap-3 md:col-span-2 pt-2">
              <input 
                type="checkbox" 
                id={`sim_${section}`}
                checked={config.sections[section]?.simulate_human ?? true}
                onChange={e => updateSection(section, 'simulate_human', e.target.checked)}
                className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
              />
              <label htmlFor={`sim_${section}`} className="text-sm font-medium text-slate-700 cursor-pointer">
                启用人类行为模拟 (防封控机制)
              </label>
            </div>
            <div className="space-y-2 flex items-center gap-3 md:col-span-2 pt-2 border-t border-slate-100">
              <input 
                type="checkbox" 
                id={`timer_enabled_${section}`}
                checked={config.sections[section]?.timer_enabled ?? false}
                onChange={e => updateSection(section, 'timer_enabled', e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded border-gray-300 focus:ring-emerald-600"
              />
              <label htmlFor={`timer_enabled_${section}`} className="text-sm font-medium text-slate-700 cursor-pointer">
                开启此版块的每日定时自动爬取任务
              </label>
              
              {config.sections[section]?.timer_enabled && (
                <div className="flex items-center gap-2 ml-4">
                  <span className="text-sm text-slate-500">定时启动时间:</span>
                  <input 
                    type="time" 
                    value={config.sections[section]?.timer_time || "03:00"}
                    onChange={e => updateSection(section, 'timer_time', e.target.value)}
                    className="px-2 py-1 bg-slate-50 border border-slate-200 rounded-md outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
      
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <h4 className="font-semibold text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="w-1.5 h-4 bg-slate-800 rounded-full"></span>
            高级参数
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="space-y-3 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">浏览器内核引擎选择 (Browser Path)</label>
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="browser_type"
                    checked={!config.browser_path || config.browser_path === ''}
                    onChange={() => setConfig({ ...config, browser_path: '' })}
                    className="w-4 h-4 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-slate-600">自动检测 (默认)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="browser_type"
                    checked={config.browser_path?.toLowerCase() === 'edge'}
                    onChange={() => setConfig({ ...config, browser_path: 'edge' })}
                    className="w-4 h-4 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-slate-600">Microsoft Edge</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="browser_type"
                    checked={config.browser_path?.toLowerCase() === 'chrome'}
                    onChange={() => setConfig({ ...config, browser_path: 'chrome' })}
                    className="w-4 h-4 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-slate-600">Google Chrome</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="browser_type"
                    checked={!!config.browser_path && !['edge', 'chrome', ''].includes(config.browser_path.toLowerCase())}
                    onChange={() => setConfig({ ...config, browser_path: 'C:\\' })}
                    className="w-4 h-4 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-slate-600">自定义物理路径</span>
                </label>
              </div>

              {!!config.browser_path && !['edge', 'chrome', ''].includes(config.browser_path.toLowerCase()) && (
                <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-300">
                  <input 
                    type="text" 
                    value={config.browser_path}
                    onChange={e => setConfig({ ...config, browser_path: e.target.value })}
                    placeholder="请输入可执行文件的绝对路径，例如: D:\MyBrowser\chrome.exe"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary font-mono text-sm"
                  />
                </div>
              )}
            </div>
            <div className="space-y-2 flex items-center gap-3">
                <input 
                  type="checkbox" 
                  id="hide_browser"
                  checked={config.hide_browser ?? false}
                  onChange={e => setConfig({ ...config, hide_browser: e.target.checked })}
                  className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
                />
                <label htmlFor="hide_browser" className="text-sm font-medium text-slate-700 cursor-pointer">
                  开启无头静默运行 (极深隐身模式)
                </label>
            </div>
            <div className="space-y-2 flex items-center gap-3">
                <label htmlFor="spider_threads" className="text-sm font-medium text-slate-700">爬虫多线程数量</label>
                <input 
                  type="number" 
                  id="spider_threads"
                  value={config.spider_threads ?? 1}
                  onChange={e => setConfig({ ...config, spider_threads: Number(e.target.value) })}
                  className="w-20 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary text-center"
                  min="1" max="10"
                />
                <span className="text-xs text-slate-500">(提升并发抓取效率)</span>
            </div>
          </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 border-l-4 border-l-purple-500">
          <h4 className="font-semibold text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="w-1.5 h-4 bg-purple-500 rounded-full"></span>
            数据安全与迁移
          </h4>
          <div className="text-sm text-slate-500 mb-6">
            你可以将当前的所有核心数据（包含系统配置、历史进度水位线、全局死链回收站记录、以及所有的心动白名单与屏蔽词库）打包为一个压缩包进行异地备份。在更换电脑或重装系统后，可以通过导入此文件实现一键无损迁移。
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button 
                onClick={handleBackup}
                className="flex items-center justify-center gap-3 bg-slate-50 border border-slate-200 hover:bg-purple-50 hover:border-purple-300 hover:text-purple-700 text-slate-700 px-6 py-4 rounded-xl font-medium transition-all shadow-sm"
              >
                <Download className="w-5 h-5" />
                <div className="text-left">
                  <div className="font-bold">生成全量备份快照</div>
                  <div className="text-xs opacity-70">导出 .zip 备份包到本地</div>
                </div>
              </button>
              
              <div className="relative">
                  <input 
                    type="file" 
                    accept=".zip"
                    onChange={handleRestore}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    title="点击选择备份文件上传"
                  />
                  <button className="w-full flex items-center justify-center gap-3 bg-slate-50 border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-700 text-slate-700 px-6 py-4 rounded-xl font-medium transition-all shadow-sm pointer-events-none">
                    <UploadCloud className="w-5 h-5" />
                    <div className="text-left">
                      <div className="font-bold">导入并覆盖恢复</div>
                      <div className="text-xs opacity-70">上传 .zip 备份包重建环境</div>
                    </div>
                  </button>
              </div>
          </div>
      </div>
    </div>
  );
}
