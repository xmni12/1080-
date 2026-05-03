import { useState } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Tasks } from './pages/Tasks';
import { Rename } from './pages/Rename';

function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');

  return (
    <Layout currentTab={currentTab} setCurrentTab={setCurrentTab}>
      {currentTab === 'dashboard' && <Dashboard />}
      {currentTab === 'tasks' && <Tasks />}
      {currentTab === 'rename' && <Rename />}
      
      {currentTab !== 'dashboard' && currentTab !== 'tasks' && currentTab !== 'rename' && (
        <div className="h-full flex flex-col items-center justify-center text-slate-400">
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-100 text-center">
            <h3 className="text-lg font-medium text-slate-700 mb-2">正在开发中</h3>
            <p>当前页面：<span className="font-bold text-primary">{currentTab}</span> 正在紧锣密鼓地构建中...</p>
          </div>
        </div>
      )}
    </Layout>
  );
}

export default App;
