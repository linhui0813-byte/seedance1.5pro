"use client";

import type { JobStep } from "@/types";

function StepIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return (
        <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    case "running":
      return (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center animate-pulse">
          <div className="w-3 h-3 bg-white rounded-full" />
        </div>
      );
    case "failed":
      return (
        <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    default:
      return (
        <div className="w-8 h-8 rounded-full bg-gray-200 border-2 border-gray-300" />
      );
  }
}

export default function ProgressTimeline({ steps }: { steps: JobStep[] }) {
  return (
    <div className="space-y-0">
      {steps.map((step, idx) => (
        <div key={step.id} className="flex gap-4">
          {/* Left: icon + connector line */}
          <div className="flex flex-col items-center">
            <StepIcon status={step.status} />
            {idx < steps.length - 1 && (
              <div className="w-0.5 flex-1 min-h-[24px] bg-gray-200" />
            )}
          </div>

          {/* Right: text */}
          <div className="pb-6 pt-1">
            <p
              className={`font-medium ${
                step.status === "running"
                  ? "text-blue-700"
                  : step.status === "completed"
                  ? "text-gray-900"
                  : step.status === "failed"
                  ? "text-red-700"
                  : "text-gray-400"
              }`}
            >
              {step.display_name}
            </p>
            {step.detail && (
              <p className="text-sm text-gray-500 mt-0.5">{step.detail}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
