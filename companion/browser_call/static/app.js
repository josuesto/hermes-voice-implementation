const statusEl = document.querySelector("#status");
const supportEl = document.querySelector("#support");
const startButton = document.querySelector("#start");
const controls = document.querySelector("#controls");
const muteMicButton = document.querySelector("#muteMic");
const muteOutputButton = document.querySelector("#muteOutput");
const toneButton = document.querySelector("#tone");
const endButton = document.querySelector("#end");
const remoteAudio = document.querySelector("#remoteAudio");
const peerStateEl = document.querySelector("#peerState");
const micLabelEl = document.querySelector("#micLabel");
const meterEl = document.querySelector("#meter");
const micSelectWrap = document.querySelector("#micSelectWrap");
const micSelect = document.querySelector("#micSelect");

let peer = null;
let microphone = null;
let meterContext = null;
let meterAnalyser = null;
let meterSource = null;
let meterRaf = 0;
let switchingMic = false;

function supported() {
  return Boolean(window.RTCPeerConnection && navigator.mediaDevices?.getUserMedia);
}

function setStatus(message) {
  statusEl.textContent = message;
}

function setPeerState(state) {
  peerStateEl.textContent = `WebRTC: ${state}`;
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

function showMicLabel(track) {
  const label = track?.label ? track.label : "selected";
  micLabelEl.hidden = false;
  micLabelEl.textContent = `Microphone: ${label}`;
}

function stopMeter() {
  if (meterRaf) window.cancelAnimationFrame(meterRaf);
  meterRaf = 0;
  if (meterSource) meterSource.disconnect();
  meterSource = null;
  meterAnalyser = null;
  if (meterContext) meterContext.close().catch(() => {});
  meterContext = null;
  meterEl.hidden = true;
  meterEl.style.setProperty("--level", "0");
  meterEl.dataset.state = "silent";
}

function attachMeter(stream) {
  stopMeter();
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;
  meterContext = new AudioCtx();
  meterAnalyser = meterContext.createAnalyser();
  meterAnalyser.fftSize = 256;
  meterSource = meterContext.createMediaStreamSource(stream);
  meterSource.connect(meterAnalyser);
  meterEl.hidden = false;
  const data = new Uint8Array(meterAnalyser.fftSize);
  const tick = () => {
    if (!meterAnalyser) return;
    meterAnalyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i += 1) {
      const centered = (data[i] - 128) / 128;
      sum += centered * centered;
    }
    const rms = Math.sqrt(sum / data.length);
    meterEl.style.setProperty("--level", String(Math.min(1, rms * 4)));
    meterEl.dataset.state = rms > 0.02 ? "receiving" : "silent";
    meterRaf = window.requestAnimationFrame(tick);
  };
  tick();
}

async function listInputDevices() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((device) => device.kind === "audioinput");
}

async function fillMicSelect() {
  const inputs = await listInputDevices();
  if (inputs.length < 2) {
    micSelectWrap.hidden = true;
    return;
  }
  const currentId = microphone?.getAudioTracks()[0]?.getSettings?.().deviceId || "";
  micSelect.innerHTML = "";
  for (const input of inputs) {
    const option = document.createElement("option");
    option.value = input.deviceId;
    option.textContent = input.label || "Microphone";
    micSelect.appendChild(option);
  }
  if (currentId) micSelect.value = currentId;
  micSelectWrap.hidden = false;
}

async function replaceOutgoingTrack(nextStream) {
  const nextTrack = nextStream.getAudioTracks()[0];
  const sender = peer?.getSenders().find((item) => item.track && item.track.kind === "audio");
  if (!sender) {
    nextStream.getTracks().forEach((track) => track.stop());
    throw new Error("No audio sender is available");
  }
  try {
    await sender.replaceTrack(nextTrack);
  } catch (error) {
    nextStream.getTracks().forEach((track) => track.stop());
    throw error;
  }
  if (microphone) microphone.getTracks().forEach((track) => track.stop());
  microphone = nextStream;
  attachMeter(nextStream);
  showMicLabel(nextTrack);
}

async function switchMicrophone(deviceId) {
  if (!peer || switchingMic || !deviceId) return;
  switchingMic = true;
  try {
    const next = await navigator.mediaDevices.getUserMedia({
      audio: {
        deviceId: { exact: deviceId },
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
    await replaceOutgoingTrack(next);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not switch microphone");
  } finally {
    switchingMic = false;
  }
}

async function startCall() {
  startButton.disabled = true;
  setStatus("Requesting microphone…");
  setPeerState("connecting");
  try {
    microphone = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    showMicLabel(microphone.getAudioTracks()[0]);
    attachMeter(microphone);
    await fillMicSelect();
    peer = new RTCPeerConnection({ iceServers: [] });
    for (const track of microphone.getAudioTracks()) peer.addTrack(track, microphone);
    peer.addEventListener("track", (event) => {
      remoteAudio.srcObject = event.streams[0] || new MediaStream([event.track]);
      remoteAudio.play().catch(() => setStatus("Tap the page to allow audio playback"));
    });
    peer.addEventListener("connectionstatechange", () => {
      const state = peer?.connectionState || "closed";
      setPeerState(state);
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
    setPeerState("none");
    setStatus(error instanceof Error ? error.message : "Could not start the call");
  }
}

async function closeLocal() {
  stopMeter();
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
  micSelectWrap.hidden = true;
  micSelect.innerHTML = "";
  micLabelEl.hidden = true;
  micLabelEl.textContent = "";
  stopMeter();
}

startButton.addEventListener("click", startCall);
micSelect.addEventListener("change", () => switchMicrophone(micSelect.value));
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
  setPeerState("none");
  setStatus("Call left. You can start the call again.");
});

if (!supported()) {
  startButton.disabled = true;
  supportEl.textContent = "This browser is missing secure microphone or WebRTC support.";
} else if (!window.isSecureContext) {
  startButton.disabled = true;
  supportEl.textContent = "A secure HTTPS page is required on phones.";
}
