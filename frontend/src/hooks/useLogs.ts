import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

export interface LogMessage {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  content: string;
}

export function useLogs(url: string, onQueueUpdate?: (data: any) => void) {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    
    // 1. Fetch history first
    axios.get('http://127.0.0.1:8000/api/ws/history').then(res => {
        if (res.data && Array.isArray(res.data)) {
            const historyLogs: LogMessage[] = res.data
              .filter((item: any) => item.type !== 'queue_update' && item.type !== 'lab_status' && item.type !== 'lab_result')
              .map((item: any) => ({
                id: Math.random().toString(36).substring(2, 9),
                timestamp: new Date().toLocaleTimeString(),
                level: item.level || 'info',
                content: item.message || JSON.stringify(item)
            }));
            setLogs(historyLogs);
        }
        
        // 2. Then connect websocket
        ws = new WebSocket(url);
        wsRef.current = ws;
    
        ws.onopen = () => setIsConnected(true);
        ws.onclose = () => setIsConnected(false);
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'queue_update') {
              if (onQueueUpdate) onQueueUpdate(data.data);
              return; // Do not push to logs
            }
            if (data.type === 'lab_status' || data.type === 'lab_result') {
              return; // Handled in Lab.tsx (which is now removed, but ignore anyway)
            }
            
            const newLog: LogMessage = {
              id: Math.random().toString(36).substring(2, 9),
              timestamp: new Date().toLocaleTimeString(),
              level: data.level || 'info',
              content: data.message || event.data
            };
            setLogs(prev => [...prev.slice(-99), newLog]);
          } catch {
            const newLog: LogMessage = {
              id: Math.random().toString(36).substring(2, 9),
              timestamp: new Date().toLocaleTimeString(),
              level: 'info',
              content: event.data
            };
            setLogs(prev => [...prev.slice(-99), newLog]);
          }
        };
    }).catch(e => {
        console.error("Failed to load history", e);
    });

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [url]);

  const clearLogs = () => setLogs([]);

  return { logs, isConnected, clearLogs };
}
