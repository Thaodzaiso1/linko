import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';

type Props<T> = {
  items: T[];
  /** Ước lượng chiều cao 1 ô (px) — dùng để tính cửa sổ ảo */
  estimateItemHeight?: number;
  /** min width mỗi cột, khớp CSS grid auto-fill */
  minColumnWidth?: number;
  gap?: number;
  overscan?: number;
  getKey: (item: T, index: number) => string | number;
  renderItem: (item: T, index: number) => ReactNode;
  className?: string;
  /** Bật virtual khi items.length >= threshold */
  threshold?: number;
};

/**
 * Grid ảo nhẹ (không dependency).
 * Khi items < threshold → render full như grid thường.
 * Khi >= threshold → chỉ mount các ô trong viewport + overscan.
 */
function VirtualGridInner<T>({
  items,
  estimateItemHeight = 168,
  minColumnWidth = 228,
  gap = 8,
  overscan = 2,
  getKey,
  renderItem,
  className = 'emp-grid',
  threshold = 200,
}: Props<T>) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(600);
  const [viewportW, setViewportW] = useState(900);

  const cols = useMemo(() => {
    const w = Math.max(viewportW, minColumnWidth);
    return Math.max(1, Math.floor((w + gap) / (minColumnWidth + gap)));
  }, [viewportW, minColumnWidth, gap]);

  const rowCount = Math.ceil(items.length / cols) || 1;
  const rowHeight = estimateItemHeight + gap;
  const totalHeight = rowCount * rowHeight;

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;

    const measure = () => {
      setViewportH(el.clientHeight || 600);
      setViewportW(el.clientWidth || 900);
    };
    measure();

    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const onScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    setScrollTop(el.scrollTop);
  }, []);

  // Dưới ngưỡng: render đầy đủ, không virtual
  if (items.length < threshold) {
    return (
      <div className={className}>
        {items.map((item, i) => (
          <div key={getKey(item, i)}>{renderItem(item, i)}</div>
        ))}
      </div>
    );
  }

  const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const visibleRows = Math.ceil(viewportH / rowHeight) + overscan * 2;
  const endRow = Math.min(rowCount - 1, startRow + visibleRows);

  const cells: ReactNode[] = [];
  for (let row = startRow; row <= endRow; row++) {
    for (let col = 0; col < cols; col++) {
      const index = row * cols + col;
      if (index >= items.length) break;
      const item = items[index];
      const style: CSSProperties = {
        position: 'absolute',
        top: row * rowHeight,
        left: `calc(${(col * 100) / cols}% + ${col === 0 ? 0 : gap / 2}px)`,
        width: `calc(${100 / cols}% - ${gap * ((cols - 1) / cols)}px)`,
        height: estimateItemHeight,
        boxSizing: 'border-box',
      };
      cells.push(
        <div key={getKey(item, index)} style={style} className="virtual-grid-cell">
          {renderItem(item, index)}
        </div>
      );
    }
  }

  return (
    <div
      ref={scrollerRef}
      className="virtual-grid-scroller"
      onScroll={onScroll}
      style={{
        maxHeight: 'min(70vh, 720px)',
        overflow: 'auto',
        position: 'relative',
        borderRadius: 14,
      }}
    >
      <div
        className={className}
        style={{
          position: 'relative',
          height: totalHeight,
          display: 'block',
          margin: 0,
        }}
      >
        {cells}
      </div>
      <div className="virtual-grid-hint" aria-hidden>
        Đang hiển thị ảo {items.length} mục · ~{endRow - startRow + 1} hàng trong viewport
      </div>
    </div>
  );
}

export const VirtualGrid = memo(VirtualGridInner) as typeof VirtualGridInner;
