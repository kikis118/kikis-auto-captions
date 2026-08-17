let currentJobId = null;
let browsePath = "";

document.getElementById("runBtn").addEventListener("click", startJob);
document.getElementById("browseBtn").addEventListener("click", () => openBrowser());
document.getElementById("browseCloseBtn").addEventListener("click", closeBrowser);
document.getElementById("browseModal").addEventListener("click", (e) => {
  if (e.target.id === "browseModal") closeBrowser();
});

function joinPath(base, name) {
  if (base.endsWith("\\") || base.endsWith("/")) return base + name;
  return base + "\\" + name;
}

async function openBrowser() {
  const existing = document.getElementById("videoPath").value.trim();
  let startPath = "";
  if (existing) {
    const idx = Math.max(existing.lastIndexOf("\\"), existing.lastIndexOf("/"));
    if (idx > -1) startPath = existing.slice(0, idx + 1);
  }
  document.getElementById("browseModal").style.display = "flex";
  await browseTo(startPath);
}

function closeBrowser() {
  document.getElementById("browseModal").style.display = "none";
}

async function browseTo(path) {
  const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
  if (!res.ok) return;
  const data = await res.json();
  browsePath = data.path;
  document.getElementById("browsePath").textContent = data.path || "This PC";

  const rows = [];
  if (data.parent !== null) {
    rows.push(`<div class="browse-item browse-up" data-path="${escapeAttr(data.parent)}">.. (up)</div>`);
  } else if (data.path) {
    rows.push(`<div class="browse-item browse-up" data-path="">.. (up)</div>`);
  }
  for (const d of data.dirs) {
    const full = data.path ? joinPath(data.path, d) : d;
    rows.push(`<div class="browse-item browse-dir" data-path="${escapeAttr(full)}">📁 ${escapeHtml(d)}</div>`);
  }
  for (const f of data.files) {
    const full = joinPath(data.path, f);
    rows.push(`<div class="browse-item browse-file" data-file="${escapeAttr(full)}">🎬 ${escapeHtml(f)}</div>`);
  }
  document.getElementById("browseList").innerHTML = rows.length
    ? rows.join("")
    : `<div class="browse-empty">No folders or video files here.</div>`;

  document.querySelectorAll(".browse-dir, .browse-up").forEach((el) => {
    el.addEventListener("click", () => browseTo(el.dataset.path));
  });
  document.querySelectorAll(".browse-file").forEach((el) => {
    el.addEventListener("click", () => {
      document.getElementById("videoPath").value = el.dataset.file;
      closeBrowser();
    });
  });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) {
  return escapeHtml(s);
}

async function startJob() {
  const videoPath = document.getElementById("videoPath").value.trim();
  if (!videoPath) return;

  document.getElementById("runBtn").disabled = true;
  document.getElementById("resultPanel").style.display = "none";
  document.getElementById("log").textContent = "";
  document.getElementById("status").textContent = "Starting...";

  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_path: videoPath }),
  });
  const data = await res.json();
  setCurrentJob(data.job_id);
  poll();
}

function setCurrentJob(jobId) {
  currentJobId = jobId;
  localStorage.setItem("lastJobId", jobId);
  const url = new URL(window.location);
  url.searchParams.set("job", jobId);
  window.history.replaceState({}, "", url);
}

window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const jobId = params.get("job") || localStorage.getItem("lastJobId");
  if (jobId) {
    setCurrentJob(jobId);
    document.getElementById("status").textContent = "Reconnecting to job...";
    poll();
  }
});

function fmtTime(sec) {
  sec = Math.floor(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return (h ? h + "h" : "") + String(m).padStart(2, "0") + "m" + String(s).padStart(2, "0") + "s";
}

async function poll() {
  const res = await fetch(`/api/jobs/${currentJobId}`);
  if (!res.ok) {
    document.getElementById("status").textContent = "No such job (it may have been cleared by a server restart).";
    document.getElementById("runBtn").disabled = false;
    localStorage.removeItem("lastJobId");
    return;
  }
  const job = await res.json();
  const elapsed = job.elapsed_seconds != null ? ` (${fmtTime(job.elapsed_seconds)} elapsed)` : "";
  document.getElementById("status").textContent = `Status: ${job.status}${elapsed}`;
  document.getElementById("log").textContent = job.log.join("\n");
  document.getElementById("log").scrollTop = document.getElementById("log").scrollHeight;

  if (job.status === "done") {
    document.getElementById("runBtn").disabled = false;
    showResult(job.result);
    return;
  }
  if (job.status === "error") {
    document.getElementById("runBtn").disabled = false;
    document.getElementById("status").textContent = `Error: ${job.error}`;
    return;
  }
  setTimeout(poll, 3000);
}

function showResult(result) {
  document.getElementById("resultPanel").style.display = "block";
  document.getElementById("outputPath").textContent = result.output_path;
  const filename = result.output_path.split(/[\\/]/).pop();
  document.getElementById("preview").src = `/output/${currentJobId}/${filename}`;
}
