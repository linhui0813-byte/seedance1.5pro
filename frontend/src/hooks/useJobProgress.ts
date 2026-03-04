"use client";

import { useEffect, useState, useRef } from "react";
import { getProgressSSEUrl } from "@/lib/api";
import type { Job } from "@/types";

export function useJobProgress(jobId: string, initialJob?: Job) {
  const [job, setJob] = useState<Job | null>(initialJob ?? null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // 如果已经完成或失败，不需要 SSE
    if (job?.status === "completed" || job?.status === "failed") return;

    const es = new EventSource(getProgressSSEUrl(jobId));
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Job;
        setJob(data);

        if (data.status === "completed" || data.status === "failed") {
          es.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  return job;
}
