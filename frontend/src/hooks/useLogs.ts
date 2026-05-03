import { useState, useEffect, useRef } from 'react';

export interface LogMessage {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  content: string;
}

export function useLogs(url: string) {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 建立 WebSocket 连接
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    
    ws.onclose = () => setIsConnected(false);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const newLog: LogMessage = {
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          level: data.level || 'info',
          content: data.message || event.data
        };
        setLogs(prev => [...prev.slice(-999), newLog]); // 限制最大 1000 条日志
      } catch {
        // 非 JSON 格式
        const newLog: LogMessage = {
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          level: 'info',
          content: event.data
        };
        setLogs(prev => [...prev.slice(-999), newLog]);
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const clearLogs = () => setLogs([]);

  return { logs, isConnected, clearLogs };
}
