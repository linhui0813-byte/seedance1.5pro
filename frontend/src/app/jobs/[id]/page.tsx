"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchJob } from "@/lib/api";
import { useJobProgress } from "@/hooks/useJobProgress";
import ProgressTimeline from "@/components/ProgressTimeline";
import VideoPreview from "@/components/VideoPreview";
import type { Job } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  scraping: "抓取中",
  generating_videos: "生成视频中",
  composing: "合成中",
  completed: "已完成",
  failed: "失败",
};

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [initialJob, setInitialJob] = useState<Job | null>(null);

  useEffect(() => {
    fetchJob(jobId).then(setInitialJob).catch(() => {});
  }, [jobId]);

  const job = useJobProgress(jobId, initialJob ?? undefined);

  if (!job) {
    return (
      <main className="min-h-screen py-12 px-4">
        <div className="max-w-2xl mx-auto text-center text-gray-400">
          加载中...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="text-sm text-blue-600 hover:underline mb-6 inline-block"
        >
          &larr; 返回首页
        </Link>

        <h1 className="text-2xl font-bold mb-1">
          {job.product_title || "任务详情"}
        </h1>
        <p className="text-sm text-gray-500 mb-6 truncate">{job.url}</p>

        {/* Overall progress */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-1">
            <span className="font-medium">
              {STATUS_LABELS[job.status] ?? job.status}
            </span>
            <span className="text-gray-500">{Math.round(job.progress_pct)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${
                job.status === "failed" ? "bg-red-500" : "bg-blue-600"
              }`}
              style={{ width: `${job.progress_pct}%` }}
            />
          </div>
        </div>

        {/* Error */}
        {job.error_message && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <p className="font-medium mb-1">任务失败</p>
            <p>{job.error_message}</p>
          </div>
        )}

        {/* Steps timeline */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-700 mb-4">
            处理进度
          </h2>
          <ProgressTimeline steps={job.steps} />
        </div>

        {/* Video preview */}
        {job.status === "completed" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              生成结果
            </h2>
            <VideoPreview jobId={job.id} />

            {/* 朋友圈文案 */}
            {job.wechat_moments_copy && (
              <div className="mt-6 p-4 bg-gradient-to-r from-pink-50 to-orange-50 border border-pink-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-pink-700">朋友圈文案</h3>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(job.wechat_moments_copy || "");
                      alert("已复制到剪贴板！");
                    }}
                    className="px-3 py-1 text-sm bg-pink-500 text-white rounded-full hover:bg-pink-600 transition-colors"
                  >
                    一键复制
                  </button>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">{job.wechat_moments_copy}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
