"use client";

import UrlInputForm from "@/components/UrlInputForm";
import JobList from "@/components/JobList";

export default function Home() {
  return (
    <main className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2">
          Seedance Video Generator
        </h1>
        <p className="text-center text-gray-500 mb-8">
          粘贴 1688 商品链接，自动生成种草短视频
        </p>

        <div className="flex justify-center mb-10">
          <UrlInputForm />
        </div>

        <h2 className="text-lg font-semibold text-gray-700 mb-4">
          最近任务
        </h2>
        <JobList />
      </div>
    </main>
  );
}
