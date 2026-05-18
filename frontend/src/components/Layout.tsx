import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: ReactNode;
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export function Layout({ children, currentTab, setCurrentTab }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar (Fixed) */}
      <div className="flex-shrink-0">
        <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      </div>

      {/* Main Content (Scrollable) */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 h-16 flex items-center px-8 flex-shrink-0 z-10 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-800 capitalize">
            {currentTab === 'dashboard' && '仪表盘 Dashboard'}
            {currentTab === 'tasks' && '任务中心 Tasks Center'}
            {currentTab === 'completion' && '女优补全计划 Completion Plan'}
            {currentTab === 'failed_records' && '死链回收站 Failed Records'}
            {currentTab === 'database' && '全局仓库 Database'}
            {currentTab === 'title_blocklist' && '标题屏蔽词库 Title Blocklist'}
            {currentTab === 'blacklist' && '演员黑名单 Actor Blacklist'}
            {currentTab === 'whitelist' && '心动白名单 Actor Whitelist'}
            {currentTab === 'settings' && '系统设置 Settings'}
          </h2>
          <div className="ml-auto flex items-center gap-4">
             <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-sm font-medium text-slate-600">内核在线</span>
             </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50/50 p-8">
          <div className="max-w-7xl mx-auto h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
