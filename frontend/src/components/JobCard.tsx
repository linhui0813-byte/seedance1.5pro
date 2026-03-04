"use client";

import Link from "next/link";
import type { JobListItem } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  scraping: "抓取中",
  generating_videos: "生成视频中",
  composing: "合成中",
  completed: "已完成",
  failed: "失败",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  scraping: "bg-blue-100 text-blue-700",
  generating_videos: "bg-blue-100 text-blue-700",
  composing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function JobCard({ job }: { job: JobListItem }) {
  const statusLabel = STATUS_LABELS[job.status] ?? job.status;
  const statusColor = STATUS_COLORS[job.status] ?? "bg-gray-100 text-gray-700";
  const time = new Date(job.created_at).toLocaleString("zh-CN");

  return (
    <Link href={`/jobs/${job.id}`}>
      <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-gray-900 truncate flex-1 mr-3">
            {job.product_title || "加载中..."}
          </h3>
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}
          >
            {statusLabel}
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${job.progress_pct}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-gray-500">
          <span className="truncate max-w-[60%]">{job.url}</span>
          <span>{time}</span>
        </div>
      </div>
    </Link>
  );
}
