export type PathHistoryItem = {
  from_id: number;
  to_id: number;
  from_name: string;
  to_name: string;
  path_length: number | null;
  found: boolean;
  at: string;
};

const KEY = 'linko-path-history';

export function loadHistory(): PathHistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    return [];
  }
}

export function pushHistory(item: PathHistoryItem) {
  const list = loadHistory().filter(
    (x) => !(x.from_id === item.from_id && x.to_id === item.to_id)
  );
  list.unshift(item);
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, 12)));
}

export function clearHistory() {
  localStorage.removeItem(KEY);
}
