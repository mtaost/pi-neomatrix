const $ = (id) => document.getElementById(id);
const page = document.body.dataset.page;
let latestState = null;
let assets = [];
let modes = [];
let selectedModeId = null;
let automationFormInitialized = false;

let modeSettingsTimer = null;
let modeSettingsRequest = Promise.resolve();
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
    const thermal = state.thermal || {};
    const occupancy = state.occupancy || {};
    $("thermal-status").textContent = thermal.available ? (thermal.error || "Available") : (thermal.error || "Unavailable");
    $("occupancy-status").textContent = occupancy.calibrating ? "Calibrating" : occupancy.present ? "Present" : "Empty";
    $("occupancy-confidence").textContent = occupancy.confidence == null ? "—" : `${Math.round(occupancy.confidence * 100)}%`;
    const background = occupancy.background_temperature;
    const maximum = occupancy.maximum_temperature;
    $("occupancy-temperature").textContent = background == null ? "No reading" : `${background.toFixed(1)} / ${maximum.toFixed(1)} °C`;
    if (!automationFormInitialized) populateAutomationForm(state.automation, occupancy);
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

function populateAutomationForm(automation, occupancy) {
  $("automation-enabled").checked = automation.enabled;
  setValue("sleep-lux", automation.sleep_lux); setValue("wake-lux", automation.wake_lux); setValue("sleep-dwell", automation.sleep_dwell_seconds);
  setValue("wake-dwell", automation.wake_dwell_seconds); setValue("poll-seconds", automation.poll_seconds); setValue("min-brightness", automation.min_brightness);
  setValue("max-lux", automation.max_lux); setValue("override-policy", automation.manual_override_policy); setValue("override-minutes", automation.manual_override_minutes);
  if (occupancy) {
    $("occupancy-enabled").checked = Boolean(occupancy.enabled);
    setValue("occupancy-delta", occupancy.temperature_delta_f); setValue("occupancy-region", occupancy.minimum_region_size);
    setValue("occupancy-absence-dwell", occupancy.absence_dwell_seconds); setValue("occupancy-presence-dwell", occupancy.presence_dwell_seconds);
    setValue("occupancy-calibration", occupancy.startup_calibration_seconds); setValue("occupancy-edge", occupancy.edge_exclusion);
  }
  syncAutomationSettingsVisibility();
  automationFormInitialized = true;
}

function syncAutomationSettingsVisibility() {
  const ambientSettings = $("ambient-settings");
  const occupancySettings = $("occupancy-settings");
  if (ambientSettings) ambientSettings.hidden = !$("automation-enabled").checked;
  if (occupancySettings) occupancySettings.hidden = !$("occupancy-enabled").checked;
}

function sliderDecimalPlaces(step) {
  const decimal = String(step).split(".")[1];
  return decimal ? decimal.length : 0;
}

function invertedSliderValue(input, value) {
  const inverted = Number(input.min) + Number(input.max) - Number(value);
  return inverted.toFixed(sliderDecimalPlaces(input.step));
}

function modeSettingValue(input) {
  let value = Number(input.dataset.inverse === "true" ? invertedSliderValue(input, input.value) : input.value);
  if (input.dataset.displayScale) {
    value = value * Number(input.dataset.displayScale) + Number(input.dataset.displayOffset || 0);
    const decimals = Number(input.dataset.displayDecimals || 0);
    value = decimals ? value.toFixed(decimals) : Math.round(value);
  } else if (Number.isNaN(value)) {
    value = input.value;
  }
  return input.dataset.unit ? `${value} ${input.dataset.unit}` : value;
}

function updateModeSettingOutput(input) {
  const output = input.closest("label")?.querySelector(".setting-value");
  if (output) output.textContent = modeSettingValue(input);
}

function createModeSetting(field, value) {
  const label = document.createElement("label");
  const isBoolean = field.type === "boolean";
  if (field.show_value) {
    const title = document.createElement("span");
    title.textContent = field.label;
    const output = document.createElement("output");
    output.className = "setting-value";
    title.append(output);
    label.append(title);
  } else if (isBoolean) {
    label.className = "setting-toggle";
    const title = document.createElement("span");
    title.className = "setting-label";
    title.textContent = field.label;
    label.append(title);
  } else {
    label.textContent = field.label;
  }
  const input = document.createElement(field.type === "select" ? "select" : "input");
  input.dataset.modeSetting = field.key;
  input.dataset.unit = field.unit || "";
  if (field.display_scale !== undefined) input.dataset.displayScale = field.display_scale;
  if (field.display_offset !== undefined) input.dataset.displayOffset = field.display_offset;
  if (field.display_decimals !== undefined) input.dataset.displayDecimals = field.display_decimals;
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
    if (field.inverse) input.dataset.inverse = "true";
  }
  input.value = field.inverse ? invertedSliderValue(input, value) : value;
  if (isBoolean) {
    input.checked = Boolean(value);
    input.classList.add("pill-switch");
  }

  label.append(input);
  updateModeSettingOutput(input);
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
    const isRelevant = Array.isArray(requiredMode) ? requiredMode.includes(colorMode.value) : colorMode.value === requiredMode;
    label.style.display = isRelevant ? "" : "none";
    label.setAttribute("aria-hidden", String(!isRelevant));
  }
}

function settingsPayload(settingInputs) {
  return Object.fromEntries(Object.entries(settingInputs).map(([key, input]) => [key, input.type === "checkbox" ? input.checked : input.dataset.inverse === "true" ? invertedSliderValue(input, input.value) : input.value]));
}

function applyActiveModeSettings(mode, settingInputs) {
  if (latestState?.mode !== mode.id) return;
  modeSettingsRequest = modeSettingsRequest.catch(() => {}).then(async () => {
    if (latestState?.mode !== mode.id) return;
    try {
      renderState(await api("/api/mode/settings", {method: "PATCH", body: JSON.stringify(settingsPayload(settingInputs))}));
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

function bindLiveModeSettings(mode, settingInputs) {
  const applyNow = () => {
    clearTimeout(modeSettingsTimer);
    modeSettingsTimer = null;
    applyActiveModeSettings(mode, settingInputs);
  };
  for (const input of Object.values(settingInputs)) {
    input.addEventListener("input", () => {
      updateModeSettingOutput(input);
      clearTimeout(modeSettingsTimer);
      modeSettingsTimer = setTimeout(applyNow, 125);
    });
    input.addEventListener("change", () => {
      updateModeSettingOutput(input);
      applyNow();
    });
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
  description.textContent = mode.requires_asset ? "Choose a bundled image or GIF below." : mode.settings_schema && Object.keys(mode.settings_schema).length ? "Changes apply immediately while this mode is running." : "Mode-specific controls will appear here as they are added.";
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
    if (definition.hidden) continue;
    const field = {...definition, key};
    const value = latestState?.mode === mode.id ? (latestState.mode_options?.[key] ?? field.default) : field.default;
    const control = createModeSetting(field, value);
    settingInputs[key] = control.input;
    if (mode.id === "spectrum" && key === "auto_gain") continue;
    settings.append(control.element);
  }
  if (mode.id === "spectrum" && settingInputs.auto_gain) {
    const gainLabel = settingInputs.gain_db.closest("label");
    const autoInput = settingInputs.auto_gain;
    const gainText = [...gainLabel.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    const gainTitle = document.createElement("span");
    gainTitle.textContent = gainText.textContent;
    Object.assign(gainTitle.style, {display: "flex", alignItems: "center", gap: "10px"});
    gainLabel.replaceChild(gainTitle, gainText);
    const autoToggle = document.createElement("span");
    autoToggle.textContent = "Automatic";
    Object.assign(autoToggle.style, {display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap", fontSize: "0.9em"});
    autoInput.setAttribute("aria-label", "Automatic gain");
    autoInput.title = mode.settings_schema.auto_gain.help;
    autoToggle.prepend(autoInput);
    gainTitle.append(autoToggle);
    const syncAutoGain = () => {
      settingInputs.gain_db.disabled = autoInput.checked;
      settingInputs.gain_db.closest("label").classList.toggle("is-disabled", autoInput.checked);
      settingInputs.gain_db.closest("label").style.opacity = autoInput.checked ? "0.5" : "";
    };
    syncAutoGain();
    autoInput.addEventListener("change", syncAutoGain);
  }

  const colorModeControls = {
    life: {modeKey: "alive_color_mode", relevantModes: {alive_fixed_color: "fixed", rainbow_cycle_speed: "rainbow_cycle", rainbow_gradient_speed: "rainbow_gradient"}},
    rain: {modeKey: "rain_color_mode", relevantModes: {rain_fixed_color: "fixed", rainbow_cycle_speed: "rainbow_cycle", rainbow_gradient_speed: "rainbow_gradient"}},
    stars: {modeKey: "star_color_mode", relevantModes: {star_fixed_color: "fixed", rainbow_cycle_speed: "rainbow_cycle", rainbow_gradient_speed: "rainbow_gradient"}},
    spectrum: {modeKey: "palette", relevantModes: {fixed_color: "fixed"}},
    perlin: {modeKey: "palette", relevantModes: {custom_start_color: "custom", custom_mid_color: "custom", custom_end_color: "custom"}},
    fireplace: {modeKey: "palette", relevantModes: {custom_shadow_color: "custom", custom_mid_color: "custom", custom_highlight_color: "custom"}},
    thermal: {modeKey: "palette", relevantModes: {custom_cold_color: "custom", custom_mid_color: "custom", custom_hot_color: "custom"}},
  };
  const colorControls = colorModeControls[mode.id];
  if (colorControls) {
    syncColorModeControls(settingInputs, colorControls.modeKey, colorControls.relevantModes);
    settingInputs[colorControls.modeKey].addEventListener("change", () => syncColorModeControls(settingInputs, colorControls.modeKey, colorControls.relevantModes));
  }
  if (mode.id === "thermal") {
    const exposureMode = settingInputs.exposure_mode;
    const exposureFields = {exposure_smoothing: ["auto", "percentile"], min_temperature: "fixed", max_temperature: "fixed", low_percentile: "percentile", high_percentile: "percentile"};
    syncColorModeControls(settingInputs, "exposure_mode", exposureFields);
    exposureMode.addEventListener("change", () => syncColorModeControls(settingInputs, "exposure_mode", exposureFields));
  }

  bindLiveModeSettings(mode, settingInputs);
  card.append(settings);
  const launch = document.createElement("button");
  launch.textContent = mode.id === "off" ? "Turn display off" : `Start ${mode.name}`;
  launch.onclick = async () => {
    try {
      if (mode.requires_asset && !assetSelect.value) throw new Error("Add an image or GIF to the res directory first.");
      renderState(await api("/api/mode", {method: "POST", body: JSON.stringify({mode: mode.id, asset_id: assetSelect?.value, settings: settingsPayload(settingInputs)})}));
    } catch (error) { setStatus(error.message, true); }
  };
  card.append(launch);
  return card;
}

function renderSelectedMode() {
  clearTimeout(modeSettingsTimer);
  modeSettingsTimer = null;
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
  $("automation-enabled").addEventListener("change", syncAutomationSettingsVisibility);
  $("occupancy-enabled").addEventListener("change", syncAutomationSettingsVisibility);
  $("save-automation").onclick = async () => {
    try {
      const automation = {enabled: $("automation-enabled").checked, sleep_lux: number("sleep-lux"), wake_lux: number("wake-lux"), sleep_dwell_seconds: number("sleep-dwell"), wake_dwell_seconds: number("wake-dwell"), poll_seconds: number("poll-seconds"), min_brightness: number("min-brightness"), max_lux: number("max-lux"), manual_override_policy: $("override-policy").value, manual_override_minutes: number("override-minutes")};
      const state = await api("/api/settings", {method: "PATCH", body: JSON.stringify({automation})});
      populateAutomationForm(state.automation);
      renderState(state);
    } catch (error) { setStatus(error.message, true); }
  };
  $("save-occupancy").onclick = async () => {
    try {
      const occupancy = {enabled: $("occupancy-enabled").checked, temperature_delta_f: number("occupancy-delta"), minimum_region_size: number("occupancy-region"), absence_dwell_seconds: number("occupancy-absence-dwell"), presence_dwell_seconds: number("occupancy-presence-dwell"), startup_calibration_seconds: number("occupancy-calibration"), edge_exclusion: number("occupancy-edge")};
      const state = await api("/api/settings", {method: "PATCH", body: JSON.stringify({occupancy})});
      populateAutomationForm(state.automation, state.occupancy);
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
