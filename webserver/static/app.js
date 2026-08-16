const $ = (id) => document.getElementById(id);
const page = document.body.dataset.page;
let latestState = null;
let assets = [];
let modes = [];
let selectedModeId = null;
let automationFormInitialized = false;

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
    if (!automationFormInitialized) populateAutomationForm(state.automation);
  }
  const card = document.querySelector(".mode-card");
  if (card) card.classList.toggle("active", card.dataset.mode === state.mode);
  const selectedAsset = state.mode_options?.asset_id;
  if (selectedAsset) {
    const assetSelect = document.querySelector(`[data-asset-for="${state.mode}"]`);
    if (assetSelect) assetSelect.value = selectedAsset;
  }
  if (state.mode_error) {
    setStatus(`Mode error (${state.mode_error.mode}): ${state.mode_error.message}`, true);
  } else {
    setStatus(state.mode ? `${state.mode} · ${state.sleep_reason.replaceAll("_", " ")}` : "No mode selected");
  }
}
async function refresh() { try { renderState(await api("/api/state")); } catch (error) { setStatus(error.message, true); } }

function populateAutomationForm(automation) {
  $("automation-enabled").checked = automation.enabled;
  setValue("sleep-lux", automation.sleep_lux); setValue("wake-lux", automation.wake_lux); setValue("sleep-dwell", automation.sleep_dwell_seconds);
  setValue("wake-dwell", automation.wake_dwell_seconds); setValue("poll-seconds", automation.poll_seconds); setValue("min-brightness", automation.min_brightness);
  setValue("max-lux", automation.max_lux); setValue("override-policy", automation.manual_override_policy); setValue("override-minutes", automation.manual_override_minutes);
  automationFormInitialized = true;
}

function createModeSetting(field, value) {
  const label = document.createElement("label");
  label.textContent = field.label;
  const input = document.createElement(field.type === "select" ? "select" : "input");
  input.dataset.modeSetting = field.key;
  if (field.type === "select") {
    for (const choice of field.choices) {
      const option = document.createElement("option");
      option.value = choice.value;
      option.textContent = choice.label;
      input.append(option);
    }
  } else {
    input.type = field.type === "color" ? "color" : field.type === "boolean" ? "checkbox" : "range";
    input.min = field.min;
    input.max = field.max;
    input.step = field.step;
  }
  input.value = value;
  if (field.type === "boolean") input.checked = Boolean(value);

  label.append(input);
  if (field.help) {
    const help = document.createElement("span");
    help.className = "help";
    help.textContent = field.help;
    label.append(help);
  }
  return {element: label, input};
}

function syncColorModeControls(settingInputs, modeKey, relevantModes) {
  const colorMode = settingInputs[modeKey];
  if (!colorMode) return;
  for (const [key, requiredMode] of Object.entries(relevantModes)) {
    const input = settingInputs[key];
    if (!input) continue;
    const label = input.closest("label");
    const isRelevant = colorMode.value === requiredMode;
    label.style.display = isRelevant ? "" : "none";
    label.setAttribute("aria-hidden", String(!isRelevant));
  }
}

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
  const settingInputs = {};

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
  for (const [key, definition] of Object.entries(mode.settings_schema)) {
    const field = {...definition, key};
    const value = latestState?.mode === mode.id ? (latestState.mode_options?.[key] ?? field.default) : field.default;
    const control = createModeSetting(field, value);
    settingInputs[key] = control.input;
    settings.append(control.element);
  }

  const colorModeControls = {
    life: {modeKey: "alive_color_mode", relevantModes: {alive_fixed_color: "fixed", rainbow_cycle_speed: "rainbow_cycle", rainbow_gradient_speed: "rainbow_gradient"}},
    rain: {modeKey: "rain_color_mode", relevantModes: {rain_fixed_color: "fixed", rainbow_cycle_speed: "rainbow_cycle", rainbow_gradient_speed: "rainbow_gradient"}},
  };
  const colorControls = colorModeControls[mode.id];
  if (colorControls) {
    syncColorModeControls(settingInputs, colorControls.modeKey, colorControls.relevantModes);
    settingInputs[colorControls.modeKey].addEventListener("change", () => syncColorModeControls(settingInputs, colorControls.modeKey, colorControls.relevantModes));
  }

  card.append(settings);
  const launch = document.createElement("button");
  launch.textContent = mode.id === "off" ? "Turn display off" : `Start ${mode.name}`;
  launch.onclick = async () => {
    try {
      if (mode.requires_asset && !assetSelect.value) throw new Error("Add an image or GIF to the res directory first.");
      renderState(await api("/api/mode", {method: "POST", body: JSON.stringify({mode: mode.id, asset_id: assetSelect?.value, settings: Object.fromEntries(Object.entries(settingInputs).map(([key, input]) => [key, input.type === "checkbox" ? input.checked : input.value]))})}));
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
      const state = await api("/api/settings", {method: "PATCH", body: JSON.stringify({automation})});
      populateAutomationForm(state.automation);
      renderState(state);
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
