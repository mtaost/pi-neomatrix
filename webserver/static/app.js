const $ = (id) => document.getElementById(id);
const page = document.body.dataset.page;
let latestState = null;
let assets = [];
let modes = [];
let selectedModeId = null;

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data.state;
}
function setStatus(message, error = false) {
  const element = $("status");
  element.textContent = message;
  element.style.color = error ? "#ff9d9d" : "";
}
function number(id) { return Number($(id).value); }
function setValue(id, value) { const element = $(id); if (element) element.value = value; }
function renderState(state) {
  latestState = state;
  const brightness = $("brightness");
  if (brightness) {
    brightness.value = state.user_brightness;
    $("brightness-value").textContent = `${Math.round(state.user_brightness * 100)}%`;
    const powerToggle = $("power-toggle");
    powerToggle.classList.toggle("is-off", !state.power);
    powerToggle.setAttribute("aria-pressed", String(state.power));
    powerToggle.setAttribute("aria-label", state.power ? "Turn display off" : "Turn display on");
    powerToggle.title = state.power ? "Turn display off" : "Turn display on";
  }
  if ($("effective-brightness")) {
    $("effective-brightness").textContent = `${Math.round(state.effective_brightness * 100)}%${state.sleeping ? " (sleeping)" : ""}`;
    $("sensor-status").textContent = state.sensor.available ? (state.sensor.error || "Available") : (state.sensor.error || "Unavailable");
    $("sensor-lux").textContent = state.sensor.lux == null ? "No reading" : `${state.sensor.lux.toFixed(1)} lux`;
    const a = state.automation;
    $("automation-enabled").checked = a.enabled;
    setValue("sleep-lux", a.sleep_lux); setValue("wake-lux", a.wake_lux); setValue("sleep-dwell", a.sleep_dwell_seconds);
    setValue("wake-dwell", a.wake_dwell_seconds); setValue("poll-seconds", a.poll_seconds); setValue("min-brightness", a.min_brightness);
    setValue("max-lux", a.max_lux); setValue("override-policy", a.manual_override_policy); setValue("override-minutes", a.manual_override_minutes);
  }
  const card = document.querySelector(".mode-card");
  if (card) card.classList.toggle("active", card.dataset.mode === state.mode);
  const selectedAsset = state.mode_options?.asset_id;
  if (selectedAsset) {
    const assetSelect = document.querySelector(`[data-asset-for="${state.mode}"]`);
    if (assetSelect) assetSelect.value = selectedAsset;
  }
  setStatus(state.mode ? `${state.mode} · ${state.sleep_reason.replaceAll("_", " ")}` : "No mode selected");
}
async function refresh() { try { renderState(await api("/api/state")); } catch (error) { setStatus(error.message, true); } }

function createModeCard(mode) {
  const card = document.createElement("article");
  card.className = "mode-card";
  card.dataset.mode = mode.id;
  const header = document.createElement("div");
  header.className = "mode-card-header";
  const title = document.createElement("h3");
  title.textContent = mode.name;
  header.append(title);
  if (mode.capabilities.length) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = mode.capabilities.join(", ");
    header.append(badge);
  }
  card.append(header);
  const description = document.createElement("p");
  description.className = "mode-description";
  description.textContent = mode.requires_asset ? "Choose a bundled image or GIF below." : "Mode-specific controls will appear here as they are added.";
  card.append(description);
  const settings = document.createElement("div");
  settings.className = "mode-settings";
  let assetSelect = null;
  if (mode.requires_asset) {
    const label = document.createElement("label");
    label.textContent = "Image or GIF";
    assetSelect = document.createElement("select");
    assetSelect.dataset.assetFor = mode.id;
    for (const asset of assets) {
      const option = document.createElement("option");
      option.value = asset.id;
      option.textContent = asset.name;
      assetSelect.append(option);
    }
    label.append(assetSelect);
    settings.append(label);
  }
  card.append(settings);
  const launch = document.createElement("button");
  launch.textContent = mode.id === "off" ? "Turn display off" : `Start ${mode.name}`;
  launch.onclick = async () => {
    try {
      if (mode.requires_asset && !assetSelect.value) throw new Error("Add an image or GIF to the res directory first.");
      renderState(await api("/api/mode", {method: "POST", body: JSON.stringify({mode: mode.id, asset_id: assetSelect?.value})}));
    } catch (error) { setStatus(error.message, true); }
  };
  card.append(launch);
  return card;
}

function renderSelectedMode() {
  const mode = modes.find(candidate => candidate.id === selectedModeId);
  const container = $("mode-card");
  container.replaceChildren();
  if (mode) container.append(createModeCard(mode));
  if (latestState) renderState(latestState);
}

async function initDisplayPage() {
  const [modeResponse, assetResponse] = await Promise.all([api("/api/modes"), api("/api/assets")]);
  modes = modeResponse.modes;
  assets = assetResponse.assets;
  const select = $("mode-select");
  for (const mode of modes) {
    const option = document.createElement("option");
    option.value = mode.id;
    option.textContent = mode.name;
    select.append(option);
  }
  selectedModeId = latestState?.mode || modes[0]?.id || null;
  select.value = selectedModeId;
  select.onchange = () => { selectedModeId = select.value; renderSelectedMode(); };
  renderSelectedMode();
  $("brightness").oninput = () => { $("brightness-value").textContent = `${Math.round(number("brightness") * 100)}%`; };
  $("brightness").onchange = async () => { try { renderState(await api("/api/settings", {method: "PATCH", body: JSON.stringify({brightness: number("brightness")})})); } catch (error) { setStatus(error.message, true); } };
  $("power-toggle").onclick = async () => { try { renderState(await api("/api/power", {method: "POST", body: JSON.stringify({on: !latestState.power})})); } catch (error) { setStatus(error.message, true); } };
}

function initAutomationPage() {
  $("save-automation").onclick = async () => {
    try {
      const automation = {enabled: $("automation-enabled").checked, sleep_lux: number("sleep-lux"), wake_lux: number("wake-lux"), sleep_dwell_seconds: number("sleep-dwell"), wake_dwell_seconds: number("wake-dwell"), poll_seconds: number("poll-seconds"), min_brightness: number("min-brightness"), max_lux: number("max-lux"), manual_override_policy: $("override-policy").value, manual_override_minutes: number("override-minutes")};
      renderState(await api("/api/settings", {method: "PATCH", body: JSON.stringify({automation})}));
    } catch (error) { setStatus(error.message, true); }
  };
}

async function init() {
  try {
    await refresh();
    if (page === "display") await initDisplayPage();
    if (page === "automation") initAutomationPage();
  } catch (error) { setStatus(error.message, true); }
}
init();
setInterval(refresh, 5000);
