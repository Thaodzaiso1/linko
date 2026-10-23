import { memo, type SVGProps, type ReactNode } from 'react';

export type IconName =
  | 'dashboard'
  | 'users'
  | 'network'
  | 'route'
  | 'layers'
  | 'building'
  | 'briefcase'
  | 'chart'
  | 'activity'
  | 'database'
  | 'help'
  | 'logout'
  | 'chevron'
  | 'arrow'
  | 'search'
  | 'sun'
  | 'moon'
  | 'menu'
  | 'close'
  | 'refresh'
  | 'bolt'
  | 'check'
  | 'clock'
  | 'sparkles'
  | 'target'
  | 'globe'
  | 'filter'
  | 'plus'
  | 'shield'
  | 'book'
  | 'download'
  | 'more'
  | 'link'
  | 'git'
  | 'command'
  | 'mail'
  | 'eye'
  | 'eyeoff'
  | 'external'
  | 'arrowup'
  | 'calendar';

type Props = Omit<SVGProps<SVGSVGElement>, 'name'> & {
  name: IconName;
  size?: number;
  strokeWidth?: number;
};

/** Trả về node SVG mới mỗi lần gọi — không tái sử dụng element instance. */
function shape(name: IconName): ReactNode {
  switch (name) {
    case 'dashboard':
      return (
        <>
          <rect x="3" y="3" width="7" height="9" rx="1.4" />
          <rect x="14" y="3" width="7" height="5" rx="1.4" />
          <rect x="14" y="12" width="7" height="9" rx="1.4" />
          <rect x="3" y="16" width="7" height="5" rx="1.4" />
        </>
      );
    case 'users':
      return (
        <>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </>
      );
    case 'network':
      return (
        <>
          <circle cx="12" cy="12" r="3" />
          <circle cx="4.5" cy="5" r="2" />
          <circle cx="19.5" cy="5" r="2" />
          <circle cx="4.5" cy="19" r="2" />
          <circle cx="19.5" cy="19" r="2" />
          <path d="m6 6.5 4 4m4-0.5 4-4m-8 9-4 3m8-3 4 3" />
        </>
      );
    case 'route':
      return (
        <>
          <circle cx="6" cy="18" r="2" />
          <path d="M9 18h7a5 5 0 0 0 0-10H9a3 3 0 0 1 0-6h7" />
          <path d="m13 5 3-3 3 3" />
        </>
      );
    case 'layers':
      return (
        <>
          <path d="m12 2 9 5-9 5-9-5 9-5Z" />
          <path d="m3 12 9 5 9-5M3 17l9 5 9-5" />
        </>
      );
    case 'building':
      return (
        <>
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="M9 21v-4h6v4M8 7h1m6 0h1M8 11h1m6 0h1" />
        </>
      );
    case 'briefcase':
      return (
        <>
          <rect x="3" y="7" width="18" height="14" rx="2" />
          <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18" />
        </>
      );
    case 'chart':
      return (
        <>
          <path d="M3 3v18h18" />
          <path d="m7 15 4-5 3 3 6-8" />
        </>
      );
    case 'activity':
      return <path d="M22 12h-4l-3 9L9 3l-3 9H2" />;
    case 'database':
      return (
        <>
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3" />
        </>
      );
    case 'help':
      return (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M9 9a3 3 0 1 1 5.5 1.5C13 12 12 12 12 14" />
          <path d="M12 17h.01" />
        </>
      );
    case 'logout':
      return (
        <>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <path d="m16 17 5-5-5-5M21 12H9" />
        </>
      );
    case 'chevron':
      return <path d="m9 18 6-6-6-6" />;
    case 'arrow':
      return <path d="M5 12h14m-6-6 6 6-6 6" />;
    case 'search':
      return (
        <>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-4-4" />
        </>
      );
    case 'sun':
      return (
        <>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </>
      );
    case 'moon':
      return <path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" />;
    case 'menu':
      return <path d="M4 6h16M4 12h16M4 18h16" />;
    case 'close':
      return <path d="M18 6 6 18M6 6l12 12" />;
    case 'refresh':
      return (
        <>
          <path d="M20 11a8 8 0 0 0-14-5L3 9" />
          <path d="M3 4v5h5M4 13a8 8 0 0 0 14 5l3-3" />
          <path d="M21 20v-5h-5" />
        </>
      );
    case 'bolt':
      return <path d="m13 2-9 12h7l-1 8 10-12h-7l0-8Z" />;
    case 'check':
      return <path d="m5 12 4 4L19 6" />;
    case 'clock':
      return (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </>
      );
    case 'sparkles':
      return (
        <>
          <path d="m12 3 1.9 5.9L20 11l-6.1 2.1L12 19l-1.9-5.9L4 11l6.1-2.1L12 3ZM19 17l.7 1.3L21 19l-1.3.7L19 21l-.7-1.3L17 19l1.3-.7L19 17Z" />
        </>
      );
    case 'target':
      return (
        <>
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="5" />
          <circle cx="12" cy="12" r="1" />
        </>
      );
    case 'globe':
      return (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20M12 2c6 6 6 14 0 20M12 2c-6 6-6 14 0 20" />
        </>
      );
    case 'filter':
      return <path d="M4 7h16M7 12h10M10 17h4" />;
    case 'plus':
      return <path d="M12 5v14M5 12h14" />;
    case 'shield':
      return (
        <>
          <path d="m12 22 8-4V6l-8-4-8 4v12l8 4Z" />
          <path d="m9 12 2 2 4-4" />
        </>
      );
    case 'book':
      return (
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
      );
    case 'download':
      return <path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" />;
    case 'more':
      return (
        <>
          <circle cx="5" cy="12" r="1" />
          <circle cx="12" cy="12" r="1" />
          <circle cx="19" cy="12" r="1" />
        </>
      );
    case 'link':
      return (
        <path d="m10 13 4-4M8 16H6a4 4 0 0 1 0-8h4m4 0h4a4 4 0 0 1 0 8h-4" />
      );
    case 'git':
      return (
        <>
          <circle cx="6" cy="3" r="2" />
          <circle cx="6" cy="21" r="2" />
          <circle cx="18" cy="6" r="2" />
          <path d="M6 5v14m0-11c0-2 4-2 9-2" />
        </>
      );
    case 'command':
      return (
        <path d="M9 7V5a2 2 0 1 0-2 2h10a2 2 0 1 0-2-2v14a2 2 0 1 0 2-2H7a2 2 0 1 0 2 2V7Z" />
      );
    case 'mail':
      return (
        <>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="m2 6 10 8L22 6" />
        </>
      );
    case 'eye':
      return (
        <>
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
          <circle cx="12" cy="12" r="3" />
        </>
      );
    case 'eyeoff':
      return (
        <path d="m3 3 18 18M10.5 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a15 15 0 0 1-3.1 3.8M6 6.6C3.5 8.4 2 12 2 12s3.5 7 10 7a10.4 10.4 0 0 0 4-.8" />
      );
    case 'external':
      return (
        <>
          <path d="M14 3h7v7M21 3l-9 9" />
          <path d="M20 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6" />
        </>
      );
    case 'arrowup':
      return <path d="M12 19V5m-6 6 6-6 6 6" />;
    case 'calendar':
      return (
        <>
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M7 3v4m10-4v4M3 10h18" />
        </>
      );
    default:
      return null;
  }
}

function IconInner({ name, size = 18, strokeWidth = 1.8, className, style, ...props }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
      style={{ display: 'inline-block', flexShrink: 0, verticalAlign: 'middle', ...style }}
      {...props}
    >
      {shape(name)}
    </svg>
  );
}

function iconAreEqual(prev: Props, next: Props): boolean {
  return (
    prev.name === next.name &&
    prev.size === next.size &&
    prev.strokeWidth === next.strokeWidth &&
    prev.className === next.className &&
    prev.color === next.color
  );
}

export const Icon = memo(IconInner, iconAreEqual);
