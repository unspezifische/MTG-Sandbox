import React, { useState } from "react";

const SETTINGS_KEY = "mtg-sandbox-preferences";
const DEFAULTS = {
  defaultFormat: "commander",
  defaultSleeve: "classic",
  confirmConcede: true,
  showPlacementGuides: true,
  animateCards: true,
};

function loadPreferences() {
  try {
    return { ...DEFAULTS, ...JSON.parse(window.localStorage.getItem(SETTINGS_KEY) || "{}") };
  } catch {
    return DEFAULTS;
  }
}

export default function SettingsPage() {
  const [settings, setSettings] = useState(loadPreferences);
  const [saved, setSaved] = useState(false);
  const update = (key, value) => {
    setSaved(false);
    setSettings((previous) => ({ ...previous, [key]: value }));
  };
  const save = () => {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    setSaved(true);
  };

  return (
    <div className="page-shell">
      <section className="page-card settings-page">
        <div className="eyebrow">Personal preferences</div>
        <h1>Settings</h1>
        <div className="settings-grid">
          <label><span>Default deck format</span><select value={settings.defaultFormat} onChange={(event) => update("defaultFormat", event.target.value)}><option value="commander">Commander</option><option value="standard">Standard</option><option value="modern">Modern</option><option value="none">No format</option></select></label>
          <label><span>Default sleeve</span><select value={settings.defaultSleeve} onChange={(event) => update("defaultSleeve", event.target.value)}><option value="classic">Classic MTG</option><option value="obsidian-matte">Obsidian Matte</option><option value="arcane-swirl">Arcane Swirl</option><option value="dragon-scale">Dragon Scale</option></select></label>
          <label className="settings-toggle"><input type="checkbox" checked={settings.confirmConcede} onChange={(event) => update("confirmConcede", event.target.checked)} /><span>Confirm before conceding</span></label>
          <label className="settings-toggle"><input type="checkbox" checked={settings.showPlacementGuides} onChange={(event) => update("showPlacementGuides", event.target.checked)} /><span>Show battlefield placement guides</span></label>
          <label className="settings-toggle"><input type="checkbox" checked={settings.animateCards} onChange={(event) => update("animateCards", event.target.checked)} /><span>Animate newly drawn cards</span></label>
        </div>
        <div className="settings-actions"><button type="button" className="button-primary" onClick={save}>Save settings</button>{saved ? <span>Saved locally for this browser.</span> : null}</div>
      </section>
    </div>
  );
}
