import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Bell,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import {
  createTask,
  deleteTask,
  fetchDueReminders,
  fetchTasks,
  type Task,
  updateTask,
} from '../lib/api';
import './TaskPanel.css';

export const TaskPanel: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [reminders, setReminders] = useState<Task[]>([]);
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'completed'>('all');
  const [filterPriority, setFilterPriority] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Creation form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');

  const loadTasks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchTasks({
        status: filterStatus === 'all' ? undefined : filterStatus,
        priority: filterPriority === 'all' ? undefined : filterPriority,
      });
      setTasks(res.tasks);

      const rems = await fetchDueReminders();
      setReminders(rems);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [filterStatus, filterPriority]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      const created = await createTask({
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
        priority,
      });

      setTasks((prev) => [created, ...prev]);
      setTitle('');
      setDescription('');
      setDueDate('');
      setShowAddForm(false);
      loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  const handleToggleComplete = async (task: Task) => {
    const nextStatus = task.status === 'completed' ? 'pending' : 'completed';
    // Optimistic UI
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: nextStatus } : t))
    );

    try {
      await updateTask(task.id, { status: nextStatus });
      loadTasks();
    } catch {
      // Revert on error
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, status: task.status } : t))
      );
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    try {
      await deleteTask(taskId);
      loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  return (
    <div className="task-panel-container">
      {/* Reminder Alert Banner */}
      {reminders.length > 0 && (
        <div className="reminders-banner">
          <Bell size={16} className="reminder-icon" />
          <div className="reminder-text">
            <strong>{reminders.length} task{reminders.length > 1 ? 's' : ''} require attention:</strong>
            <span className="reminder-items">
              {reminders.map((r) => r.title).join(', ')}
            </span>
          </div>
        </div>
      )}

      {/* Header and Controls */}
      <div className="task-panel-header">
        <div className="task-header-left">
          <Calendar size={18} color="var(--cyan-core)" />
          <h2 className="task-heading">Task & Reminder Manager</h2>
          <span className="task-count-pill">{tasks.length} total</span>
        </div>

        <button
          type="button"
          className="add-task-btn"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? <X size={15} /> : <Plus size={15} />}
          <span>{showAddForm ? 'Cancel' : 'New Task'}</span>
        </button>
      </div>

      {/* Creation Modal / Form */}
      {showAddForm && (
        <form onSubmit={handleCreateTask} className="task-create-form">
          <h3 className="form-title">Create New Task</h3>
          <div className="form-group">
            <input
              type="text"
              placeholder="Task title (e.g. Back up database, review documents)..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="form-input"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <textarea
              placeholder="Optional notes or details..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="form-textarea"
              rows={2}
            />
          </div>

          <div className="form-row">
            <div className="form-field">
              <label className="field-label">Due Date & Time</label>
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="form-input"
              />
            </div>

            <div className="form-field">
              <label className="field-label">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
                className="form-select"
              >
                <option value="low">Low Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="high">High Priority</option>
              </select>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowAddForm(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={!title.trim()}>
              Save Task
            </button>
          </div>
        </form>
      )}

      {/* Filters Bar */}
      <div className="task-filters-bar">
        <div className="filter-group">
          <span className="filter-label">Status:</span>
          {(['all', 'pending', 'completed'] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={`filter-chip ${filterStatus === s ? 'active' : ''}`}
              onClick={() => setFilterStatus(s)}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="filter-group">
          <span className="filter-label">Priority:</span>
          {(['all', 'high', 'medium', 'low'] as const).map((p) => (
            <button
              key={p}
              type="button"
              className={`filter-chip ${filterPriority === p ? 'active' : ''}`}
              onClick={() => setFilterPriority(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="task-error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Tasks List */}
      <div className="tasks-list">
        {isLoading && tasks.length === 0 ? (
          <div className="tasks-empty">Loading tasks from SQLite...</div>
        ) : tasks.length === 0 ? (
          <div className="tasks-empty">
            <CheckCircle2 size={32} color="var(--cyan-subtle)" />
            <p>No tasks found matching current filters.</p>
          </div>
        ) : (
          tasks.map((task) => {
            const isCompleted = task.status === 'completed';
            const isOverdue =
              task.due_date &&
              task.status === 'pending' &&
              new Date(task.due_date) < new Date();

            return (
              <div
                key={task.id}
                className={`task-card ${isCompleted ? 'completed' : ''} ${
                  isOverdue ? 'overdue' : ''
                }`}
              >
                <button
                  type="button"
                  className="task-checkbox"
                  onClick={() => handleToggleComplete(task)}
                  title={isCompleted ? 'Mark as pending' : 'Mark as completed'}
                  aria-label={isCompleted ? 'Mark as pending' : 'Mark as completed'}
                >
                  {isCompleted ? (
                    <CheckCircle2 size={18} color="var(--emerald)" />
                  ) : (
                    <Circle size={18} color="var(--cyan-subtle)" />
                  )}
                </button>

                <div className="task-details">
                  <div className="task-title-row">
                    <span className="task-title-text">{task.title}</span>
                    <span className={`priority-tag priority-${task.priority}`}>
                      {task.priority}
                    </span>
                    {isOverdue && <span className="overdue-tag">Overdue</span>}
                  </div>

                  {task.description && (
                    <p className="task-description-text">{task.description}</p>
                  )}

                  {task.due_date && (
                    <div className="task-due-row">
                      <Clock size={12} />
                      <span>Due: {new Date(task.due_date).toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  className="delete-task-btn"
                  onClick={() => handleDeleteTask(task.id)}
                  title="Delete task"
                  aria-label="Delete task"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default TaskPanel;
