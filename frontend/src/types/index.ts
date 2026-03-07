export interface JobStep {
  id: number;
  step_order: number;
  step_name: string;
  display_name: string;
  status: "pending" | "running" | "completed" | "failed";
  detail: string | null;
}

export interface Job {
  id: string;
  url: string;
  status:
    | "pending"
    | "scraping"
    | "generating_videos"
    | "composing"
    | "completed"
    | "failed";
  product_title: string | null;
  error_message: string | null;
  progress_pct: number;
  final_video_path: string | null;
  wechat_moments_copy: string | null;
  created_at: string;
  updated_at: string;
  steps: JobStep[];
}

export interface JobListItem {
  id: string;
  url: string;
  status: string;
  product_title: string | null;
  progress_pct: number;
  created_at: string;
  updated_at: string;
}
