import { LayoutDashboard, ListTodo, FileEdit, Database, Settings, Link2, FlaskConical } from 'lucide-react';
import { clsx } from 'clsx';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

const navItems = [
  { id: 'dashboard', label: '仪表盘', icon: LayoutDashboard },
  { id: 'tasks', label: '任务中心', icon: ListTodo },
  { id: 'rename', label: '智能重命名', icon: FileEdit },
  { id: 'lab', label: '智能工作台', icon: FlaskConical },
  { id: 'ed2k', label: 'ED2K提取', icon: Link2 },
  { id: 'database', label: '全局仓库', icon: Database },
  { id: 'settings', label: '系统设置', icon: Settings },
];

export function Sidebar({ currentTab, setCurrentTab }: SidebarProps) {
  return (
    <div className="w-64 bg-slate-900 text-slate-300 min-h-screen flex flex-col transition-all duration-300">
      <div className="p-6 flex items-center gap-3 text-white">
        <div className="bg-primary/20 p-2 rounded-lg">
          <Database className="w-6 h-6 text-primary" />
        </div>
        <h1 className="font-bold text-xl tracking-tight">DiscuzSpider</h1>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentTab(item.id)}
              className={clsx(
                "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                isActive 
                  ? "bg-primary text-white shadow-md shadow-primary/20" 
                  : "hover:bg-slate-800 hover:text-slate-100"
              )}
            >
              <Icon className={clsx(
                "w-5 h-5 transition-transform duration-200",
                isActive ? "scale-110" : "group-hover:scale-110"
              )} />
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-center text-slate-500">
          V5.4 交互旗舰版
        </div>
      </div>
    </div>
  );
}
