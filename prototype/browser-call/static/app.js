const statusEl = document.querySelector("#status");
const supportEl = document.querySelector("#support");
const startButton = document.querySelector("#start");
const controls = document.querySelector("#controls");
const muteMicButton = document.querySelector("#muteMic");
const muteOutputButton = document.querySelector("#muteOutput");
const toneButton = document.querySelector("#tone");
const endButton = document.querySelector("#end");
const remoteAudio = document.querySelector("#remoteAudio");

let peer = null;
let microphone = null;

function supported() {
  return Boolean(window.RTCPeerConnection && navigator.mediaDevices?.getUserMedia);
}

function setStatus(message) {
  statusEl.textContent = message;
}

function waitForIceGathering(pc) {
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      pc.removeEventListener("icegatheringstatechange", listener);
      resolve();
    };
    const listener = () => {
      if (pc.iceGatheringState === "complete") finish();
    };
    pc.addEventListener("icegatheringstatechange", listener);
    if (pc.iceGatheringState === "complete") finish();
    window.setTimeout(finish, 2000);
  });
}

async function startCall() {
  startButton.disabled = true;
  setStatus("Requesting microphone…");
  try {
    microphone = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    peer = new RTCPeerConnection({ iceServers: [] });
    for (const track of microphone.getAudioTracks()) peer.addTrack(track, microphone);
    peer.addEventListener("track", (event) => {
      remoteAudio.srcObject = event.streams[0] || new MediaStream([event.track]);
      remoteAudio.play().catch(() => setStatus("Tap the page to allow audio playback"));
    });
    peer.addEventListener("connectionstatechange", () => {
      const state = peer?.connectionState || "closed";
      setStatus(state === "connected" ? "Connected" : state);
      if (["failed", "closed"].includes(state)) resetUi();
    });
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    await waitForIceGathering(peer);
    const response = await fetch("/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(peer.localDescription),
    });
    if (!response.ok) throw new Error("The local call bridge refused the connection.");
    const answer = await response.json();
    await peer.setRemoteDescription(answer);
    startButton.hidden = true;
    controls.hidden = false;
    setStatus("Connecting…");
  } catch (error) {
    await closeLocal();
    startButton.disabled = false;
    setStatus(error instanceof Error ? error.message : "Could not start the call");
  }
}

async function closeLocal() {
  if (microphone) microphone.getTracks().forEach((track) => track.stop());
  microphone = null;
  if (peer) peer.close();
  peer = null;
  remoteAudio.srcObject = null;
}

function resetUi() {
  controls.hidden = true;
  startButton.hidden = false;
  startButton.disabled = false;
  muteMicButton.textContent = "Mute microphone";
  muteOutputButton.textContent = "Mute Codex audio";
}

startButton.addEventListener("click", startCall);
muteMicButton.addEventListener("click", () => {
  const track = microphone?.getAudioTracks()[0];
  if (!track) return;
  track.enabled = !track.enabled;
  muteMicButton.textContent = track.enabled ? "Mute microphone" : "Unmute microphone";
});
muteOutputButton.addEventListener("click", () => {
  remoteAudio.muted = !remoteAudio.muted;
  muteOutputButton.textContent = remoteAudio.muted ? "Unmute Codex audio" : "Mute Codex audio";
});
toneButton.addEventListener("click", async () => {
  toneButton.disabled = true;
  const response = await fetch("/test-tone", { method: "POST" });
  setStatus(response.ok ? "Playing one-second return-path test" : "Return test unavailable");
  window.setTimeout(() => { toneButton.disabled = false; }, 1200);
});
endButton.addEventListener("click", async () => {
  endButton.disabled = true;
  await fetch("/end", { method: "POST" }).catch(() => {});
  await closeLocal();
  resetUi();
  endButton.disabled = false;
  setStatus("Session ended");
});

if (!supported()) {
  startButton.disabled = true;
  supportEl.textContent = "This browser is missing secure microphone or WebRTC support.";
} else if (!window.isSecureContext) {
  startButton.disabled = true;
  supportEl.textContent = "A secure HTTPS page is required on phones.";
}
