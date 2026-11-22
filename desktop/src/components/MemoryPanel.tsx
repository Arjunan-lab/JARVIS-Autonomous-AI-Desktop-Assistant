import { useEffect, useState } from 'react';
import {
  AlertCircle,
  Brain,
  Edit3,
  FileText,
  FolderSearch,
  Plus,
  Save,
  Search,
  ShieldCheck,
  Tag,
  Trash2,
  X,
} from 'lucide-react';
import {
  createMemory,
  deleteMemory,
  fetchMemories,
  searchMemoryAndDocs,
  updateMemory,
  type DocumentSearchResult,
  type Memory,
  type MemoryCategory,
} from '../lib/api';
import './MemoryPanel.css';

export function MemoryPanel() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [docResults, setDocResults] = useState<DocumentSearchResult[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [approvedOnly, setApprovedOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchDocs, setSearchDocs] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New Memory Modal state
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [newCategory, setNewCategory] = useState<MemoryCategory>('preference');
  const [newContent, setNewContent] = useState<string>('');
  const [newApproved, setNewApproved] = useState<boolean>(true);

  // Inline editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [editCategory, setEditCategory] = useState<MemoryCategory>('preference');

  // Stats
  const [counts, setCounts] = useState({
    total: 0,
    preference: 0,
    project: 0,
    knowledge: 0,
    task_history: 0,
  });

  const loadMemories = async () => {
    try {
      setLoading(true);
      setError(null);

      if (searchQuery.trim()) {
        const results = await searchMemoryAndDocs(
          searchQuery.trim(),
          activeCategory === 'all' ? undefined : activeCategory,
          searchDocs
        );
        setMemories(results.memories);
        setDocResults(results.documents);
      } else {
        const data = await fetchMemories({
          category: activeCategory === 'all' ? undefined : activeCategory,
          approved_only: approvedOnly ? true : undefined,
        });
        setMemories(data.memories);
        setDocResults([]);
        setCounts({
          total: data.total,
          preference: data.preference_count,
          project: data.project_count,
          knowledge: data.knowledge_count,
          task_history: data.task_history_count,
        });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [activeCategory, approvedOnly, searchQuery, searchDocs]);

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    try {
      await createMemory({
        category: newCategory,
        content: newContent.trim(),
        approved: newApproved,
      });
      setNewContent('');
      setNewCategory('preference');
      setNewApproved(true);
      setIsCreating(false);
      await loadMemories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save memory');
    }
  };

  const handleStartEdit = (memory: Memory) => {
    setEditingId(memory.id);
    setEditContent(memory.content);
    setEditCategory(memory.category);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editContent.trim()) return;

    try {
      await updateMemory(id, {
        content: editContent.trim(),
        category: editCategory,
      });
      setEditingId(null);
      await loadMemories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update memory');
    }
  };

  const handleToggleApproval = async (memory: Memory) => {
    try {
      await updateMemory(memory.id, {
        approved: !memory.approved,
      });
      await loadMemories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to toggle approval');
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await deleteMemory(id);
      await loadMemories();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete memory');
    }
  };

  return (
    <div className="memory-panel-container">
      {/* Header and Controls */}
      <div className="memory-header-card">
        <div className="memory-header-info">
          <h2 className="memory-title">
            <Brain size={18} color="var(--accent)" />
            <span>Memory & Knowledge Base</span>
          </h2>
          <p className="memory-subtitle">
            Explicitly approved user preferences, project context, and secure local file search
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsCreating(true)}
          className="new-memory-btn"
        >
          <Plus size={14} />
          <span>New Memory</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div className="memory-controls-section">
        <div className="memory-search-row">
          <div className="search-input-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search memories or documents (e.g. telemetry, dark mode, preferences)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="memory-search-input"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="search-clear-btn"
                title="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <label className="search-files-toggle">
            <input
              type="checkbox"
              checked={searchDocs}
              onChange={(e) => setSearchDocs(e.target.checked)}
            />
            <FolderSearch size={14} color="var(--accent)" />
            <span>Search Local Files</span>
          </label>
        </div>

        {/* Category Filter Chips */}
        <div className="category-chips-row">
          {[
            { id: 'all', label: 'All', count: counts.total },
            { id: 'preference', label: 'Preferences', count: counts.preference },
            { id: 'project', label: 'Projects', count: counts.project },
            { id: 'knowledge', label: 'Knowledge', count: counts.knowledge },
            { id: 'task_history', label: 'Task History', count: counts.task_history },
          ].map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setActiveCategory(cat.id)}
              className={`category-chip ${activeCategory === cat.id ? 'active' : ''}`}
            >
              <span>{cat.label}</span>
              {!searchQuery && <span className="chip-count">{cat.count}</span>}
            </button>
          ))}

          <button
            type="button"
            onClick={() => setApprovedOnly(!approvedOnly)}
            className={`approved-filter-btn ${approvedOnly ? 'active' : ''}`}
          >
            <ShieldCheck size={14} />
            <span>Approved Only</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert-banner">
          <AlertCircle size={15} color="var(--color-error)" />
          <span>{error}</span>
        </div>
      )}

      {/* New Memory Modal */}
      {isCreating && (
        <div className="modal-overlay">
          <div className="modal-dialog">
            <h3 className="modal-title">
              <Plus size={16} color="var(--accent)" />
              <span>Add Explicit Memory</span>
            </h3>
            <form onSubmit={handleCreateMemory} className="modal-form">
              <div className="modal-field">
                <label className="modal-label">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                  className="modal-select"
                >
                  <option value="preference">User Preference</option>
                  <option value="project">Project Context</option>
                  <option value="knowledge">Factual Knowledge</option>
                  <option value="task_history">Task History</option>
                </select>
              </div>

              <div className="modal-field">
                <label className="modal-label">Memory Content</label>
                <textarea
                  rows={3}
                  placeholder="Enter memory details (e.g. Always respond in concise technical terms)..."
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  className="modal-textarea"
                  required
                />
              </div>

              <label className="modal-checkbox-row">
                <input
                  type="checkbox"
                  id="new-approved"
                  checked={newApproved}
                  onChange={(e) => setNewApproved(e.target.checked)}
                />
                <span>Explicitly approve memory persistence</span>
              </label>

              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Memory
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Content Area */}
      <div className="memory-list-scroll">
        {loading ? (
          <div className="memory-loading-state">
            <span>Accessing memory index…</span>
          </div>
        ) : (
          <>
            {/* Matched Documents Section if searching */}
            {searchQuery && docResults.length > 0 && (
              <div className="matched-docs-section">
                <h3 className="section-label-header">
                  <FolderSearch size={14} />
                  <span>Matched Local Documents ({docResults.length})</span>
                </h3>
                <div className="matched-docs-grid">
                  {docResults.map((doc, idx) => (
                    <div key={idx} className="doc-snippet-card">
                      <div className="doc-snippet-header">
                        <span className="doc-file-name">
                          <FileText size={14} color="var(--accent)" />
                          {doc.file_name}
                        </span>
                        {doc.line_number && (
                          <span className="doc-line-badge">Line {doc.line_number}</span>
                        )}
                      </div>
                      <p className="doc-snippet-code">{doc.snippet}</p>
                      <p className="doc-snippet-path" title={doc.file_path}>
                        {doc.file_path}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Memories List */}
            <div className="memories-section">
              {searchQuery && (
                <h3 className="section-label-header" style={{ color: 'var(--text-secondary)' }}>
                  <Tag size={14} />
                  <span>Structured Memories ({memories.length})</span>
                </h3>
              )}

              {memories.length === 0 && (!searchQuery || docResults.length === 0) ? (
                <div className="memory-empty-state">
                  <Brain size={32} color="var(--text-tertiary)" />
                  <p className="memory-empty-title">No memories found</p>
                  <p className="memory-empty-desc">
                    {searchQuery
                      ? 'Try a different search term or category'
                      : 'Add an explicit preference or project context to build JARVIS memory'}
                  </p>
                </div>
              ) : (
                memories.map((memory) => {
                  const isEditing = editingId === memory.id;

                  return (
                    <div key={memory.id} className="memory-card">
                      <div className="memory-card-header">
                        <div className="memory-card-meta">
                          <span className={`memory-category-tag cat-${memory.category}`}>
                            {memory.category.replace('_', ' ')}
                          </span>

                          <button
                            type="button"
                            onClick={() => handleToggleApproval(memory)}
                            title="Click to toggle approved memory status"
                            className={`memory-approval-toggle ${
                              memory.approved ? 'approved' : 'unapproved'
                            }`}
                          >
                            {memory.approved ? (
                              <>
                                <ShieldCheck size={12} />
                                <span>Approved</span>
                              </>
                            ) : (
                              <>
                                <AlertCircle size={12} />
                                <span>Unapproved</span>
                              </>
                            )}
                          </button>
                        </div>

                        <div className="memory-card-actions">
                          {isEditing ? (
                            <>
                              <button
                                type="button"
                                onClick={() => handleSaveEdit(memory.id)}
                                className="icon-action-btn"
                                title="Save changes"
                              >
                                <Save size={14} color="var(--color-success)" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingId(null)}
                                className="icon-action-btn"
                                title="Cancel"
                              >
                                <X size={14} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => handleStartEdit(memory)}
                                className="icon-action-btn"
                                title="Edit memory"
                              >
                                <Edit3 size={14} />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteMemory(memory.id)}
                                className="icon-action-btn delete"
                                title="Delete memory"
                              >
                                <Trash2 size={14} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {isEditing ? (
                        <div className="memory-edit-box">
                          <textarea
                            rows={2}
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            className="memory-edit-textarea"
                          />
                          <div className="memory-edit-category-row">
                            <span>Category:</span>
                            <select
                              value={editCategory}
                              onChange={(e) =>
                                setEditCategory(e.target.value as MemoryCategory)
                              }
                              className="memory-edit-select"
                            >
                              <option value="preference">Preference</option>
                              <option value="project">Project</option>
                              <option value="knowledge">Knowledge</option>
                              <option value="task_history">Task History</option>
                            </select>
                          </div>
                        </div>
                      ) : (
                        <p className="memory-content-text">{memory.content}</p>
                      )}

                      <div className="memory-card-footer">
                        <span>Source: {memory.source || 'user'}</span>
                        <span>
                          {new Date(memory.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default MemoryPanel;
