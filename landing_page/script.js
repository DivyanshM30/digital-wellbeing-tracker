"use strict";

const copyButton = document.getElementById("copy-command");
const command = document.getElementById("install-command");
const copyStatus = document.getElementById("copy-status");

if (copyButton && command && copyStatus && navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(command.textContent.trim());
      copyStatus.textContent = "Commands copied. Paste them into PowerShell.";
    } catch {
      copyStatus.textContent = "Could not copy. Select the commands and copy them manually.";
    }
  });
}
