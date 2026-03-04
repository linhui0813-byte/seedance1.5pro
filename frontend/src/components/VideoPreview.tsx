"use client";

import { getFileUrl } from "@/lib/api";

export default function VideoPreview({ jobId }: { jobId: string }) {
  const videoUrl = getFileUrl(jobId, "final_video.mp4");

  return (
    <div className="space-y-4">
      <video
        src={videoUrl}
        controls
        className="w-full max-w-md mx-auto rounded-lg shadow-lg"
        style={{ maxHeight: "70vh" }}
      />
      <div className="text-center">
        <a
          href={videoUrl}
          download="final_video.mp4"
          className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下载视频
        </a>
      </div>
    </div>
  );
}
