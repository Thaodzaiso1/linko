import { useEffect, useState } from 'react';

export type ToastItem = { id: number; type: 'ok' | 'err' | 'info'; text: string };

let pushFn: ((t: Omit<ToastItem, 'id'>) => void) | null = null;
let seq = 1;

export function toast(type: ToastItem['type'], text: string) {
  pushFn?.({ type, text });
}

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    pushFn = (t) => {
      const id = seq++;
      setItems((prev) => [...prev, { ...t, id }]);
      setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== id)), 3200);
    };
    return () => {
      pushFn = null;
    };
  }, []);

  if (!items.length) return null;
  return (
    <div className="toast-host">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.type === 'ok' ? '✓ ' : t.type === 'err' ? '✗ ' : 'ℹ '}
          {t.text}
        </div>
      ))}
    </div>
  );
}
