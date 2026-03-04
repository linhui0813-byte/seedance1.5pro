"use client";

import { useEffect, useState } from "react";
import { fetchJobs } from "@/lib/api";
import type { JobListItem } from "@/types";
import JobCard from "./JobCard";

export default function JobList() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchJobs();
        setJobs(data);
      } catch {
        // ignore
      }
    };

    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (jobs.length === 0) {
    return (
      <p className="text-center text-gray-400 py-8">
        暂无任务，粘贴 1688 链接开始生成视频
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
