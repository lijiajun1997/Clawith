/**
 * Unified FileBrowser component
 * Replaces duplicated file browsing/editing logic across:
 * - Agent Workspace, Skills, Soul, Memory tabs
 * - Enterprise Knowledge Base
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import MarkdownRenderer from './MarkdownRenderer';
import { useDropZone } from '../hooks/useDropZone';
import {
    IconFile, IconFolder, IconPhoto, IconFileText, IconCode, IconVideo, IconMusic,
    IconArchive, IconDownload, IconTrash, IconUpload, IconFolderPlus, IconPlus,
    IconChevronLeft, IconSearch, IconCheck, IconX, IconRefresh, IconSortAscending,
    IconSortDescending, IconGridDots, IconList, IconEye, IconEyeOff,
    IconFileText as IconFileDescription, IconTable, IconPresentation,
    IconAlertTriangle, IconCheckbox, IconSquare,
    IconArrowUp, IconFolderOpen
} from '@tabler/icons-react';

// ─── Utils ─────────────────────────────────────────────

// Debounce hook for search input
function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
}

// ─── Types ─────────────────────────────────────────────

export interface FileItem {
    name: string;
    path: string;
    is_dir: boolean;
    size?: number;
    modified_at?: string;
    file_count?: number;  // Number of files in directory (only for directories)
}

export interface FileBrowserApi {
    list: (path: string, params?: {
        search?: string;
        file_type?: string;
        sort_by?: string;
        sort_order?: string;
    }) => Promise<FileItem[]>;
    read: (path: string) => Promise<{ content: string }>;
    write: (path: string, content: string) => Promise<any>;
    delete: (path: string) => Promise<any>;
    upload?: (file: File, path: string, onProgress?: (pct: number) => void) => Promise<any>;
    downloadUrl?: (path: string) => string;
    downloadFolderUrl?: (path: string) => string;
}

// File type mappings for filtering
const FILE_TYPE_MAP: Record<string, string[]> = {
    image: ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.tif'],
    pdf: ['.pdf'],
    word: ['.doc', '.docx'],
    excel: ['.xls', '.xlsx', '.xlsm'],
    powerpoint: ['.ppt', '.pptx'],
    text: ['.txt', '.md', '.markdown', '.rst'],
    code: ['.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.css', '.html', '.json', '.xml', '.yaml', '.yml', '.sh', '.bat'],
    video: ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'],
    audio: ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    archive: ['.zip', '.rar', '.7z', '.tar', '.gz'],
};

const FILE_TYPE_OPTIONS = [
    { value: 'all', label: '全部文件', icon: IconFolder },
    { value: 'image', label: '图片', icon: IconPhoto },
    { value: 'pdf', label: 'PDF', icon: IconFileDescription },
    { value: 'word', label: 'Word', icon: IconFileDescription },
    { value: 'excel', label: 'Excel', icon: IconTable },
    { value: 'powerpoint', label: 'PowerPoint', icon: IconPresentation },
    { value: 'text', label: '文本/Markdown', icon: IconFileText },
    { value: 'code', label: '代码', icon: IconCode },
    { value: 'video', label: '视频', icon: IconVideo },
    { value: 'audio', label: '音频', icon: IconMusic },
    { value: 'archive', label: '压缩包', icon: IconArchive },
];

const SORT_OPTIONS = [
    { value: 'name', label: '名称' },
    { value: 'size', label: '大小' },
    { value: 'modified_at', label: '修改时间' },
];

export interface FileBrowserProps {
    api: FileBrowserApi;
    rootPath?: string;
    features?: {
        upload?: boolean;
        newFile?: boolean;
        newFolder?: boolean;
        edit?: boolean;
        delete?: boolean;
        directoryNavigation?: boolean;
    };
    fileFilter?: string[];
    singleFile?: string;
    uploadAccept?: string;
    title?: string;
    readOnly?: boolean;
    onRefresh?: () => void;
}

// ─── File Icon Mapping ───────────────────────────────────

function getFileIcon(name: string, isDir: boolean): string {
    if (isDir) return '📁';

    const ext = name.toLowerCase().split('.').pop();
    const iconMap: Record<string, string> = {
        // Images
        'png': '🖼️', 'jpg': '🖼️', 'jpeg': '🖼️', 'gif': '🖼️', 'svg': '🖼️', 'webp': '🖼️', 'bmp': '🖼️', 'ico': '🖼️',
        // PDF
        'pdf': '📕',
        // Word
        'doc': '📘', 'docx': '📘',
        // Excel
        'xls': '📗', 'xlsx': '📗', 'xlsm': '📗',
        // PowerPoint
        'ppt': '📙', 'pptx': '📙',
        // Text/Code
        'txt': '📝', 'md': '📝', 'markdown': '📝', 'rst': '📝',
        'js': '📜', 'ts': '📜', 'py': '📜', 'java': '📜', 'c': '📜', 'cpp': '📜', 'h': '📜',
        'css': '📜', 'html': '📜', 'json': '📜', 'xml': '📜', 'yaml': '📜', 'yml': '📜', 'sh': '📜',
        // Video
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬', 'mkv': '🎬', 'flv': '🎬', 'wmv': '🎬', 'webm': '🎬',
        // Audio
        'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'aac': '🎵', 'ogg': '🎵', 'wma': '🎵', 'm4a': '🎵',
        // Archive
        'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
        // Default
        'default': '📄',
    };
    return iconMap[ext || ''] || iconMap['default'];
}

// Returns a Tabler Icon component based on file name and type
function getFileIconComponent(name: string, isDir: boolean, size: number = 20): React.ReactElement {
    if (isDir) {
        return <IconFolder size={size} color="#3B82F6" />;
    }

    const ext = name.toLowerCase().split('.').pop();

    // Icon type mapping with colors
    const iconTypeMap: Record<string, { icon: any; color: string }> = {
        // Images
        'png': { icon: IconPhoto, color: '#8B5CF6' },
        'jpg': { icon: IconPhoto, color: '#8B5CF6' },
        'jpeg': { icon: IconPhoto, color: '#8B5CF6' },
        'gif': { icon: IconPhoto, color: '#8B5CF6' },
        'svg': { icon: IconPhoto, color: '#8B5CF6' },
        'webp': { icon: IconPhoto, color: '#8B5CF6' },
        'bmp': { icon: IconPhoto, color: '#8B5CF6' },
        'ico': { icon: IconPhoto, color: '#8B5CF6' },

        // PDF
        'pdf': { icon: IconFile, color: '#EF4444' },

        // Word
        'doc': { icon: IconFileDescription, color: '#2563EB' },
        'docx': { icon: IconFileDescription, color: '#2563EB' },

        // Excel
        'xls': { icon: IconTable, color: '#10B981' },
        'xlsx': { icon: IconTable, color: '#10B981' },
        'xlsm': { icon: IconTable, color: '#10B981' },

        // PowerPoint
        'ppt': { icon: IconPresentation, color: '#F59E0B' },
        'pptx': { icon: IconPresentation, color: '#F59E0B' },

        // Text/Markdown
        'txt': { icon: IconFileText, color: '#6B7280' },
        'md': { icon: IconFileText, color: '#6B7280' },
        'markdown': { icon: IconFileText, color: '#6B7280' },
        'rst': { icon: IconFileText, color: '#6B7280' },

        // Code
        'js': { icon: IconCode, color: '#F59E0B' },
        'ts': { icon: IconCode, color: '#3178C6' },
        'py': { icon: IconCode, color: '#3776AB' },
        'java': { icon: IconCode, color: '#007396' },
        'c': { icon: IconCode, color: '#555555' },
        'cpp': { icon: IconCode, color: '#00599C' },
        'h': { icon: IconCode, color: '#555555' },
        'css': { icon: IconCode, color: '#264DE4' },
        'html': { icon: IconCode, color: '#E34F26' },
        'json': { icon: IconCode, color: '#292929' },
        'xml': { icon: IconCode, color: '#0060AC' },
        'yaml': { icon: IconCode, color: '#CB171E' },
        'yml': { icon: IconCode, color: '#CB171E' },
        'sh': { icon: IconCode, color: '#4EAA25' },
        'bat': { icon: IconCode, color: '#4EAA25' },

        // Video
        'mp4': { icon: IconVideo, color: '#EC4899' },
        'avi': { icon: IconVideo, color: '#EC4899' },
        'mov': { icon: IconVideo, color: '#EC4899' },
        'mkv': { icon: IconVideo, color: '#EC4899' },
        'flv': { icon: IconVideo, color: '#EC4899' },
        'wmv': { icon: IconVideo, color: '#EC4899' },
        'webm': { icon: IconVideo, color: '#EC4899' },
        'm4v': { icon: IconVideo, color: '#EC4899' },

        // Audio
        'mp3': { icon: IconMusic, color: '#8B5CF6' },
        'wav': { icon: IconMusic, color: '#8B5CF6' },
        'flac': { icon: IconMusic, color: '#8B5CF6' },
        'aac': { icon: IconMusic, color: '#8B5CF6' },
        'ogg': { icon: IconMusic, color: '#8B5CF6' },
        'wma': { icon: IconMusic, color: '#8B5CF6' },
        'm4a': { icon: IconMusic, color: '#8B5CF6' },

        // Archive
        'zip': { icon: IconArchive, color: '#6B7280' },
        'rar': { icon: IconArchive, color: '#6B7280' },
        '7z': { icon: IconArchive, color: '#6B7280' },
        'tar': { icon: IconArchive, color: '#6B7280' },
        'gz': { icon: IconArchive, color: '#6B7280' },
    };

    const iconConfig = iconTypeMap[ext || ''];
    if (iconConfig) {
        const IconComp = iconConfig.icon;
        return <IconComp size={size} color={iconConfig.color} />;
    }

    // Default file icon
    return <IconFile size={size} color="#9CA3AF" />;
}

function formatFileSize(bytes: number | null | undefined): string {
    if (bytes == null) return '-';
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(timestamp: string | undefined): string {
    if (!timestamp) return '-';
    const date = new Date(parseFloat(timestamp) * 1000);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
        return '昨天';
    } else if (diffDays < 7) {
        return `${diffDays}天前`;
    } else {
        return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    }
}

// ─── Text file detection ───────────────────────────────

const TEXT_EXTS = ['.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml', '.js', '.ts', '.py', '.html', '.css', '.sh', '.log', '.gitkeep', '.env'];

function isTextFile(name: string): boolean {
    const n = name.toLowerCase();
    if (TEXT_EXTS.some(ext => n.endsWith(ext))) return true;
    const base = n.split('/').pop() || '';
    return !base.includes('.') || base.startsWith('.');
}

const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico'];

function isImage(name: string): boolean {
    const n = name.toLowerCase();
    return IMAGE_EXTS.some(ext => n.endsWith(ext));
}

// ─── Component ─────────────────────────────────────────

export default function FileBrowser({
    api,
    rootPath = '',
    features = {},
    fileFilter,
    singleFile,
    uploadAccept = '.pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.json,.xml,.yaml,.yml,.js,.ts,.py,.html,.css,.sh,.log,.png,.jpg,.jpeg,.gif,.svg,.webp',
    title,
    readOnly = false,
    onRefresh,
}: FileBrowserProps) {
    const { t } = useTranslation();
    const {
        upload = false,
        newFile = false,
        newFolder = false,
        edit = !readOnly,
        delete: canDelete = !readOnly,
        directoryNavigation = false,
    } = features;

    // ─── State ─────────────────────────────────────────
    const [currentPath, setCurrentPath] = useState(rootPath);
    const [files, setFiles] = useState<FileItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [contentLoaded, setContentLoaded] = useState(false);
    const [viewing, setViewing] = useState<string | null>(singleFile || null);
    const [content, setContent] = useState('');
    const [editing, setEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<{ path: string; name: string } | null>(null);
    const [promptModal, setPromptModal] = useState<{ title: string; placeholder: string; action: string } | null>(null);
    const [promptValue, setPromptValue] = useState('');
    const [uploadProgress, setUploadProgress] = useState<{ fileName: string; percent: number } | null>(null);

    // Valid file type options
    const validFileTypes = new Set(['all', 'image', 'pdf', 'word', 'excel', 'powerpoint', 'text', 'code', 'video', 'audio', 'archive']);

    // Load preferences from localStorage on mount
    const getInitialSortState = () => {
        try {
            const saved = localStorage.getItem('file-browser-preferences');
            if (saved) {
                const prefs = JSON.parse(saved);
                // Validate file type filter - reset to 'all' if invalid (e.g., old 'document' type)
                const fileTypeFilter = validFileTypes.has(prefs.fileTypeFilter) ? prefs.fileTypeFilter : 'all';

                return {
                    sortBy: prefs.sortBy || 'name',
                    sortOrder: (prefs.sortOrder || 'asc') as 'asc' | 'desc',
                    fileTypeFilter,
                    viewMode: (prefs.viewMode || 'list') as 'list' | 'grid',
                    showHiddenFiles: prefs.showHiddenFiles || false
                };
            }
        } catch {
            // Ignore parse errors
        }
        return {
            sortBy: 'name',
            sortOrder: 'asc' as 'asc' | 'desc',
            fileTypeFilter: 'all',
            viewMode: 'list' as 'list' | 'grid',
            showHiddenFiles: false
        };
    };

    const initialSort = getInitialSortState();
    const [searchQuery, setSearchQuery] = useState('');
    const [fileTypeFilter, setFileTypeFilter] = useState(initialSort.fileTypeFilter);
    const [sortBy, setSortBy] = useState(initialSort.sortBy);
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(initialSort.sortOrder);

    // View mode: 'list' (table) or 'grid' (cards)
    const [viewMode, setViewMode] = useState<'list' | 'grid'>(initialSort.viewMode);

    // Show hidden files (starting with .)
    const [showHiddenFiles, setShowHiddenFiles] = useState(initialSort.showHiddenFiles);

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 50;

    // Debounced search query
    const debouncedSearchQuery = useDebounce(searchQuery, 300);

    // Save preferences to localStorage when changed
    useEffect(() => {
        try {
            const prefs = {
                sortBy,
                sortOrder,
                fileTypeFilter,
                viewMode,
                showHiddenFiles
            };
            localStorage.setItem('file-browser-preferences', JSON.stringify(prefs));
        } catch {
            // Ignore storage errors (e.g., private browsing)
        }
    }, [sortBy, sortOrder, fileTypeFilter, viewMode, showHiddenFiles]);

    // Multi-select state (no more "select mode", checkboxes always visible)
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());

    const textareaRef = useRef<HTMLTextAreaElement>(null);

 

    // Auto-resize textarea to match content height
    useEffect(() => {
        const el = textareaRef.current;
        if (el && editing) {
            el.style.height = 'auto';
            el.style.height = Math.max(200, el.scrollHeight) + 'px';
        }
    }, [editing, editContent]);

    // ─── Helpers ───────────────────────────────────────

    const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    }, []);

    // Multi-select helpers
    const toggleFileSelection = useCallback((filePath: string) => {
        setSelectedFiles(prev => {
            const newSet = new Set(prev);
            if (newSet.has(filePath)) {
                newSet.delete(filePath);
            } else {
                newSet.add(filePath);
            }
            return newSet;
        });
    }, []);

    const selectAllFiles = useCallback(() => {
        const allPaths = files.map(f => f.path || `${currentPath}/${f.name}`);
        setSelectedFiles(new Set(allPaths));
    }, [files, currentPath]);

    const clearSelection = useCallback(() => {
        setSelectedFiles(new Set());
    }, []);

    const invertSelection = useCallback(() => {
        const allPaths = new Set(files.map(f => f.path || `${currentPath}/${f.name}`));
        setSelectedFiles(prev => {
            const newSet = new Set<string>();
            for (const path of allPaths) {
                if (!prev.has(path)) {
                    newSet.add(path);
                }
            }
            return newSet;
        });
    }, [files, currentPath]);

 

    const reload = useCallback(async () => {
        if (singleFile) {
            // Single-file mode: just load the content
            try {
                const data = await api.read(singleFile);
                setContent(data.content || '');
            } catch {
                setContent('');
            }
            setContentLoaded(true);
            return;
        }
        setLoading(true);
        try {
            // Call API with filter and sort parameters
            const params: Record<string, string> = {};
            if (debouncedSearchQuery) params.search = debouncedSearchQuery;
            if (fileTypeFilter && fileTypeFilter !== 'all') params.file_type = fileTypeFilter;
            if (sortBy) params.sort_by = sortBy;
            if (sortOrder) params.sort_order = sortOrder;

            let data = await api.list(currentPath, Object.keys(params).length > 0 ? params : undefined);

            // Apply legacy fileFilter if provided
            if (fileFilter && fileFilter.length > 0) {
                data = data.filter(f => f.is_dir || fileFilter.some(ext => f.name.toLowerCase().endsWith(ext)));
            }

            // Filter hidden files if needed
            if (!showHiddenFiles) {
                data = data.filter(f => !f.name.startsWith('.'));
            }

            setFiles(data);
            // Reset to first page when files change
            setCurrentPage(1);
        } catch {
            setFiles([]);
        }
        setLoading(false);
    }, [api, currentPath, singleFile, fileFilter, debouncedSearchQuery, fileTypeFilter, sortBy, sortOrder, showHiddenFiles]);

    // ─── Drag-and-drop upload ─────────────────────
    const handleDroppedFiles = useCallback(async (files: File[]) => {
        if (!api.upload || files.length === 0) return;
        try {
            for (const file of files) {
                // For folder upload, extract directory path from webkitRelativePath
                // e.g., "subfolder/file.txt" -> targetPath = "workspace/subfolder"
                // e.g., "single.txt" -> targetPath = "workspace"
                const relativePath = (file as any).webkitRelativePath;
                const targetPath = relativePath && relativePath !== file.name
                    ? `${currentPath}/${relativePath.substring(0, relativePath.lastIndexOf('/'))}`
                    : currentPath;

                setUploadProgress({ fileName: relativePath || file.name, percent: 0 });
                await api.upload(file, targetPath, (pct) => {
                    setUploadProgress({ fileName: relativePath || file.name, percent: pct });
                });
            }
            setUploadProgress(null);
            reload();
            onRefresh?.();
            showToast(t('agent.upload.success', 'Upload successful'));
        } catch (err: any) {
            setUploadProgress(null);
            showToast(t('agent.upload.failed', 'Upload failed') + ': ' + (err.message || ''), 'error');
        }
    }, [api, currentPath, reload, onRefresh, showToast, t]);

    const { isDragging, dropZoneProps } = useDropZone({
        onDrop: handleDroppedFiles,
        disabled: !upload || !api.upload || !!singleFile || readOnly,
        accept: uploadAccept,
    });

    useEffect(() => { reload(); }, [reload]);

    // ─── Load file content when viewing ───────────────

    useEffect(() => {
        if (!viewing || singleFile) return;
        api.read(viewing).then(data => {
            setContent(data.content || '');
        }).catch(() => setContent(''));
    }, [viewing, api, singleFile]);

    // ─── Actions ──────────────────────────────────────

    const handleSave = async () => {
        const target = singleFile || viewing;
        if (!target) return;
        setSaving(true);
        try {
            await api.write(target, editContent);
            setContent(editContent);
            setEditing(false);
            showToast('Saved');
            onRefresh?.();
        } catch (err: any) {
            showToast('Save failed: ' + (err.message || ''), 'error');
        }
        setSaving(false);
    };

    const handleDelete = async () => {
        if (!deleteTarget) return;
        try {
            // Check if it's a batch delete (path contains comma)
            if (deleteTarget.path.includes(',')) {
                // Batch delete
                const pathsToDelete = deleteTarget.path.split(',');
                let successCount = 0;
                let failCount = 0;

                for (const path of pathsToDelete) {
                    try {
                        await api.delete(path.trim());
                        successCount++;
                    } catch {
                        failCount++;
                    }
                }

                setDeleteTarget(null);
                clearSelection();
                reload();
                onRefresh?.();

                if (failCount > 0) {
                    showToast(`已删除 ${successCount} 个文件，${failCount} 个失败`, 'error');
                } else {
                    showToast(`成功删除 ${successCount} 个文件`, 'success');
                }
            } else {
                // Single file delete
                await api.delete(deleteTarget.path);
                setDeleteTarget(null);
                if (viewing === deleteTarget.path) {
                    setViewing(null);
                    setEditing(false);
                }
                reload();
                onRefresh?.();
                showToast('已删除', 'success');
            }
        } catch (err: any) {
            showToast('删除失败: ' + (err.message || ''), 'error');
        }
    };

    const handleUpload = () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = uploadAccept;
        input.multiple = true;
        input.onchange = async () => {
            if (!input.files || input.files.length === 0) return;
            try {
                const fileList = Array.from(input.files);
                for (const file of fileList) {
                    setUploadProgress({ fileName: file.name, percent: 0 });
                    await api.upload!(file, currentPath, (pct) => {
                        setUploadProgress({ fileName: file.name, percent: pct });
                    });
                }
                setUploadProgress(null);
                reload();
                onRefresh?.();
                showToast('Upload successful');
            } catch (err: any) {
                setUploadProgress(null);
                showToast('Upload failed: ' + (err.message || ''), 'error');
            }
        };
        input.click();
    };

    const handlePromptConfirm = async () => {
        const value = promptValue.trim();
        if (!value || !promptModal) return;
        const action = promptModal.action;
        setPromptModal(null);
        setPromptValue('');
        try {
            if (action === 'newFolder') {
                const folderPath = currentPath ? `${currentPath}/${value}` : value;
                await api.write(`${folderPath}/.gitkeep`, '');
            } else if (action === 'newFile') {
                const filePath = currentPath ? `${currentPath}/${value}` : value;
                await api.write(filePath, '');
                setViewing(filePath);
                setEditContent('');
                setEditing(true);
            } else if (action === 'newSkill') {
                const template = `# ${value}\n\n## Description\n_Describe the purpose and triggers_\n\n## Input\n- Param1: Description\n\n## Steps\n1. Step one\n2. Step two\n\n## Output\n_Describe the output format_\n`;
                const filePath = currentPath ? `${currentPath}/${value}.md` : `${value}.md`;
                await api.write(filePath, template);
                setViewing(filePath);
                setEditContent(template);
                setEditing(true);
            }
            reload();
            onRefresh?.();
        } catch (err: any) {
            showToast('Failed: ' + (err.message || ''), 'error');
        }
    };

    // ─── Breadcrumbs ──────────────────────────────────

    const pathParts = currentPath ? currentPath.split('/').filter(Boolean) : [];

    const renderBreadcrumbs = () => {
        if (!directoryNavigation || singleFile) return null;
        return (
            <div style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <span
                    style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}
                    onClick={() => { setCurrentPath(rootPath); setViewing(null); setEditing(false); }}
                >
                    <IconFolder size={14} />
                    {rootPath || 'root'}
                </span>
                {pathParts.slice(rootPath ? rootPath.split('/').filter(Boolean).length : 0).map((part, i) => {
                    const upTo = pathParts.slice(0, (rootPath ? rootPath.split('/').filter(Boolean).length : 0) + i + 1).join('/');
                    return (
                        <span key={upTo}>
                            <span style={{ color: 'var(--text-tertiary)' }}> / </span>
                            <span
                                style={{ cursor: 'pointer', color: 'var(--accent-primary)' }}
                                onClick={() => { setCurrentPath(upTo); setViewing(null); setEditing(false); }}
                            >
                                {part}
                            </span>
                        </span>
                    );
                })}
            </div>
        );
    };

    // ─── Toast ─────────────────────────────────────────

    const renderToast = () => {
        if (!toast) return null;
        return (
            <div style={{
                position: 'fixed', top: '20px', right: '20px', zIndex: 20000, padding: '12px 20px', borderRadius: '8px',
                background: toast.type === 'success' ? 'rgba(34, 197, 94, 0.9)' : 'rgba(239, 68, 68, 0.9)',
                color: '#fff', fontSize: '14px', fontWeight: 500, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            }}>
                {toast.message}
            </div>
        );
    };

    // ─── Delete confirmation modal ────────────────────

    const renderDeleteModal = () => {
        if (!deleteTarget) return null;
        const isBatchDelete = deleteTarget.path.includes(',');
        const deleteMessage = isBatchDelete
            ? `确定要删除选中的 ${deleteTarget.name} 吗？此操作不可撤销。`
            : `确定要删除 "${deleteTarget.name}" 吗？此操作不可撤销。`;

        return (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000 }}
                onClick={(e) => { if (e.target === e.currentTarget) setDeleteTarget(null); }}>
                <div style={{ background: 'var(--bg-primary)', borderRadius: '12px', padding: '24px', width: '400px', border: '1px solid var(--border-subtle)', boxShadow: '0 20px 60px rgba(0,0,0,0.4)' }}>
                    <h4 style={{ marginBottom: '12px', fontSize: '16px', fontWeight: 600, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <IconAlertTriangle size={20} />
                        {isBatchDelete ? '批量删除确认' : '删除确认'}
                    </h4>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: '1.5' }}>
                        {deleteMessage}
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                        <button
                            className="btn btn-secondary"
                            onClick={() => setDeleteTarget(null)}
                            style={{ padding: '8px 16px', fontSize: '13px' }}
                        >
                            取消
                        </button>
                        <button
                            className="btn"
                            onClick={handleDelete}
                            style={{ padding: '8px 16px', fontSize: '13px', background: 'var(--error)', color: 'white' }}
                        >
                            确认删除
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    // ─── Prompt modal ─────────────────────────────────

    const renderPromptModal = () => {
        if (!promptModal) return null;
        return (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000 }}
                onClick={(e) => { if (e.target === e.currentTarget) { setPromptModal(null); setPromptValue(''); } }}>
                <div style={{ background: 'var(--bg-primary)', borderRadius: '12px', padding: '24px', width: '400px', border: '1px solid var(--border-subtle)', boxShadow: '0 20px 60px rgba(0,0,0,0.4)' }}>
                    <h4 style={{ marginBottom: '16px', fontSize: '15px' }}>{promptModal.title}</h4>
                    <input
                        className="form-input"
                        autoFocus
                        placeholder={promptModal.placeholder}
                        value={promptValue}
                        onChange={e => setPromptValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handlePromptConfirm(); }}
                        style={{ marginBottom: '16px' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                        <button className="btn btn-secondary" onClick={() => { setPromptModal(null); setPromptValue(''); }}>{t('common.cancel')}</button>
                        <button className="btn btn-primary" onClick={handlePromptConfirm} disabled={!promptValue.trim()}>OK</button>
                    </div>
                </div>
            </div>
        );
    };

    // ═══════════════════════════════════════════════════
    // SINGLE FILE MODE (Soul-style)
    // ═══════════════════════════════════════════════════
    if (singleFile) {
        return (
            <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    {title ? <h3>{title}</h3> : <div />}
                    {edit && (
                        !editing ? (
                            <button className="btn btn-secondary" onClick={() => { setEditContent(content); setEditing(true); }}>{t('agent.soul.editButton')}</button>
                        ) : (
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button className="btn btn-secondary" onClick={() => setEditing(false)}>{t('common.cancel')}</button>
                                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                                    {saving ? t('agent.soul.saving') : t('agent.soul.saveButton')}
                                </button>
                            </div>
                        )
                    )}
                </div>
                {editing ? (
                    <textarea ref={textareaRef} className="form-textarea" value={editContent} onChange={e => setEditContent(e.target.value)}
                        style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', lineHeight: '1.6', minHeight: '200px', resize: 'vertical', overflow: 'hidden' }} />
                ) : !contentLoaded ? (
                    <div style={{ padding: '20px', color: 'var(--text-tertiary)', textAlign: 'center' }}>{t('common.loading')}</div>
                ) : content ? (
                    singleFile?.endsWith('.md') ? (
                        <MarkdownRenderer content={content} style={{ padding: '4px 0' }} />
                    ) : (
                        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '13px', lineHeight: '1.6', margin: 0 }}>
                            {content}
                        </pre>
                    )
                ) : (
                    <div style={{ padding: '20px', color: 'var(--text-tertiary)', textAlign: 'center', fontSize: '13px' }}>
                        {t('common.noData', 'No content yet. Click Edit to add.')}
                    </div>
                )}
                {renderToast()}
            </div>
        );
    }

    // ═══════════════════════════════════════════════════
    // FILE VIEWER MODE (viewing a specific file)
    // ═══════════════════════════════════════════════════
    if (viewing) {
        const isText = isTextFile(viewing);
        return (
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px' }}
                        onClick={() => { setViewing(null); setEditing(false); }}>← {t('common.back')}</button>
                    <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--text-secondary)', flex: 1 }}>{viewing}</span>
                    {isText && edit && (
                        !editing ? (
                            <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                onClick={() => { setEditContent(content); setEditing(true); }}>
                                <IconFileText size={14} />
                                {t('agent.soul.editButton')}
                            </button>
                        ) : (
                            <div style={{ display: 'flex', gap: '6px' }}>
                                <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px' }}
                                    onClick={() => setEditing(false)}>{t('common.cancel')}</button>
                                <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '12px' }}
                                    disabled={saving} onClick={handleSave}>{saving ? 'Saving...' : t('common.save')}</button>
                            </div>
                        )
                    )}
                    {api.downloadUrl && (
                        <a href={api.downloadUrl(viewing)} download style={{ textDecoration: 'none' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <IconDownload size={14} />
                                {t('common.download', 'Download')}
                            </button>
                        </a>
                    )}
                    {canDelete && (
                        <button className="btn btn-danger" style={{ padding: '4px 10px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            onClick={() => setDeleteTarget({ path: viewing, name: viewing.split('/').pop() || viewing })}>
                            <IconTrash size={14} />
                        </button>
                    )}
                </div>
                <div className="card">
                    {isText ? (
                        editing ? (
                            <textarea ref={textareaRef} className="form-textarea" value={editContent} onChange={e => setEditContent(e.target.value)}
                                style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: '1.6', minHeight: '200px', resize: 'vertical', overflow: 'hidden' }} />
                        ) : viewing?.endsWith('.md') ? (
                            <MarkdownRenderer content={content || ''} style={{ padding: '4px' }} />
                        ) : (
                            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: '1.5', margin: 0 }}>
                                {content || t('common.noData', 'No content yet')}
                            </pre>
                        )
                    ) : isImage(viewing) ? (
                        <div style={{ textAlign: 'center', padding: '20px', background: 'var(--bg-tertiary)', borderRadius: '8px' }}>
                            {api.downloadUrl ? (
                                <img 
                                    src={api.downloadUrl(viewing)} 
                                    alt={viewing.split('/').pop()} 
                                    style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain', borderRadius: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} 
                                />
                            ) : (
                                <div style={{ padding: '20px', color: 'var(--text-tertiary)' }}>Cannot preview image without download URL</div>
                            )}
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                            <div style={{ fontSize: '48px', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
                                <IconFile size={48} color="var(--text-tertiary)" />
                            </div>
                            <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>{viewing.split('/').pop()}</div>
                            <div style={{ fontSize: '12px', marginBottom: '16px' }}>Binary file — cannot preview</div>
                            {api.downloadUrl && (
                                <a href={api.downloadUrl(viewing)} download style={{ textDecoration: 'none' }}>
                                    <button className="btn btn-primary" style={{ fontSize: '13px', padding: '8px 20px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <IconDownload size={16} />
                                        {t('common.download', 'Download')}
                                    </button>
                                </a>
                            )}
                        </div>
                    )}
                </div>
                {renderDeleteModal()}
                {renderToast()}
            </div>
        );
    }

    // ═══════════════════════════════════════════════════
    // FILE LIST / BROWSER MODE
    // ═══════════════════════════════════════════════════
    return (
        <div className="drop-zone-wrapper" {...dropZoneProps}>
            {/* Drop overlay */}
            {isDragging && (
                <div className="drop-zone-overlay">
                    <div className="drop-zone-overlay__icon">
                        <IconUpload size={48} color="var(--accent-primary)" />
                    </div>
                    <div className="drop-zone-overlay__text">支持文件和文件夹拖拽上传</div>
                </div>
            )}

            {/* Toolbar */}
            <div className="file-browser-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
                {/* Left side: Title and breadcrumbs */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, minWidth: 0 }}>
                    {title && <h3 style={{ margin: 0 }}>{title}</h3>}
                    {renderBreadcrumbs()}
                </div>

                {/* Right side: Actions and filters */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    {/* Action buttons */}
                    <div className="file-browser-toolbar-actions" style={{ display: 'flex', gap: '6px' }}>
                        {upload && api.upload && (
                            <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }} onClick={handleUpload}>
                                <IconUpload size={16} />
                                <span>上传文件</span>
                            </button>
                        )}
                        {newFolder && (
                            <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                onClick={() => setPromptModal({ title: '新建文件夹', placeholder: '文件夹名称', action: 'newFolder' })}>
                                <IconFolderPlus size={16} />
                                <span>新建文件夹</span>
                            </button>
                        )}
                        {newFile && !fileFilter && (
                            <button className="btn btn-primary" style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                onClick={() => setPromptModal({ title: '新建文件', placeholder: '文件名.md', action: 'newFile' })}>
                                <IconPlus size={16} />
                                <span>新建文件</span>
                            </button>
                        )}

                        {/* Batch actions (always visible, enabled when files are selected) */}
                        {selectedFiles.size > 0 && (
                            <>
                                <button
                                    className="btn btn-secondary"
                                    style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    onClick={selectAllFiles}
                                    title="全选"
                                >
                                    <IconCheck size={16} />
                                    <span>全选</span>
                                </button>
                                <button
                                    className="btn btn-secondary"
                                    style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    onClick={invertSelection}
                                    title="反选"
                                >
                                    <IconRefresh size={16} />
                                    <span>反选</span>
                                </button>
                                <button
                                    className="btn btn-secondary"
                                    style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    onClick={clearSelection}
                                    title="取消选择"
                                >
                                    <IconX size={16} />
                                    <span>清除</span>
                                </button>
                                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '6px 10px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', height: '34px', display: 'flex', alignItems: 'center' }}>
                                    已选 {selectedFiles.size} 项
                                </span>
                                <button
                                    className="btn btn-primary"
                                    style={{ fontSize: '12px', padding: '6px 12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    onClick={async () => {
                                        // Batch download - improved version
                                        let successCount = 0;
                                        let failCount = 0;

                                        for (const filePath of Array.from(selectedFiles)) {
                                            try {
                                                // Check if it's a directory or file
                                                const file = files.find(f => (f.path || `${currentPath}/${f.name}`) === filePath);

                                                if (file?.is_dir && api.downloadFolderUrl) {
                                                    // Download folder as ZIP
                                                    const url = api.downloadFolderUrl(filePath);
                                                    if (url) {
                                                        const link = document.createElement('a');
                                                        link.href = url;
                                                        link.download = filePath.split('/').pop() || 'download';
                                                        document.body.appendChild(link);
                                                        link.click();
                                                        document.body.removeChild(link);
                                                        successCount++;
                                                    } else {
                                                        failCount++;
                                                    }
                                                } else if (!file?.is_dir && api.downloadUrl) {
                                                    // Download single file
                                                    const url = api.downloadUrl(filePath);
                                                    if (url) {
                                                        // Use fetch to download with proper headers
                                                        const response = await fetch(url);
                                                        if (response.ok) {
                                                            const blob = await response.blob();
                                                            const downloadUrl = window.URL.createObjectURL(blob);
                                                            const link = document.createElement('a');
                                                            link.href = downloadUrl;
                                                            link.download = filePath.split('/').pop() || 'download';
                                                            document.body.appendChild(link);
                                                            link.click();
                                                            document.body.removeChild(link);
                                                            window.URL.revokeObjectURL(downloadUrl);
                                                            successCount++;
                                                        } else {
                                                            failCount++;
                                                        }
                                                    } else {
                                                        failCount++;
                                                    }
                                                } else {
                                                    failCount++;
                                                }
                                            } catch {
                                                failCount++;
                                            }
                                            // Add delay between downloads
                                            await new Promise(resolve => setTimeout(resolve, 300));
                                        }
                                        showToast(`已下载 ${successCount} 个文件${failCount > 0 ? `，${failCount} 个失败` : ''}`, failCount > 0 ? 'error' : 'success');
                                        clearSelection();
                                    }}
                                    title={`批量下载 ${selectedFiles.size} 个文件`}
                                >
                                    <IconDownload size={16} />
                                    <span>批量下载</span>
                                </button>
                                {canDelete && (
                                    <button
                                        className="btn"
                                        style={{ fontSize: '12px', padding: '6px 12px', height: '34px', background: 'var(--error)', color: 'white', display: 'flex', alignItems: 'center', gap: '4px' }}
                                        onClick={() => {
                                            // Batch delete - show confirmation
                                            const fileCount = selectedFiles.size;
                                            setDeleteTarget({
                                                path: Array.from(selectedFiles).join(','),
                                                name: `${fileCount} 个文件`
                                            });
                                        }}
                                        title={`批量删除 ${selectedFiles.size} 个文件`}
                                    >
                                        <IconTrash size={16} />
                                        <span>批量删除</span>
                                    </button>
                                )}
                            </>
                        )}
                    </div>

                    {/* Filter and sort controls */}
                    <div className="file-browser-toolbar-controls" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {/* Search input */}
                        <div className="file-browser-toolbar-search-wrapper" style={{ position: 'relative' }}>
                            <div style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)', pointerEvents: 'none', display: 'flex', alignItems: 'center' }}>
                                <IconSearch size={16} />
                            </div>
                            <input
                                type="text"
                                placeholder="搜索文件..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="form-input"
                                style={{ paddingLeft: '32px', width: '160px', fontSize: '13px', height: '34px' }}
                            />
                        </div>

                        {/* File type filter */}
                        <select
                            value={fileTypeFilter}
                            onChange={(e) => setFileTypeFilter(e.target.value)}
                            className="form-select"
                            style={{ height: '34px', minWidth: '120px', fontSize: '13px' }}
                        >
                            {FILE_TYPE_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>

                        {/* Sort buttons */}
                        <div className="file-browser-toolbar-sort-group" style={{ display: 'flex', gap: '2px', height: '34px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: '2px', border: '1px solid var(--border-subtle)' }}>
                            {SORT_OPTIONS.map(opt => (
                                <button
                                    key={opt.value}
                                    className={`file-browser-toolbar-sort-btn ${sortBy === opt.value ? 'active' : ''}`}
                                    onClick={() => {
                                        if (sortBy === opt.value) {
                                            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                                        } else {
                                            setSortBy(opt.value);
                                            setSortOrder('asc');
                                        }
                                    }}
                                    style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '4px',
                                        padding: '0 10px',
                                        height: '100%',
                                        border: 'none',
                                        borderRadius: 'var(--radius-sm)',
                                        background: sortBy === opt.value ? 'var(--bg-elevated)' : 'transparent',
                                        color: sortBy === opt.value ? 'var(--text-primary)' : 'var(--text-tertiary)',
                                        fontSize: '12px',
                                        cursor: 'pointer',
                                        transition: 'all 120ms ease',
                                        whiteSpace: 'nowrap',
                                        boxShadow: sortBy === opt.value ? 'var(--shadow-sm)' : 'none'
                                    }}
                                    title={`按${opt.label}排序`}
                                >
                                    {opt.label}
                                    {sortBy === opt.value && (
                                        <span style={{ fontSize: '10px', transform: sortOrder === 'desc' ? 'rotate(180deg)' : 'none', transition: 'transform 180ms ease-in-out', display: 'flex', alignItems: 'center' }}>
                                            {sortOrder === 'desc' ? <IconSortDescending size={12} /> : <IconSortAscending size={12} />}
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* View mode toggle */}
                        <div style={{ display: 'flex', gap: '2px', height: '34px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: '2px', border: '1px solid var(--border-subtle)' }}>
                            <button
                                className={viewMode === 'list' ? 'active' : ''}
                                onClick={() => setViewMode('list')}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '4px',
                                    padding: '0 10px',
                                    height: '100%',
                                    border: 'none',
                                    borderRadius: 'var(--radius-sm)',
                                    background: viewMode === 'list' ? 'var(--bg-elevated)' : 'transparent',
                                    color: viewMode === 'list' ? 'var(--text-primary)' : 'var(--text-tertiary)',
                                    fontSize: '12px',
                                    cursor: 'pointer',
                                    transition: 'all 120ms ease',
                                    boxShadow: viewMode === 'list' ? 'var(--shadow-sm)' : 'none'
                                }}
                                title="列表视图"
                            >
                                <IconList size={16} />
                                <span>列表</span>
                            </button>
                            <button
                                className={viewMode === 'grid' ? 'active' : ''}
                                onClick={() => setViewMode('grid')}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '4px',
                                    padding: '0 10px',
                                    height: '100%',
                                    border: 'none',
                                    borderRadius: 'var(--radius-sm)',
                                    background: viewMode === 'grid' ? 'var(--bg-elevated)' : 'transparent',
                                    color: viewMode === 'grid' ? 'var(--text-primary)' : 'var(--text-tertiary)',
                                    fontSize: '12px',
                                    cursor: 'pointer',
                                    transition: 'all 120ms ease',
                                    boxShadow: viewMode === 'grid' ? 'var(--shadow-sm)' : 'none'
                                }}
                                title="卡片视图"
                            >
                                <IconGridDots size={16} />
                                <span>卡片</span>
                            </button>
                        </div>

                        {/* Show hidden files toggle */}
                        <button
                            className={`btn ${showHiddenFiles ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setShowHiddenFiles(!showHiddenFiles)}
                            style={{ fontSize: '12px', height: '34px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            title={showHiddenFiles ? '隐藏以.开头的文件' : '显示以.开头的文件'}
                        >
                            {showHiddenFiles ? <IconEyeOff size={16} /> : <IconEye size={16} />}
                            <span>{showHiddenFiles ? '隐藏' : '显示'}</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* File list */}
            {loading ? (
                <div style={{ padding: '40px', color: 'var(--text-tertiary)', textAlign: 'center' }}>{t('common.loading')}</div>
            ) : uploadProgress ? (
                <div className="card" style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <IconArrowUp size={16} color="var(--accent-primary)" />
                        <span style={{ fontSize: '13px', fontWeight: 500, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{uploadProgress.fileName}</span>
                        <span style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>{uploadProgress.percent}%</span>
                    </div>
                    <div style={{ height: '4px', borderRadius: '2px', background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: '2px', background: 'var(--accent-primary)', width: `${uploadProgress.percent}%`, transition: 'width 0.15s ease' }} />
                    </div>
                </div>
            ) : files.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                    <div style={{ fontSize: '48px', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
                        <IconFolderOpen size={48} color="var(--text-tertiary)" />
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>暂无文件</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        {upload && api.upload
                            ? '拖拽文件到此处或点击上传按钮'
                            : '此文件夹为空'}
                    </div>
                </div>
            ) : (
                <>
                    {/* File count and pagination info */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        <span>共 {files.length} 项</span>
                        {files.length > pageSize && (
                            <span>第 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, files.length)} 项</span>
                        )}
                    </div>

                    {/* Back button for subdirectories */}
                    {directoryNavigation && currentPath !== rootPath && (
                        <div
                            className="card"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '10px 12px',
                                marginBottom: '8px',
                                cursor: 'pointer',
                                background: 'var(--bg-tertiary)',
                                border: '1px dashed var(--border-subtle)'
                            }}
                            onClick={() => {
                                const parts = currentPath.split('/').filter(Boolean);
                                parts.pop();
                                setCurrentPath(parts.join('/') || rootPath);
                                setViewing(null);
                                setEditing(false);
                            }}
                        >
                            <IconChevronLeft size={16} color="var(--text-secondary)" />
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>返回上级目录</span>
                        </div>
                    )}

                    {/* LIST VIEW */}
                    {viewMode === 'list' && (
                        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                            {/* Table header */}
                            <div style={{ display: 'grid', gridTemplateColumns: '40px 2fr 100px 140px 120px 1fr', gap: '12px', padding: '10px 12px', background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-subtle)', fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                                <div></div>
                                <div>名称</div>
                                <div>大小</div>
                                <div>修改时间</div>
                                <div>类型</div>
                                <div style={{ textAlign: 'right' }}>操作</div>
                            </div>

                            {/* Table rows */}
                            {files.map((f) => {
                                const filePath = f.path || `${currentPath}/${f.name}`;
                                const isSelected = selectedFiles.has(filePath);

                                return (
                                    <div
                                        key={f.name}
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: '40px 2fr 100px 140px 120px 1fr',
                                            gap: '12px',
                                            padding: '10px 12px',
                                            borderBottom: '1px solid var(--border-subtle)',
                                            cursor: 'pointer',
                                            background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                                            transition: 'background 0.15s ease',
                                        }}
                                        onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
                                        onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                                        onClick={(e) => {
                                            const target = e.target as HTMLElement;
                                            const isInteractive = target.tagName === 'A' || target.tagName === 'BUTTON' ||
                                                                   target.classList.contains('file-checkbox');

                                            if (isInteractive) return;

                                            if (selectedFiles.size > 0) {
                                                toggleFileSelection(filePath);
                                            } else if (f.is_dir && directoryNavigation) {
                                                setCurrentPath(filePath);
                                                setViewing(null);
                                                setEditing(false);
                                            } else if (!f.is_dir) {
                                                setViewing(filePath);
                                                setEditing(false);
                                            }
                                        }}
                                    >
                                        {/* Checkbox */}
                                        <div style={{ display: 'flex', alignItems: 'center' }}>
                                            <span
                                                className="file-checkbox"
                                                onClick={(e) => { e.stopPropagation(); toggleFileSelection(filePath); }}
                                                style={{
                                                    fontSize: '16px',
                                                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                                                    cursor: 'pointer',
                                                    userSelect: 'none',
                                                    display: 'flex',
                                                    alignItems: 'center'
                                                }}
                                            >
                                                {isSelected ? <IconCheckbox size={18} color="var(--accent-primary)" /> : <IconSquare size={18} color="var(--text-tertiary)" />}
                                            </span>
                                        </div>

                                        {/* Name */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                                            <span style={{ fontSize: '20px', flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                                                {getFileIconComponent(f.name, f.is_dir, 20)}
                                            </span>
                                            <span style={{
                                                fontWeight: 500,
                                                fontSize: '13px',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap'
                                            }}>
                                                {fileFilter?.includes('.md') ? f.name.replace('.md', '') : f.name}
                                            </span>
                                        </div>

                                        {/* Size */}
                                        <div style={{ display: 'flex', alignItems: 'center', fontSize: '12px', color: 'var(--text-secondary)', gap: '4px' }}>
                                            {f.is_dir ? (
                                                <>
                                                    {f.file_count !== undefined && f.file_count > 0 ? (
                                                        <span>{f.file_count} 项</span>
                                                    ) : (
                                                        <span>—</span>
                                                    )}
                                                    {f.size !== undefined && f.size > 0 && (
                                                        <span style={{ color: 'var(--text-tertiary)' }}>({formatFileSize(f.size)})</span>
                                                    )}
                                                </>
                                            ) : (
                                                <span>{formatFileSize(f.size)}</span>
                                            )}
                                        </div>

                                        {/* Modified time */}
                                        <div style={{ display: 'flex', alignItems: 'center', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                            {formatDate(f.modified_at)}
                                        </div>

                                        {/* Type */}
                                        <div style={{ display: 'flex', alignItems: 'center', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                                            {f.is_dir ? '文件夹' : (f.name.split('.').pop() || '文件').toUpperCase()}
                                        </div>

                                        {/* Actions */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                                            {f.is_dir && api.downloadFolderUrl && (
                                                <a
                                                    href={api.downloadFolderUrl(filePath)}
                                                    download
                                                    onClick={(e) => e.stopPropagation()}
                                                    title="下载文件夹"
                                                    style={{
                                                        padding: '6px 10px',
                                                        fontSize: '12px',
                                                        color: 'var(--accent-primary)',
                                                        textDecoration: 'none',
                                                        borderRadius: '6px',
                                                        background: 'var(--bg-tertiary)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        border: '1px solid var(--border-subtle)',
                                                        transition: 'all 0.15s ease'
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-subtle)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconDownload size={14} />
                                                    <span>下载</span>
                                                </a>
                                            )}
                                            {!f.is_dir && api.downloadUrl && (
                                                <a
                                                    href={api.downloadUrl(filePath)}
                                                    download
                                                    onClick={(e) => e.stopPropagation()}
                                                    title="下载文件"
                                                    style={{
                                                        padding: '6px 10px',
                                                        fontSize: '12px',
                                                        color: 'var(--accent-primary)',
                                                        textDecoration: 'none',
                                                        borderRadius: '6px',
                                                        background: 'var(--bg-tertiary)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        border: '1px solid var(--border-subtle)',
                                                        transition: 'all 0.15s ease'
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-subtle)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconDownload size={14} />
                                                    <span>下载</span>
                                                </a>
                                            )}
                                            {canDelete && (
                                                <button
                                                    className="btn btn-ghost"
                                                    onClick={(e) => { e.stopPropagation(); setDeleteTarget({ path: filePath, name: f.name }); }}
                                                    style={{
                                                        padding: '6px 10px',
                                                        fontSize: '12px',
                                                        color: 'var(--error)',
                                                        background: 'var(--bg-tertiary)',
                                                        borderRadius: '6px',
                                                        border: '1px solid var(--border-subtle)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        transition: 'all 0.15s ease'
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.borderColor = 'var(--error)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconTrash size={14} />
                                                    <span>删除</span>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* GRID/CARD VIEW */}
                    {viewMode === 'grid' && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px' }}>
                            {files.map((f) => {
                                const filePath = f.path || `${currentPath}/${f.name}`;
                                const isSelected = selectedFiles.has(filePath);

                                return (
                                    <div
                                        key={f.name}
                                        className="card"
                                        style={{
                                            padding: '16px',
                                            cursor: 'pointer',
                                            background: isSelected ? 'var(--accent-subtle)' : 'var(--bg-elevated)',
                                            border: isSelected ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                            borderRadius: '12px',
                                            transition: 'all 0.2s ease',
                                            position: 'relative',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'center'
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isSelected) {
                                                e.currentTarget.style.transform = 'translateY(-4px)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isSelected) {
                                                e.currentTarget.style.transform = 'translateY(0)';
                                                e.currentTarget.style.boxShadow = 'none';
                                            }
                                        }}
                                        onClick={(e) => {
                                            const target = e.target as HTMLElement;
                                            const isInteractive = target.tagName === 'A' || target.tagName === 'BUTTON' ||
                                                                   target.classList.contains('file-checkbox') ||
                                                                   target.parentElement?.classList.contains('file-checkbox');

                                            if (isInteractive) return;

                                            if (selectedFiles.size > 0) {
                                                toggleFileSelection(filePath);
                                            } else if (f.is_dir && directoryNavigation) {
                                                setCurrentPath(filePath);
                                                setViewing(null);
                                                setEditing(false);
                                            } else if (!f.is_dir) {
                                                setViewing(filePath);
                                                setEditing(false);
                                            }
                                        }}
                                    >
                                        {/* Checkbox */}
                                        <div style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 1 }}>
                                            <span
                                                className="file-checkbox"
                                                onClick={(e) => { e.stopPropagation(); toggleFileSelection(filePath); }}
                                                style={{
                                                    fontSize: '16px',
                                                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                                                    cursor: 'pointer',
                                                    userSelect: 'none',
                                                    background: 'rgba(255,255,255,0.95)',
                                                    borderRadius: '6px',
                                                    padding: '4px',
                                                    boxShadow: isSelected ? '0 0 0 1px var(--accent-primary)' : '0 1px 3px rgba(0,0,0,0.1)',
                                                    display: 'flex',
                                                    alignItems: 'center'
                                                }}
                                            >
                                                {isSelected ? <IconCheckbox size={18} color="var(--accent-primary)" /> : <IconSquare size={18} color="var(--text-tertiary)" />}
                                            </span>
                                        </div>

                                        {/* File icon */}
                                        <div style={{ marginBottom: '12px', marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            {getFileIconComponent(f.name, f.is_dir, 48)}
                                        </div>

                                        {/* File name */}
                                        <div style={{
                                            fontWeight: 500,
                                            fontSize: '14px',
                                            textAlign: 'center',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                            width: '100%',
                                            marginBottom: '4px'
                                        }}>
                                            {fileFilter?.includes('.md') ? f.name.replace('.md', '') : f.name}
                                        </div>

                                        {/* File info */}
                                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center', marginBottom: '12px' }}>
                                            {f.is_dir ? (
                                                <>
                                                    {f.file_count !== undefined && f.file_count > 0 ? (
                                                        <span>{f.file_count} 项</span>
                                                    ) : (
                                                        <span>空文件夹</span>
                                                    )}
                                                    {f.size !== undefined && f.size > 0 && (
                                                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                                                            {formatFileSize(f.size)}
                                                        </div>
                                                    )}
                                                </>
                                            ) : (
                                                <span>{formatFileSize(f.size)}</span>
                                            )}
                                        </div>

                                        {/* Actions */}
                                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', width: '100%' }}>
                                            {f.is_dir && api.downloadFolderUrl && (
                                                <a
                                                    href={api.downloadFolderUrl(filePath)}
                                                    download
                                                    onClick={(e) => e.stopPropagation()}
                                                    title="下载文件夹"
                                                    style={{
                                                        padding: '8px 12px',
                                                        fontSize: '12px',
                                                        color: 'var(--accent-primary)',
                                                        textDecoration: 'none',
                                                        borderRadius: '8px',
                                                        background: 'var(--bg-tertiary)',
                                                        border: '1px solid var(--border-subtle)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        flex: 1,
                                                        transition: 'all 0.15s ease',
                                                        fontWeight: 500
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-subtle)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconDownload size={16} />
                                                </a>
                                            )}
                                            {!f.is_dir && api.downloadUrl && (
                                                <a
                                                    href={api.downloadUrl(filePath)}
                                                    download
                                                    onClick={(e) => e.stopPropagation()}
                                                    title="下载文件"
                                                    style={{
                                                        padding: '8px 12px',
                                                        fontSize: '12px',
                                                        color: 'var(--accent-primary)',
                                                        textDecoration: 'none',
                                                        borderRadius: '8px',
                                                        background: 'var(--bg-tertiary)',
                                                        border: '1px solid var(--border-subtle)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        flex: 1,
                                                        transition: 'all 0.15s ease',
                                                        fontWeight: 500
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-subtle)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconDownload size={16} />
                                                </a>
                                            )}
                                            {canDelete && (
                                                <button
                                                    className="btn btn-ghost"
                                                    onClick={(e) => { e.stopPropagation(); setDeleteTarget({ path: filePath, name: f.name }); }}
                                                    style={{
                                                        padding: '8px 12px',
                                                        fontSize: '12px',
                                                        color: 'var(--error)',
                                                        borderRadius: '8px',
                                                        background: 'var(--bg-tertiary)',
                                                        border: '1px solid var(--border-subtle)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        transition: 'all 0.15s ease',
                                                        fontWeight: 500
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.borderColor = 'var(--error)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
                                                >
                                                    <IconTrash size={16} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* Pagination */}
                    {files.length > pageSize && (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '16px', padding: '12px' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                                style={{ fontSize: '12px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                                <IconChevronLeft size={16} />
                                上一页
                            </button>
                            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                第 {currentPage} / {Math.ceil(files.length / pageSize)} 页
                            </span>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setCurrentPage(Math.min(Math.ceil(files.length / pageSize), currentPage + 1))}
                                disabled={currentPage >= Math.ceil(files.length / pageSize)}
                                style={{ fontSize: '12px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                                下一页
                                <IconChevronLeft size={16} style={{ transform: 'rotate(180deg)' }} />
                            </button>
                        </div>
                    )}
                </>
            )}

            {renderDeleteModal()}
            {renderPromptModal()}
            {renderToast()}
        </div>
    );
}
