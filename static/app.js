let currentJobId = null;
let posXFrac = 0.5;
let posYFrac = 0.85;
let transcriptWords = [];
let previewLoadedForJob = null;
let previewRequestSeq = 0;

document.getElementById("browseBtn").addEventListener("click", browseNative);
document.getElementById("transcribeBtn").addEventListener("click", startTranscribeJob);
document.getElementById("burnBtn").addEventListener("click", burnCaptions);

document.getElementById("fontSelect").addEventListener("change", updateStylePreview);
document.getElementById("allCaps").addEventListener("change", updateStylePreview);
document.getElementById("boldToggle").addEventListener("change", updateStylePreview);
debounceOnInput("fontSize");
debounceOnInput("letterSpacing");
debounceOnInput("wordsPerGroup");
debounceOnInput("outlineWidth");
debounceOnInput("highlightColor");
debounceOnInput("textColor");
debounceOnInput("outlineColor");

loadFonts();

function debounceOnInput(id) {
  let timer = null;
  document.getElementById(id).addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(updateStylePreview, 400);
  });
}

async function loadFonts() {
  const res = await fetch("/api/fonts");
  const data = await res.json();
  const select = document.getElementById("fontSelect");
  select.innerHTML = data.fonts.map((f) => `<option value="${f}">${f}</option>`).join("");
  const arial = data.fonts.findIndex((f) => f.toLowerCase() === "arial");
  if (arial > -1) select.selectedIndex = arial;
}

async function browseNative() {
  const btn = document.getElementById("browseBtn");
  btn.disabled = true;
  btn.textContent = "Waiting for dialog...";
  try {
    const res = await fetch("/api/browse-native", { method: "POST" });
    const data = await res.json();
    if (data.path) document.getElementById("videoPath").value = data.path;
  } finally {
    btn.disabled = false;
    btn.textContent = "Browse...";
  }
}

async function startTranscribeJob() {
  const videoPath = document.getElementById("videoPath").value.trim();
  if (!videoPath) return;

  document.getElementById("transcribeBtn").disabled = true;
  document.getElementById("transcriptCard").style.display = "none";
  document.getElementById("styleCard").style.display = "none";
  document.getElementById("burnCard").style.display = "none";
  document.getElementById("resultPanel").style.display = "none";
  document.getElementById("log").textContent = "";
  document.getElementById("status").textContent = "Starting...";
  previewLoadedForJob = null;

  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_path: videoPath }),
  });
  const data = await res.json();
  setCurrentJob(data.job_id);
  poll();
}

function currentStylePayload() {
  const fontSize = parseInt(document.getElementById("fontSize").value, 10);
  const letterSpacing = parseFloat(document.getElementById("letterSpacing").value);
  const outlineWidth = parseInt(document.getElementById("outlineWidth").value, 10);
  return {
    font_name: document.getElementById("fontSelect").value || null,
    font_size: Number.isFinite(fontSize) ? fontSize : null,
    letter_spacing: Number.isFinite(letterSpacing) ? letterSpacing : null,
    words_per_group: parseInt(document.getElementById("wordsPerGroup").value, 10) || null,
    pos_x_frac: posXFrac,
    pos_y_frac: posYFrac,
    all_caps: document.getElementById("allCaps").checked,
    bold: document.getElementById("boldToggle").checked,
    highlight_color: document.getElementById("highlightColor").value,
    text_color: document.getElementById("textColor").value,
    outline_color: document.getElementById("outlineColor").value,
    outline_width: Number.isFinite(outlineWidth) ? outlineWidth : null,
  };
}

async function updateStylePreview() {
  if (!currentJobId) return;
  const seq = ++previewRequestSeq;
  document.getElementById("previewLoading").style.display = "flex";
  const res = await fetch(`/api/jobs/${currentJobId}/style-preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentStylePayload()),
  });
  if (seq !== previewRequestSeq) return; // a newer request superseded this one
  if (!res.ok) {
    document.getElementById("previewLoading").textContent = "Couldn't render a preview.";
    return;
  }
  const blob = await res.blob();
  document.getElementById("previewImg").src = URL.createObjectURL(blob);
  document.getElementById("previewLoading").style.display = "none";
}

function placeDragHandle() {
  const handle = document.getElementById("dragHandle");
  handle.style.left = `${posXFrac * 100}%`;
  handle.style.top = `${posYFrac * 100}%`;
}

(function setupDrag() {
  const handle = document.getElementById("dragHandle");
  const frame = document.getElementById("previewFrame");
  let dragging = false;

  handle.addEventListener("mousedown", (e) => {
    dragging = true;
    e.preventDefault();
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = frame.getBoundingClientRect();
    posXFrac = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    posYFrac = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    placeDragHandle();
  });
  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    updateStylePreview();
  });
})();

function fmtClock(sec) {
  sec = Math.floor(sec);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function groupIntoSentences(words) {
  const groups = [];
  let current = [];
  words.forEach((w, i) => {
    current.push(i);
    const endsSentence = /[.!?]["')\]]?$/.test(w.word);
    const tooLong = current.length >= 18;
    if (endsSentence || tooLong || i === words.length - 1) {
      groups.push(current);
      current = [];
    }
  });
  return groups;
}

function renderTranscriptEditor(words) {
  transcriptWords = words;
  const container = document.getElementById("transcriptEditor");
  container.innerHTML = "";

  groupIntoSentences(words).forEach((indices) => {
    const row = document.createElement("div");
    row.className = "transcript-sentence";

    const time = document.createElement("span");
    time.className = "transcript-time";
    time.textContent = fmtClock(words[indices[0]].start);
    row.appendChild(time);

    const wordsWrap = document.createElement("span");
    wordsWrap.className = "transcript-sentence-words";
    indices.forEach((i) => {
      const span = document.createElement("span");
      span.className = "transcript-word";
      span.contentEditable = "true";
      span.textContent = words[i].word;
      span.addEventListener("blur", () => onWordEdited(i, span));
      span.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          span.blur();
        }
      });
      wordsWrap.appendChild(span);
    });
    row.appendChild(wordsWrap);
    container.appendChild(row);
  });
}

async function onWordEdited(index, span) {
  const newText = span.textContent.trim();
  if (!newText) {
    span.textContent = transcriptWords[index].word;
    return;
  }
  if (newText === transcriptWords[index].word) return;
  transcriptWords[index] = { ...transcriptWords[index], word: newText };
  span.textContent = newText;
  await fetch(`/api/jobs/${currentJobId}/words`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words: transcriptWords }),
  });
  updateStylePreview();
}

async function burnCaptions() {
  if (!currentJobId) return;
  const btn = document.getElementById("burnBtn");
  btn.disabled = true;
  const burnStatus = document.getElementById("burnStatus");
  burnStatus.textContent = "Starting...";
  burnStatus.style.display = "flex";

  const res = await fetch(`/api/jobs/${currentJobId}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentStylePayload()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    document.getElementById("status").textContent = `Failed to start: ${err.detail || res.statusText}`;
    burnStatus.style.display = "none";
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

async function revealPostTranscriptCards() {
  document.getElementById("transcriptCard").style.display = "block";
  document.getElementById("styleCard").style.display = "block";
  document.getElementById("burnCard").style.display = "block";
  if (previewLoadedForJob === currentJobId) return;
  previewLoadedForJob = currentJobId;

  const res = await fetch(`/api/jobs/${currentJobId}/words`);
  if (res.ok) {
    const data = await res.json();
    renderTranscriptEditor(data.words);
  }
  placeDragHandle();
  updateStylePreview();
}

async function poll() {
  const res = await fetch(`/api/jobs/${currentJobId}`);
  if (!res.ok) {
    document.getElementById("status").textContent = "No such job (it may have been cleared by a server restart).";
    document.getElementById("transcribeBtn").disabled = false;
    localStorage.removeItem("lastJobId");
    return;
  }
  const job = await res.json();
  const elapsed = job.elapsed_seconds != null ? ` (${fmtTime(job.elapsed_seconds)} elapsed)` : "";
  document.getElementById("status").textContent = `Status: ${job.status}${elapsed}`;
  document.getElementById("log").textContent = job.log.join("\n");
  document.getElementById("log").scrollTop = document.getElementById("log").scrollHeight;

  const BURN_LABELS = { rendering: "Starting...", building_captions: "Building captions...", burning_in: "Burning into video..." };
  const burnStatus = document.getElementById("burnStatus");
  if (BURN_LABELS[job.status]) {
    burnStatus.textContent = `${BURN_LABELS[job.status]}${elapsed}`;
    burnStatus.style.display = "flex";
  } else {
    burnStatus.style.display = "none";
  }

  if (job.status === "transcript_ready") {
    document.getElementById("transcribeBtn").disabled = false;
    document.getElementById("burnBtn").disabled = false;
    revealPostTranscriptCards();
    return;
  }
  if (job.status === "done") {
    document.getElementById("transcribeBtn").disabled = false;
    document.getElementById("burnBtn").disabled = false;
    document.getElementById("burnBtn").textContent = "Re-render with new style";
    revealPostTranscriptCards();
    showResult(job.result);
    return;
  }
  if (job.status === "error") {
    document.getElementById("transcribeBtn").disabled = false;
    document.getElementById("burnBtn").disabled = false;
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
