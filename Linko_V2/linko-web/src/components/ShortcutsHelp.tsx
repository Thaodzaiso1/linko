import { memo } from 'react';
type Props = { open: boolean; onClose: () => void };

function ShortcutsHelpInner({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal
        aria-label="Keyboard shortcuts"
        onClick={(e) => e.stopPropagation()}
      >
        <h3>Keyboard shortcuts</h3>
        <p className="modal-desc">Console controls</p>
        <ul className="list">
          <li>
            <span>Focus search</span>
            <span>
              <kbd>Ctrl</kbd> + <kbd>K</kbd>
            </span>
          </li>
          <li>
            <span>This help</span>
            <span>
              <kbd>?</kbd>
            </span>
          </li>
          <li>
            <span>Toggle theme</span>
            <span>Topbar ☾ / ☀</span>
          </li>
          <li>
            <span>Navigate</span>
            <span>Sidebar / hash</span>
          </li>
        </ul>
        <div className="modal-actions">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export const ShortcutsHelp = memo(ShortcutsHelpInner);
