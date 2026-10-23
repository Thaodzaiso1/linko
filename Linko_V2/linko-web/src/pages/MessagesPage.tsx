import { memo, useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, type DirectMessage, type MessagePeer } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';

const initial = (name: string) => name.trim().split(/\s+/).slice(-2).map(word => word.charAt(0)).join('').toUpperCase();
const timeText = (raw: string) => {
  try { return new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }).format(new Date(raw)); }
  catch { return raw; }
};
const explain = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback;

function MessagesPageInner() {
  const { user } = useAuth();
  const [peers, setPeers] = useState<MessagePeer[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [query, setQuery] = useState('');
  const [messageQuery, setMessageQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DirectMessage[] | null>(null);
  const [searchBusy, setSearchBusy] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [loadedPeer, setLoadedPeer] = useState<string | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasOlder, setHasOlder] = useState(false);
  const [error, setError] = useState('');
  const bottom = useRef<HTMLDivElement>(null);
  const activeRef = useRef<string | null>(null);
  const scrollWhenNew = useRef(true);
  activeRef.current = active;

  const refreshPeers = useCallback(async () => {
    const data = await api.messagePeers();
    setPeers(data);
    setActive(previous => previous ?? data[0]?.username ?? null);
  }, []);

  useEffect(() => {
    let alive = true;
    void api.messagePeers().then(data => {
      if (!alive) return;
      setPeers(data);
      setActive(data[0]?.username ?? null);
    }).catch(err => { if (alive) setError(explain(err, 'Không tải được danh sách trò chuyện')); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!active) { setMessages([]); setHasOlder(false); return; }
    const peer = active;
    let alive = true;
    setMessages([]);
    setLoadedPeer(null);
    setMessageQuery('');
    setSearchResults(null);
    setChatLoading(true);
    scrollWhenNew.current = true;

    const update = async (initialLoad = false) => {
      if (document.visibilityState === 'hidden') return;
      try {
        const data = await api.directMessages(peer);
        if (!alive || activeRef.current !== peer) return;
        if (initialLoad) setHasOlder(data.length === 50);
        setLoadedPeer(peer);
        setMessages(previous => {
          // Preserve pages loaded with "Xem tin cũ" during polling.
          const all = [...previous, ...data];
          const unique = new Map(all.map(item => [item.id, item]));
          return [...unique.values()].sort((a, b) => a.id - b.id);
        });
        await api.markMessagesRead(peer);
        if (alive) void refreshPeers().catch(() => undefined);
        setError('');
      } catch (err) { if (alive) setError(explain(err, 'Không tải được tin nhắn')); }
      finally { if (initialLoad && alive) setChatLoading(false); }
    };
    void update(true);
    const timer = window.setInterval(() => { void update(); }, 15000);
    const onFocus = () => { void update(); };
    window.addEventListener('focus', onFocus);
    return () => { alive = false; window.clearInterval(timer); window.removeEventListener('focus', onFocus); };
  }, [active, refreshPeers]);

  useEffect(() => {
    if (scrollWhenNew.current) bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    else scrollWhenNew.current = true;
  }, [messages.length, active]);

  const loadOlder = async () => {
    if (!active || !messages.length || loadingOlder) return;
    const peer = active;
    setLoadingOlder(true); setError('');
    try {
      const older = await api.directMessages(peer, messages[0].id);
      if (activeRef.current !== peer) return;
      scrollWhenNew.current = false;
      setMessages(previous => [...older.filter(item => !previous.some(existing => existing.id === item.id)), ...previous]);
      setHasOlder(older.length === 50);
    } catch (err) { setError(explain(err, 'Không tải được tin nhắn cũ')); }
    finally { setLoadingOlder(false); }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!active || !text.trim() || busy) return;
    const peer = active;
    setBusy(true); setError('');
    try {
      const sent = await api.sendDirectMessage(peer, text.trim());
      if (activeRef.current === peer) {
        scrollWhenNew.current = true;
        setMessages(previous => previous.some(item => item.id === sent.id) ? previous : [...previous, sent]);
      }
      setText('');
      await refreshPeers();
    } catch (err) { setError(explain(err, 'Không gửi được tin nhắn')); }
    finally { setBusy(false); }
  };

  const searchConversation = async (event: FormEvent) => {
    event.preventDefault();
    if (!active || !messageQuery.trim()) { setSearchResults(null); return; }
    const selectedPeer = active;
    setSearchBusy(true); setError('');
    try {
      const results = await api.searchMessages(messageQuery.trim(), selectedPeer);
      if (activeRef.current === selectedPeer) setSearchResults(results);
    } catch (err) { setError(explain(err, 'Không thể tìm tin nhắn')); }
    finally { setSearchBusy(false); }
  };

  const filtered = peers.filter(peer => `${peer.full_name} ${peer.username}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi').trim()));
  const peer = peers.find(item => item.username === active);

  return <div className="linko-chat-wrap">
    <div className="linko-chat-head"><div><span className="linko-kicker"><span/> LINKO MESSAGES</span><h2>Tin nhắn <span>💬</span></h2><p>Trò chuyện riêng với các tài khoản Linko.</p></div><button type="button" onClick={() => void refreshPeers().catch(err => setError(explain(err, 'Không thể làm mới')))}><Icon name="refresh" size={16}/> Làm mới</button></div>
    {error && <div className="linko-feed-error" role="alert">{error}<button type="button" onClick={() => setError('')} aria-label="Đóng thông báo">×</button></div>}
    <div className="linko-chat-grid">
      <aside className="linko-chat-contacts"><header><h3>Cuộc trò chuyện</h3><small>{peers.length} tài khoản</small></header>
        <div className="linko-peer-search"><Icon name="search" size={16}/><input aria-label="Tìm người trò chuyện" placeholder="Tìm đồng nghiệp..." value={query} onChange={event => setQuery(event.target.value)}/></div>
        {loading ? <p className="linko-chat-empty">Đang tải...</p> : filtered.length === 0 ? <p className="linko-chat-empty">{query ? 'Không có tài khoản phù hợp.' : 'Chưa có tài khoản để nhắn tin.'}</p> : filtered.map(item => <button type="button" className={`linko-chat-peer${active === item.username ? ' selected' : ''}`} key={item.username} onClick={() => { setActive(item.username); setText(''); }} aria-current={active === item.username ? 'true' : undefined}><span className="linko-circle-avatar">{initial(item.full_name)}</span><span className="linko-peer-data"><strong>{item.full_name}</strong><small>{item.last_message || `${item.role} · Bắt đầu trò chuyện`}</small></span>{item.unread > 0 && <span className="linko-unread">{item.unread}</span>}</button>)}
      </aside>
      <section className="linko-chat-panel" aria-label="Nội dung cuộc trò chuyện">
        <header className="linko-chat-title"><span className="linko-circle-avatar">{initial(peer?.full_name || '?')}</span><div><strong>{peer?.full_name || 'Chọn một cuộc trò chuyện'}</strong><small>{peer ? `@${peer.username} · Tin nhắn nội bộ` : 'Chưa chọn người nhận'}</small></div></header>
        {active && <form className="linko-message-search" onSubmit={event => void searchConversation(event)}>
          <Icon name="search" size={16}/>
          <input aria-label="Tìm nội dung tin nhắn" placeholder="Tìm trong cuộc trò chuyện..." maxLength={100}
            value={messageQuery} onChange={event => setMessageQuery(event.target.value)} />
          <button type="submit" disabled={searchBusy || !messageQuery.trim()}>{searchBusy ? 'Đang tìm...' : 'Tìm'}</button>
          {searchResults !== null && <button type="button" onClick={() => { setSearchResults(null); setMessageQuery(''); }}>Đóng</button>}
        </form>}
        {searchResults !== null && <section className="linko-message-results" aria-label="Kết quả tìm tin nhắn">
          <strong>{searchResults.length ? `${searchResults.length} kết quả gần nhất` : 'Không tìm thấy tin nhắn phù hợp'}</strong>
          {searchResults.map(message => <article key={message.id}><small>{message.sender_username === user?.username ? 'Bạn' : peer?.full_name} · {timeText(message.created_at)}</small><p>{message.content}</p></article>)}
        </section>}
        <div className="linko-chat-thread">
          {hasOlder && <button type="button" className="linko-older-btn" disabled={loadingOlder} onClick={() => void loadOlder()}>{loadingOlder ? 'Đang tải...' : '↑ Xem tin nhắn cũ'}</button>}
          {!active ? <div className="linko-chat-placeholder"><Icon name="mail" size={30}/><strong>Chọn đồng nghiệp để bắt đầu</strong><p>Tin nhắn được lưu trong hệ thống Linko.</p></div> : (chatLoading || loadedPeer !== active) ? <div className="linko-chat-placeholder" role="status">Đang tải cuộc trò chuyện...</div> : messages.length === 0 ? <div className="linko-chat-placeholder"><Icon name="mail" size={30}/><strong>Hãy nói lời chào!</strong><p>Chưa có tin nhắn nào trong cuộc trò chuyện.</p></div> : messages.map(message => <div className={`linko-chat-message${message.sender_username === user?.username ? ' mine' : ''}`} key={message.id}><div className="linko-chat-bubble">{message.content}</div><time dateTime={message.created_at}>{timeText(message.created_at)} {message.sender_username === user?.username && message.is_read ? ' · Đã xem' : ''}</time></div>)}
          <div ref={bottom}/>
        </div>
        <form className="linko-chat-send" onSubmit={send}><input aria-label="Soạn tin nhắn" placeholder={active ? 'Aa · Viết tin nhắn...' : 'Chọn người nhận trước'} maxLength={1000} value={text} onChange={event => setText(event.target.value)} disabled={!active}/><button type="submit" disabled={busy || !active || !text.trim()} aria-label="Gửi tin nhắn"><Icon name="arrowup" size={19}/></button></form>
      </section>
    </div>
    <p className="linko-chat-footnote">Tin nhắn riêng chỉ hiển thị cho hai tài khoản tham gia. Hệ thống cập nhật khoảng 15 giây khi đang mở, chưa hỗ trợ WebSocket realtime.</p>
  </div>;
}
export const MessagesPage = memo(MessagesPageInner);
