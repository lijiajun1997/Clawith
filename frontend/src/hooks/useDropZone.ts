/**
 * useDropZone — reusable drag-and-drop file upload hook.
 *
 * Uses a counter-based approach to handle nested elements correctly:
 * dragenter/dragleave fire on every child element, so a simple boolean
 * would flicker. The counter increments on dragenter and decrements on
 * dragleave; isDragging is true when counter > 0.
 *
 * Enhanced to support folder drag-and-drop using webkitGetAsEntry API.
 */
import { useState, useRef, useCallback, type DragEvent } from 'react';

export interface UseDropZoneOptions {
    /** Callback when files are dropped. Receives the filtered file list. */
    onDrop: (files: File[]) => void;
    /** When true, the drop zone is inactive (no visual feedback, drops ignored). */
    disabled?: boolean;
    /**
     * Optional comma-separated list of accepted MIME types or extensions.
     * e.g. ".json" or "image/*,.pdf"
     * Files not matching are silently filtered out.
     */
    accept?: string;
}

export interface UseDropZoneReturn {
    /** True when a drag-with-files is hovering over the zone. */
    isDragging: boolean;
    /** Spread these onto the container element acting as the drop zone. */
    dropZoneProps: {
        onDragEnter: (e: DragEvent) => void;
        onDragOver: (e: DragEvent) => void;
        onDragLeave: (e: DragEvent) => void;
        onDrop: (e: DragEvent) => void;
    };
}

// ─── Browser Compatibility Detection ─────────────────────

/** Check if browser supports folder upload via webkitGetAsEntry */
export function supportsDirectoryUpload(): boolean {
    return 'webkitGetAsEntry' in DataTransfer.prototype ||
           'getAsEntry' in DataTransfer.prototype;
}

// ─── Folder Reading Utilities ─────────────────────────────

/** Recursively read a directory entry and return all files with relative paths */
async function readDirectoryEntry(
    directoryEntry: any,
    path = ''
): Promise<File[]> {
    const files: File[] = [];
    const reader = directoryEntry.createReader();

    // readEntries() may only return up to 100 entries at a time
    const readEntries = async (): Promise<File[]> => {
        const entries = await new Promise<any[]>((resolve) => {
            reader.readEntries(resolve);
        });

        for (const entry of entries) {
            if (entry.isFile) {
                const file = await new Promise<File>((resolve) => {
                    entry.file((f: File) => {
                        // Add relative path property for folder structure
                        Object.defineProperty(f, 'webkitRelativePath', {
                            value: `${path}${entry.name}`,
                            writable: false,
                            enumerable: true,
                            configurable: false,
                        });
                        resolve(f);
                    });
                });
                files.push(file);
            } else if (entry.isDirectory) {
                const subFiles = await readDirectoryEntry(
                    entry,
                    `${path}${entry.name}/`
                );
                files.push(...subFiles);
            }
        }

        // If we got 100 entries, there might be more to read
        if (entries.length === 100) {
            const moreFiles = await readEntries();
            files.push(...moreFiles);
        }

        return files;
    };

    return readEntries();
}

/** Extract files from DataTransfer with folder support */
async function extractFilesWithFolderSupport(
    dataTransfer: DataTransfer,
    enableFolderUpload: boolean
): Promise<File[]> {
    // Check if folder upload is supported and enabled
    if (enableFolderUpload && supportsDirectoryUpload()) {
        const items = dataTransfer.items;
        if (!items || items.length === 0) {
            // Fallback to standard file access
            return Array.from(dataTransfer.files || []);
        }

        const allFiles: File[] = [];

        for (let i = 0; i < items.length; i++) {
            const item = items[i].webkitGetAsEntry?.() || (items[i] as any).getAsEntry?.();

            if (item) {
                if (item.isDirectory) {
                    // Recursively read directory
                    const dirFiles = await readDirectoryEntry(item);
                    allFiles.push(...dirFiles);
                } else if (item.isFile) {
                    // Single file
                    const file = await new Promise<File>((resolve) => {
                        item.file((f: File) => resolve(f));
                    });
                    allFiles.push(file);
                }
            }
        }

        return allFiles.length > 0 ? allFiles : Array.from(dataTransfer.files || []);
    }

    // Fallback: standard file access
    return Array.from(dataTransfer.files || []);
}

// ─── Original Utilities ───────────────────────────────────

/** Check whether a drag event contains files (vs plain text / URLs). */
function hasFiles(e: DragEvent): boolean {
    if (e.dataTransfer?.types) {
        for (const t of Array.from(e.dataTransfer.types)) {
            if (t === 'Files') return true;
        }
    }
    return false;
}

/** Filter a FileList by an accept string (same format as <input accept>). */
function filterFiles(files: File[], accept?: string): File[] {
    if (!accept) return files;

    const tokens = accept.split(',').map(t => t.trim().toLowerCase());

    return files.filter(file => {
        const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
        const mime = file.type.toLowerCase();

        return tokens.some(token => {
            if (token.startsWith('.')) return ext === token;
            if (token.endsWith('/*')) return mime.startsWith(token.slice(0, -1));
            return mime === token;
        });
    });
}

export function useDropZone({
    onDrop,
    disabled = false,
    accept
}: UseDropZoneOptions): UseDropZoneReturn {
    const [isDragging, setIsDragging] = useState(false);
    const counterRef = useRef(0);

    const handleDragEnter = useCallback((e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (disabled || !hasFiles(e)) return;
        counterRef.current += 1;
        if (counterRef.current === 1) setIsDragging(true);
    }, [disabled]);

    const handleDragOver = useCallback((e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!disabled && hasFiles(e)) {
            e.dataTransfer.dropEffect = 'copy';
        }
    }, [disabled]);

    const handleDragLeave = useCallback((e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (disabled) return;
        counterRef.current -= 1;
        if (counterRef.current <= 0) {
            counterRef.current = 0;
            setIsDragging(false);
        }
    }, [disabled]);

    const handleDrop = useCallback(async (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        counterRef.current = 0;
        setIsDragging(false);
        if (disabled) return;

        const dataTransfer = e.dataTransfer;
        if (!dataTransfer) return;

        // Extract files with folder support (always enabled)
        const rawFiles = await extractFilesWithFolderSupport(dataTransfer, true);

        if (rawFiles.length === 0) return;

        // Filter by accept string
        const filtered = filterFiles(rawFiles, accept);
        if (filtered.length > 0) {
            onDrop(filtered);
        }
    }, [disabled, accept, onDrop]);

    return {
        isDragging,
        dropZoneProps: {
            onDragEnter: handleDragEnter,
            onDragOver: handleDragOver,
            onDragLeave: handleDragLeave,
            onDrop: handleDrop,
        },
    };
}
