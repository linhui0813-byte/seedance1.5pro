"use client";

import { useState, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { createJob } from "@/lib/api";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  horizontalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface FileItem {
  id: string;
  file: File;
}

function SortableImageItem({
  item,
  index,
  onRemove,
}: {
  item: FileItem;
  index: number;
  onRemove: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    cursor: "grab" as const,
  };

  const previewUrl = useMemo(
    () => URL.createObjectURL(item.file),
    [item.file]
  );

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="relative group"
    >
      {/* Number badge */}
      <span className="absolute top-0.5 left-0.5 z-10 w-5 h-5 bg-blue-600 text-white rounded-full text-xs flex items-center justify-center font-medium shadow">
        {index + 1}
      </span>
      <img
        src={previewUrl}
        alt={item.file.name}
        className="w-16 h-16 object-cover rounded-md border border-gray-200"
        draggable={false}
      />
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

let nextId = 0;

export default function UrlInputForm() {
  const [url, setUrl] = useState("");
  const [fileItems, setFileItems] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newItems = Array.from(e.target.files).map((file) => ({
        id: `file-${nextId++}`,
        file,
      }));
      setFileItems(newItems);
    }
  };

  const removeFile = (id: string) => {
    setFileItems((prev) => prev.filter((item) => item.id !== id));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setFileItems((prev) => {
        const oldIndex = prev.findIndex((item) => item.id === active.id);
        const newIndex = prev.findIndex((item) => item.id === over.id);
        return arrayMove(prev, oldIndex, newIndex);
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || fileItems.length === 0) return;

    setLoading(true);
    setError("");

    try {
      const files = fileItems.map((item) => item.file);
      const job = await createJob(url.trim(), files);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="flex gap-3">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="粘贴 1688 商品链接..."
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          required
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim() || fileItems.length === 0}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {loading ? "提交中..." : "生成视频"}
        </button>
      </div>

      {/* Image upload area */}
      <div className="mt-4">
        <label
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center justify-center w-full px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
        >
          <div className="text-center">
            <p className="text-sm text-gray-600">
              点击选择商品图片（可多选）
            </p>
            <p className="text-xs text-gray-400 mt-1">
              支持 JPG / PNG / WebP，建议 3-10 张
            </p>
          </div>
        </label>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={handleFiles}
          className="hidden"
          disabled={loading}
        />
      </div>

      {/* Thumbnail previews with drag-and-drop reordering */}
      {fileItems.length > 0 && (
        <div className="mt-3">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={fileItems.map((item) => item.id)}
              strategy={horizontalListSortingStrategy}
            >
              <div className="flex flex-wrap gap-2">
                {fileItems.map((item, idx) => (
                  <SortableImageItem
                    key={item.id}
                    item={item}
                    index={idx}
                    onRemove={() => removeFile(item.id)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          <p className="text-xs text-gray-500 mt-1">
            已选择 {fileItems.length} 张图片 · 拖拽调整顺序
          </p>
        </div>
      )}

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  );
}
