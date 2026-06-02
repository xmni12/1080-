import { useState } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Tasks } from './pages/Tasks';
import { Database } from './pages/Database';
import { Settings } from './pages/Settings';
import { Blacklist } from './pages/Blacklist';
import { Whitelist } from './pages/Whitelist';
import { FailedRecords } from './pages/FailedRecords';
import { Sniper } from './pages/Sniper';
import { TitleBlocklist } from './pages/TitleBlocklist';

function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');

  return (
    <Layout currentTab={currentTab} setCurrentTab={setCurrentTab}>
      {currentTab === 'dashboard' && <Dashboard />}
      {currentTab === 'tasks' && <Tasks />}
      {currentTab === 'sniper' && <Sniper />}
      {currentTab === 'failed_records' && <FailedRecords />}
      {currentTab === 'database' && <Database />}
      {currentTab === 'title_blocklist' && <TitleBlocklist />}
      {currentTab === 'blacklist' && <Blacklist />}
      {currentTab === 'whitelist' && <Whitelist />}
      {currentTab === 'settings' && <Settings />}
    </Layout>
  );
}

export default App;
