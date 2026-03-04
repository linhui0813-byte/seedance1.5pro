const API_BASE = "http://localhost:8000";

export async function createJob(url: string, images: File[]) {
  const formData = new FormData();
  formData.append("url", url);
  for (const img of images) {
    formData.append("images", img);
  }
  const res = await fetch(`${API_BASE}/api/jobs/`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`创建任务失败: ${res.status}`);
  return res.json();
}

export async function fetchJobs() {
  const res = await fetch(`${API_BASE}/api/jobs/`);
  if (!res.ok) throw new Error(`获取任务列表失败: ${res.status}`);
  return res.json();
}

export async function fetchJob(id: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${id}`);
  if (!res.ok) throw new Error(`获取任务详情失败: ${res.status}`);
  return res.json();
}

export function getProgressSSEUrl(id: string) {
  return `${API_BASE}/api/jobs/${id}/progress`;
}

export function getFileUrl(jobId: string, filename: string) {
  return `${API_BASE}/api/files/${jobId}/${filename}`;
}
