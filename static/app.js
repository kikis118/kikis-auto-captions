let currentJobId = null;

document.getElementById("runBtn").addEventListener("click", startJob);

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
