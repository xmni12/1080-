import { useState } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Tasks } from './pages/Tasks';
import { Rename } from './pages/Rename';
import { Ed2k } from './pages/Ed2k';
import { Database } from './pages/Database';
import { Settings } from './pages/Settings';

function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');

  return (
    <Layout currentTab={currentTab} setCurrentTab={setCurrentTab}>
      {currentTab === 'dashboard' && <Dashboard />}
      {currentTab === 'tasks' && <Tasks />}
      {currentTab === 'rename' && <Rename />}
      {currentTab === 'ed2k' && <Ed2k />}
      {currentTab === 'database' && <Database />}
      {currentTab === 'settings' && <Settings />}
    </Layout>
  );
}

export default App;
