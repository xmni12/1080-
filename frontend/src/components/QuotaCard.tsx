import { clsx } from 'clsx';
import { DivideIcon as LucideIcon } from 'lucide-react';

interface QuotaCardProps {
  title: string;
  current: number;
  max: number;
  icon: typeof LucideIcon;
  colorClass: string;
  bgClass: string;
}

export function QuotaCard({ title, current, max, icon: Icon, colorClass, bgClass }: QuotaCardProps) {
  const percentage = Math.min(100, Math.round((current / max) * 100));

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex flex-col hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className={clsx("p-3 rounded-xl", bgClass)}>
          <Icon className={clsx("w-6 h-6", colorClass)} />
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-slate-500">今日配额</p>
          <p className="text-2xl font-bold text-slate-800">
            {current} <span className="text-sm font-medium text-slate-400">/ {max}</span>
          </p>
        </div>
      </div>
      
      <div>
        <h3 className="text-lg font-semibold text-slate-700 mb-2">{title}</h3>
        <div className="w-full bg-slate-100 rounded-full h-2.5 mb-1 overflow-hidden">
          <div 
            className={clsx("h-2.5 rounded-full transition-all duration-500", colorClass.replace('text-', 'bg-'))} 
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        <p className="text-xs text-slate-500 text-right">{percentage}%</p>
      </div>
    </div>
  );
}
