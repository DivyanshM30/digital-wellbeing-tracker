"use client";

import { useEffect, useState } from "react";

const commands = "git clone https://github.com/DivyanshM30/digital-wellbeing-tracker.git\ncd digital-wellbeing-tracker\npy -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.\\.venv\\Scripts\\python.exe main.py";

export default function InstallCommands() {
  const [canCopy, setCanCopy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    setCanCopy(Boolean(navigator.clipboard && window.isSecureContext));
  }, []);

  async function copyCommands() {
    try {
      await navigator.clipboard.writeText(commands.trim());
      setStatus("Commands copied. Paste them into PowerShell.");
    } catch {
      setStatus("Could not copy. Select the commands and copy them manually.");
    }
  }

  return (
    <div className="install-panel">
      <div className="install-header">
        <span>POWERSHELL</span>
        <button id="copy-command" type="button" hidden={!canCopy} onClick={copyCommands}>Copy commands</button>
      </div>
      <pre><code id="install-command">{commands}</code></pre>
      <p id="copy-status" className="copy-status" role="status" aria-live="polite">{status}</p>
      <p className="install-note">Source installation only. A verified Windows installer is not provided on this page.</p>
    </div>
  );
}
