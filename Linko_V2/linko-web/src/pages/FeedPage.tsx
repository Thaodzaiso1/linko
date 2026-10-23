import { memo, useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, type FeedComment, type FeedPost, type FeedNotification } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';

const avatarLetters = (name: string) => name.trim().split(/\s+/).slice(-2).map(word => word[0]).join('').toUpperCase();
const viTime = (raw: string) => {
  try { return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(raw)); }
  catch { return raw; }
};
const errorMessage = (err: unknown, fallback: string) => err instanceof Error ? err.message : fallback;

function FeedPageInner() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [view, setView] = useState<'all' | 'mine' | 'saved'>('all');
  const [bookmarkingId, setBookmarkingId] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [draftQuery, setDraftQuery] = useState('');
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);
  const [likingId, setLikingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');
  const [commentsFor, setCommentsFor] = useState<number | null>(null);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [comments, setComments] = useState<Record<number, FeedComment[]>>({});
  const [commentDraft, setCommentDraft] = useState('');
  const [notifications, setNotifications] = useState<FeedNotification[]>([]);
  const [unread, setUnread] = useState(0);

  const load = useCallback(async (pageNumber = page, filter = query, postView = view) => {
    setLoading(true);
    try {
      const [feed, alerts] = await Promise.all([api.socialPosts(pageNumber, 10, filter, postView), api.socialNotifications()]);
      setPosts(feed.items);
      setTotal(feed.total);
      setNotifications(alerts.items);
      setUnread(alerts.unread);
      setError('');
    } catch (err) { setError(errorMessage(err, 'Không tải được bảng tin')); }
    finally { setLoading(false); }
  }, [page, query, view]);

  useEffect(() => { void load(); }, [load]);

  const submitPost = async (event: FormEvent) => {
    event.preventDefault();
    if (!content.trim() || busy) return;
    setBusy(true); setError('');
    try {
      await api.socialCreatePost(content.trim());
      setContent(''); setPage(1); setQuery(''); setDraftQuery(''); setView('all');
      setNotice('Đăng bài thành công.');
      await load(1, '', 'all');
    } catch (err) { setError(errorMessage(err, 'Đăng bài thất bại')); }
    finally { setBusy(false); }
  };

  const savePost = async (event: FormEvent, id: number) => {
    event.preventDefault();
    if (!editContent.trim() || busy) return;
    setBusy(true); setError('');
    try {
      const updated = await api.socialEditPost(id, editContent.trim());
      setPosts(previous => previous.map(post => post.id === id ? updated : post));
      setEditingId(null);
      setNotice('Đã cập nhật bài viết.');
    } catch (err) { setError(errorMessage(err, 'Không thể sửa bài viết')); }
    finally { setBusy(false); }
  };

  const removePost = async (id: number) => {
    if (busy || !window.confirm('Xóa bài viết và các bình luận liên quan?')) return;
    setBusy(true); setError('');
    try {
      await api.socialDeletePost(id);
      setNotice('Đã xóa bài viết.');
      setCommentsFor(null);
      const destinationPage = posts.length === 1 && page > 1 ? page - 1 : page;
      if (destinationPage !== page) setPage(destinationPage);
      await load(destinationPage, query, view);
    } catch (err) { setError(errorMessage(err, 'Xóa bài thất bại')); }
    finally { setBusy(false); }
  };

  const doLike = async (id: number) => {
    if (likingId !== null) return;
    setLikingId(id); setError('');
    try {
      const data = await api.socialLike(id);
      setPosts(previous => previous.map(post => post.id === id ? { ...post, ...data } : post));
    } catch (err) { setError(errorMessage(err, 'Không thể thích bài viết')); }
    finally { setLikingId(null); }
  };

  const toggleBookmark = async (id: number) => {
    if (bookmarkingId !== null) return;
    setBookmarkingId(id); setError('');
    try {
      const result = await api.socialBookmark(id);
      setPosts(previous => previous.map(post => post.id === id ? { ...post, bookmarked_by_me: result.bookmarked_by_me } : post));
      setNotice(result.bookmarked_by_me ? 'Đã lưu bài viết.' : 'Đã bỏ lưu bài viết.');
      if (view === 'saved' && !result.bookmarked_by_me) {
        // Re-fetch because removing a saved post changes the page count.
        const destination = page > 1 && posts.length === 1 ? page - 1 : page;
        if (destination !== page) setPage(destination);
        await load(destination, query, 'saved');
      }
    } catch (err) { setError(errorMessage(err, 'Không thể lưu bài viết')); }
    finally { setBookmarkingId(null); }
  };

  const toggleComments = async (id: number) => {
    if (commentsFor === id) { setCommentsFor(null); return; }
    setCommentsFor(id); setCommentDraft(''); setCommentsLoading(true);
    try {
      const data = await api.socialComments(id);
      setComments(previous => ({ ...previous, [id]: data }));
    } catch (err) { setError(errorMessage(err, 'Không tải được bình luận')); }
    finally { setCommentsLoading(false); }
  };

  const submitComment = async (event: FormEvent, id: number) => {
    event.preventDefault();
    if (!commentDraft.trim() || busy) return;
    setBusy(true); setError('');
    try {
      const result = await api.socialAddComment(id, commentDraft.trim());
      setComments(previous => ({ ...previous, [id]: [...(previous[id] || []), result] }));
      setPosts(previous => previous.map(post => post.id === id ? { ...post, comments_count: post.comments_count + 1 } : post));
      setCommentDraft('');
    } catch (err) { setError(errorMessage(err, 'Bình luận thất bại')); }
    finally { setBusy(false); }
  };

  const removeComment = async (comment: FeedComment) => {
    if (busy || !window.confirm('Bạn muốn xóa bình luận này?')) return;
    setBusy(true); setError('');
    try {
      await api.socialDeleteComment(comment.id);
      setComments(previous => ({ ...previous, [comment.post_id]: (previous[comment.post_id] || []).filter(item => item.id !== comment.id) }));
      setPosts(previous => previous.map(post => post.id === comment.post_id ? { ...post, comments_count: Math.max(0, post.comments_count - 1) } : post));
    } catch (err) { setError(errorMessage(err, 'Không thể xóa bình luận')); }
    finally { setBusy(false); }
  };

  const clearNotifications = async () => {
    try {
      await api.socialReadNotifications();
      setNotifications(previous => previous.map(item => ({ ...item, is_read: 1 })));
      setUnread(0);
    } catch (err) { setError(errorMessage(err, 'Không thể đánh dấu đã đọc')); }
  };

  const readNotification = async (id: number) => {
    try {
      const result = await api.socialReadNotification(id);
      setNotifications(previous => previous.map(item => item.id === id ? { ...item, is_read: 1 } : item));
      setUnread(result.unread);
    } catch (err) { setError(errorMessage(err, 'Không thể đánh dấu thông báo')); }
  };

  const search = (event: FormEvent) => { event.preventDefault(); setPage(1); setQuery(draftQuery.trim()); };

  return <div className="linko-feed-layout">
    <section className="linko-feed-main" aria-label="Bảng tin nội bộ">
      <div className="linko-feed-heading">
        <div><span className="linko-kicker"><span/> LINKO COMMUNITY</span><h2>Bảng tin của chúng ta <span>✦</span></h2><p>Chia sẻ kiến thức, cập nhật công việc và kết nối với đồng nghiệp.</p></div>
        <button type="button" className="linko-feed-refresh" disabled={loading} onClick={() => void load()}><Icon name="refresh" size={16}/> Làm mới</button>
      </div>
      {error && <div className="linko-feed-error" role="alert">{error}<button type="button" onClick={() => setError('')} aria-label="Đóng thông báo">×</button></div>}
      {notice && <div className="linko-feed-notice" role="status">{notice}<button type="button" onClick={() => setNotice('')} aria-label="Đóng thông báo">×</button></div>}
      <form className="linko-compose" onSubmit={submitPost}>
        <div className="linko-compose-top"><span className="linko-circle-avatar">{avatarLetters(user?.full_name || 'L')}</span><div><strong>{user?.full_name || 'Thành viên Linko'}</strong><small>Chia sẻ với đồng nghiệp trong tổ chức</small></div></div>
        <textarea aria-label="Nội dung bài viết" maxLength={2000} rows={3} value={content} onChange={event => setContent(event.target.value)} placeholder="Chia sẻ cập nhật của bạn với mọi người..."/>
        <div className="linko-compose-footer"><span><Icon name="globe" size={15}/> Nội bộ · {content.length}/2000 ký tự</span><button type="submit" disabled={busy || !content.trim()}><Icon name="arrowup" size={17}/>{busy ? 'Đang xử lý...' : 'Đăng bài'}</button></div>
      </form>
      <div className="linko-feed-filter" role="group" aria-label="Lọc bài viết">
        {([{ key: 'all', label: 'Khám phá' }, { key: 'mine', label: 'Bài của tôi' }, { key: 'saved', label: 'Đã lưu' }] as const).map(option =>
          <button key={option.key} type="button" className={view === option.key ? 'active' : ''}
            aria-pressed={view === option.key} onClick={() => { setPage(1); setView(option.key); }}>
            {option.key === 'saved' ? '🔖 ' : ''}{option.label}
          </button>)}
      </div>
      <div className="linko-feed-list-head"><div><h3>{view === 'saved' ? 'Bài viết đã lưu' : view === 'mine' ? 'Bài viết của tôi' : 'Bài viết mới nhất'}</h3><span>{total} bài viết</span></div><form onSubmit={search}><input value={draftQuery} maxLength={100} onChange={event => setDraftQuery(event.target.value)} placeholder="Tìm nội dung..." aria-label="Tìm bài viết"/><button type="submit" aria-label="Tìm kiếm"><Icon name="search" size={16}/></button></form></div>
      {loading ? <div className="linko-feed-placeholder" role="status">Đang tải bảng tin...</div> : posts.length === 0 ? <div className="linko-feed-placeholder"><Icon name="book" size={28}/><strong>{query ? 'Không tìm thấy bài viết phù hợp' : view === 'saved' ? 'Chưa lưu bài viết nào' : view === 'mine' ? 'Bạn chưa đăng bài viết' : 'Chưa có bài viết nào'}</strong><p>{query ? 'Hãy thử từ khóa khác hoặc xóa bộ lọc.' : view === 'saved' ? 'Bấm Lưu ở một bài viết để đọc lại sau.' : 'Hãy bắt đầu chia sẻ với đồng nghiệp!'}</p>{query && <button type="button" onClick={() => { setQuery(''); setDraftQuery(''); setPage(1); }}>Xóa bộ lọc</button>}</div> : posts.map(post => <article className="linko-post" key={post.id} id={`linko-post-${post.id}`}>
        <div className="linko-post-author">
          <span className="linko-circle-avatar tone-alt">{avatarLetters(post.author_name)}</span>
          <div><strong>{post.author_name}</strong><span>{viTime(post.created_at)}{post.updated_at ? ' · Đã chỉnh sửa' : ''} · <Icon name="globe" size={12}/> Nội bộ</span></div>
          <div className="linko-post-tools">
            {post.author_username === user?.username && <button type="button" disabled={busy} onClick={() => { setEditingId(post.id); setEditContent(post.content); }} aria-label="Chỉnh sửa bài viết">Sửa</button>}
            {(post.author_username === user?.username || user?.role === 'admin') && <button type="button" disabled={busy} onClick={() => void removePost(post.id)} aria-label="Xóa bài viết">Xóa</button>}
          </div>
        </div>
        {editingId === post.id ? <form className="linko-post-edit" onSubmit={event => void savePost(event, post.id)}>
          <textarea aria-label="Sửa nội dung bài viết" rows={4} maxLength={2000} value={editContent} onChange={event => setEditContent(event.target.value)}/>
          <div><span>{editContent.length}/2000</span><button type="button" onClick={() => setEditingId(null)}>Hủy</button><button type="submit" disabled={busy || !editContent.trim()}>Lưu thay đổi</button></div>
        </form> : <p className="linko-post-content">{post.content}</p>}
        <div className="linko-post-counts"><span><span className="linko-like-icon">♥</span> {post.likes_count} lượt thích</span><span>{post.comments_count} bình luận</span></div>
        <div className="linko-post-actions"><button type="button" disabled={likingId !== null} className={post.liked_by_me ? 'is-liked' : ''} onClick={() => void doLike(post.id)}>♥ {post.liked_by_me ? 'Đã thích' : 'Thích'}</button><button type="button" onClick={() => void toggleComments(post.id)}><Icon name="mail" size={17}/> Bình luận</button><button type="button" disabled={bookmarkingId !== null} className={post.bookmarked_by_me ? 'is-saved' : ''} onClick={() => void toggleBookmark(post.id)} aria-pressed={post.bookmarked_by_me}>{post.bookmarked_by_me ? '🔖 Đã lưu' : '♧ Lưu bài'}</button></div>
        {commentsFor === post.id && <div className="linko-comments"><div className="linko-comments-list">
          {commentsLoading ? <p className="linko-empty-comments">Đang tải bình luận...</p> : (comments[post.id] || []).length === 0 ? <p className="linko-empty-comments">Chưa có bình luận. Hãy bắt đầu!</p> : (comments[post.id] || []).map(comment => <div className="linko-comment" key={comment.id}><span className="linko-circle-avatar mini">{avatarLetters(comment.author_name)}</span><div><strong>{comment.author_name}</strong><p>{comment.content}</p><small>{viTime(comment.created_at)}</small>{(comment.author_username === user?.username || user?.role === 'admin') && <button type="button" disabled={busy} onClick={() => void removeComment(comment)} className="linko-comment-delete">Xóa bình luận</button>}</div></div>)}
        </div><form onSubmit={event => void submitComment(event, post.id)}><input value={commentDraft} maxLength={600} onChange={event => setCommentDraft(event.target.value)} aria-label="Viết bình luận" placeholder="Viết bình luận..."/><button type="submit" disabled={busy || !commentDraft.trim()} aria-label="Gửi bình luận"><Icon name="arrowup" size={17}/></button></form></div>}
      </article>)}
      {total > 10 && <nav aria-label="Phân trang bảng tin" className="linko-pagination"><button type="button" disabled={page === 1 || loading} onClick={() => setPage(previous => previous - 1)}>← Trang trước</button><span>Trang {page} / {Math.max(1, Math.ceil(total / 10))}</span><button type="button" disabled={page * 10 >= total || loading} onClick={() => setPage(previous => previous + 1)}>Trang tiếp →</button></nav>}
    </section>
    <aside className="linko-feed-side">
      <div className="linko-side-card linko-notifications">
        <div className="linko-side-title"><div><span className="linko-side-symbol">✦</span><h3>Thông báo</h3>{unread > 0 && <span className="linko-unread">{unread}</span>}</div>{unread > 0 && <button type="button" onClick={() => void clearNotifications()}>Đọc tất cả</button>}</div>
        {notifications.length === 0 ? <div className="linko-side-empty">Bạn chưa có thông báo nào.</div> : notifications.slice(0, 8).map(item => <div className={`linko-notification${!item.is_read ? ' unread' : ''}`} key={item.id}><span className="linko-circle-avatar mini">{avatarLetters(item.actor_name)}</span><div><strong>{item.actor_name}</strong> {item.message}<small>{viTime(item.created_at)}</small>{!item.is_read && <button type="button" className="linko-notif-action" onClick={() => void readNotification(item.id)}>Đánh dấu đã đọc</button>}</div></div>)}
      </div>
      <div className="linko-side-card linko-guidelines"><span className="linko-kicker">KẾT NỐI TỐT HƠN</span><h3>Chào mừng đến Linko <span>💙</span></h3><p>Chia sẻ kiến thức và ghi nhận thành quả của đồng đội để cùng xây dựng cộng đồng tích cực.</p><div><span>01</span> Tôn trọng đồng nghiệp</div><div><span>02</span> Chia sẻ nội dung có ích</div><div><span>03</span> Không đăng thông tin nhạy cảm</div></div>
    </aside>
  </div>;
}

export const FeedPage = memo(FeedPageInner);
