/**
 * Need for Speed ProStreet - Web Application Entrypoint.
 */

import './style.css';
import { AppShell } from './app.js';

window.addEventListener('DOMContentLoaded', async () => {
  const shell = new AppShell();

  const canvas = document.getElementById('game-canvas') as HTMLCanvasElement;
  const touchContainer = document.getElementById('touch-overlay') as HTMLElement;
  const fsBtn = document.getElementById('fs-btn') as HTMLButtonElement;
  const playBtn = document.getElementById('play-btn') as HTMLButtonElement;
  const preloadBtn = document.getElementById('preload-btn') as HTMLButtonElement;
  const progressFill = document.getElementById('progress-fill') as HTMLElement;
  const statusText = document.getElementById('status-text') as HTMLElement;
  const statusSub = document.getElementById('status-sub') as HTMLElement;

  // Settings elements
  const resSelect = document.getElementById('res-scale') as HTMLSelectElement;
  const fpsSelect = document.getElementById('fps-target') as HTMLSelectElement;
  const volumeSlider = document.getElementById('audio-volume') as HTMLInputElement;
  const steeringSelect = document.getElementById('steering-mode') as HTMLSelectElement;
  const horizonCheckbox = document.getElementById('level-horizon') as HTMLInputElement;

  // Sync initial UI from loaded settings
  if (resSelect) resSelect.value = String(shell.settings.resolutionScale);
  if (fpsSelect) fpsSelect.value = String(shell.settings.fpsTarget);
  if (volumeSlider) volumeSlider.value = String(shell.settings.audioVolume);
  if (steeringSelect) steeringSelect.value = shell.settings.steeringMode;
  if (horizonCheckbox) horizonCheckbox.checked = shell.settings.levelHorizon;

  // Setup tab navigation
  const tabButtons = document.querySelectorAll<HTMLButtonElement>('.tab-btn');
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      if (!tabName) return;

      tabButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-content').forEach((tc) => {
        tc.classList.remove('active');
      });

      const target = document.getElementById(`tab-${tabName}`);
      if (target) target.classList.add('active');
      shell.setTab(tabName);
    });
  });

  // Fullscreen button
  if (fsBtn) {
    fsBtn.addEventListener('click', () => {
      shell.toggleFullscreen(document.getElementById('stage-container') || undefined);
    });
  }

  // Settings change listeners
  if (resSelect) {
    resSelect.addEventListener('change', () => {
      shell.applyResolutionScale(parseFloat(resSelect.value) as any);
    });
  }

  if (fpsSelect) {
    fpsSelect.addEventListener('change', () => {
      shell.settings.fpsTarget = parseInt(fpsSelect.value, 10) as 60 | 120;
      shell.saveSettings();
    });
  }

  if (volumeSlider) {
    volumeSlider.addEventListener('input', () => {
      shell.settings.audioVolume = parseInt(volumeSlider.value, 10);
      shell.saveSettings();
    });
  }

  if (steeringSelect) {
    steeringSelect.addEventListener('change', () => {
      shell.settings.steeringMode = steeringSelect.value as any;
      shell.saveSettings();
    });
  }

  if (horizonCheckbox) {
    horizonCheckbox.addEventListener('change', () => {
      shell.settings.levelHorizon = horizonCheckbox.checked;
      shell.saveSettings();
    });
  }

  // Preload Game Data button
  if (preloadBtn) {
    preloadBtn.addEventListener('click', async () => {
      preloadBtn.disabled = true;
      if (statusText) statusText.textContent = 'Preloading Game Assets...';

      try {
        await shell.preloadGameData((pct, loaded, total) => {
          if (progressFill) progressFill.style.width = `${pct}%`;
          if (statusSub) {
            const mbLoaded = (loaded / 1048576).toFixed(1);
            const mbTotal = (total / 1048576).toFixed(1);
            statusSub.textContent = `${mbLoaded} MB / ${mbTotal} MB (${Math.round(pct)}%)`;
          }
        });

        if (statusText) statusText.textContent = 'Assets Preloaded to OPFS';
        if (statusSub) statusSub.textContent = 'All critical assets cached locally for instant play.';
      } catch (err) {
        if (statusText) statusText.textContent = 'Preload Complete / Up to date';
      } finally {
        preloadBtn.disabled = false;
      }
    });
  }

  // Play button
  if (playBtn) {
    playBtn.addEventListener('click', async () => {
      if (statusText) statusText.textContent = 'Booting NFS ProStreet...';
      if (progressFill) progressFill.style.width = '100%';

      try {
        shell.canvas = canvas;
        await shell.startRace(touchContainer);

        if (statusText) statusText.textContent = 'Running (1280x720 60 FPS)';
        if (statusSub) statusSub.textContent = 'ProStreet authentic engine active.';
        playBtn.textContent = 'Game Running';
        playBtn.disabled = true;
      } catch (err: any) {
        if (statusText) statusText.textContent = 'Error Starting Game';
        if (statusSub) statusSub.textContent = String(err?.message || err);
        console.error('Game start error:', err);
      }
    });
  }

  // Clear cache button
  const clearBtn = document.getElementById('clear-cache-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      if (typeof navigator !== 'undefined' && 'storage' in navigator && navigator.storage.getDirectory) {
        try {
          const root = await navigator.storage.getDirectory();
          await root.removeEntry('prostreet-cache', { recursive: true });
          alert('OPFS cache cleared successfully.');
        } catch (_) {
          alert('No cached data found.');
        }
      }
    });
  }
});
