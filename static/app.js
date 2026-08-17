let currentJobId = null;
let posXFrac = 0.5;
let posYFrac = 0.85;

document.getElementById("runBtn").addEventListener("click", startJob);
document.getElementById("rerenderBtn").addEventListener("click", rerenderJob);
document.getElementById("browseBtn").addEventListener("click", browseNative);
document.getElementById("previewBtn").addEventListener("click", loadPreview);
document.getElementById("videoPath").addEventListener("change", loadPreview);
document.getElementById("fontSelect").addEventListener("change", (e) => {
  document.getElementById("captionBox").style.fontFamily = e.target.value;
});
document.getElementById("allCaps").addEventListener("change", (e) => {
  document.getElementById("captionBox").classList.toggle("caps", e.target.checked);
});

loadFonts();

async function loadFonts() {
  const res = await fetch("/api/fonts");
  const data = await res.json();
  const select = document.getElementById("fontSelect");
  select.innerHTML = data.fonts.map((f) => `<option value="${f}">${f}</option>`).join("");
  const arial = data.fonts.findIndex((f) => f.toLowerCase() === "arial");
  if (arial > -1) select.selectedIndex = arial;
  document.getElementById("captionBox").style.fontFamily = select.value;
}

async function browseNative() {
  const btn = document.getElementById("browseBtn");
  btn.disabled = true;
  btn.textContent = "Waiting for dialog...";
  try {
    const res = await fetch("/api/browse-native", { method: "POST" });
    const data = await res.json();
    if (data.path) {
      document.getElementById("videoPath").value = data.path;
      loadPreview();
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Browse...";
  }
}

async function loadPreview() {
  const videoPath = document.getElementById("videoPath").value.trim();
  if (!videoPath) return;

  const btn = document.getElementById("previewBtn");
  btn.disabled = true;
  btn.textContent = "Loading frame...";
  try {
    const res = await fetch(`/api/thumbnail?video_path=${encodeURIComponent(videoPath)}`);
    if (!res.ok) {
      document.getElementById("previewHint").textContent = "Couldn't load a preview frame for that file.";
      return;
    }
    const blob = await res.blob();
    document.getElementById("previewImg").src = URL.createObjectURL(blob);
    document.getElementById("previewWrap").style.display = "block";
    document.getElementById("previewHint").textContent = "";
    placeCaptionBox();
  } finally {
    btn.disabled = false;
    btn.textContent = "↻ Refresh preview";
  }
}

function placeCaptionBox() {
  const box = document.getElementById("captionBox");
  box.style.left = `${posXFrac * 100}%`;
  box.style.top = `${posYFrac * 100}%`;
}

(function setupDrag() {
  const box = document.getElementById("captionBox");
  const frame = document.getElementById("previewFrame");
  let dragging = false;

  box.addEventListener("mousedown", (e) => {
    dragging = true;
    e.preventDefault();
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = frame.getBoundingClientRect();
    posXFrac = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    posYFrac = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    placeCaptionBox();
  });
  window.addEventListener("mouseup", () => {
    dragging = false;
  });
})();

function currentStylePayload() {
  return {
    font_name: document.getElementById("fontSelect").value || null,
    words_per_group: parseInt(document.getElementById("wordsPerGroup").value, 10) || null,
    pos_x_frac: posXFrac,
    pos_y_frac: posYFrac,
    all_caps: document.getElementById("allCaps").checked,
  };
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
    body: JSON.stringify({ video_path: videoPath, ...currentStylePayload() }),
  });
  const data = await res.json();
  setCurrentJob(data.job_id);
  poll();
}

async function rerenderJob() {
  if (!currentJobId) return;
  const btn = document.getElementById("rerenderBtn");
  btn.disabled = true;
  document.getElementById("status").textContent = "Re-rendering with new style...";

  const res = await fetch(`/api/jobs/${currentJobId}/rerender`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentStylePayload()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    document.getElementById("status").textContent = `Re-render failed: ${err.detail || res.statusText}`;
    btn.disabled = false;
    return;
  }
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
    document.getElementById("rerenderBtn").disabled = false;
    showResult(job.result);
    return;
  }
  if (job.status === "error") {
    document.getElementById("runBtn").disabled = false;
    document.getElementById("rerenderBtn").disabled = false;
    document.getElementById("status").textContent = `Error: ${job.error}`;
    return;
  }
  setTimeout(poll, 3000);
}

function showResult(result) {
  document.getElementById("resultPanel").style.display = "block";
  document.getElementById("outputPath").textContent = result.output_path;
  const filename = result.output_path.split(/[\\/]/).pop();
  document.getElementById("preview").src = `/output/${currentJobId}/${filename}?t=${Date.now()}`;
}
