const form = document.getElementById("download-form");
if (form) {
  form.addEventListener("submit", startDownload);
}

function startDownload(e) {
  e.preventDefault();

  const url = document.getElementById("url").value.trim();
  if (!url) return;

  const log = document.getElementById("log");
  const status = document.getElementById("status");
  const progressContainer = document.getElementById("progress-container");
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  const btn = document.getElementById("download-btn");

  // Reset UI
  log.textContent = "";
  status.textContent = "";
  status.className = "status hidden";
  progressContainer.classList.add("hidden");
  progressFill.style.width = "0%";
  btn.disabled = true;
  btn.textContent = "Downloading...";

  fetch("/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  }).then(response => {
    if (!response.ok) {
      return response.json().then(data => {
        showStatus(status, data.error || "Request failed", "error");
        resetButton(btn);
      });
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) {
          resetButton(btn);
          return;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const jsonStr = line.slice(line.indexOf(":") + 1).trim();

          let event;
          try {
            event = JSON.parse(jsonStr);
          } catch {
            appendLog(log, jsonStr);
            continue;
          }

          handleEvent(event, log, status, progressContainer, progressFill, progressText);
        }

        read();
      });
    }

    read();
  }).catch(err => {
    showStatus(status, "Connection error: " + err.message, "error");
    resetButton(btn);
  });
}

function handleEvent(event, log, status, progressContainer, progressFill, progressText) {
  switch (event.type) {
    case "info":
      appendLog(log, event.message);
      if (event.total > 0) {
        progressContainer.classList.remove("hidden");
        progressText.textContent = `0 / ${event.total}`;
      }
      break;

    case "progress":
      appendLog(log, event.message);
      if (event.total > 0) {
        progressContainer.classList.remove("hidden");
        const pct = Math.round((event.current / event.total) * 100);
        progressFill.style.width = pct + "%";
        progressText.textContent = `${event.current} / ${event.total}`;
      }
      break;

    case "error":
      appendLog(log, "ERROR: " + event.message, "error");
      break;

    case "complete":
      appendLog(log, event.message);
      showStatus(status, event.message, "success");
      if (event.total > 0) {
        progressFill.style.width = "100%";
        progressText.textContent = `${event.total} / ${event.total}`;
      }
      break;
  }
}

function appendLog(log, text, type) {
  const line = document.createElement("div");
  line.textContent = text;
  if (type === "error") line.className = "log-error";
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function showStatus(el, message, type) {
  el.textContent = message;
  el.className = "status status-" + type;
}

function resetButton(btn) {
  btn.disabled = false;
  btn.textContent = "Download";
}
