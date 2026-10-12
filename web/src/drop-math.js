// Probabilidad base sobre 1024 según la mecánica de drops de Harmony of Dissonance
export const DROP_BASE = 1024;
export const RARE_RING_COMMON_BONUS = 32;
export const RARE_RING_RARE_BONUS = 16;
// Multiplicador del parche luckyJuste: EXTRA_DROP = floor(EQUIPMENT_LUCK * RATIO)
export const DEFAULT_RATIO = 1.0;
// Probabilidad de cada tirada para la aparición de Rare Ghost y el tope efectivo del juego
export const RARE_GHOST_ROLL_CHANCE = 1 / 64;
export const RARE_GHOST_MAX_CHANCE = 0.25;

export function hexToDecimal(hex) {
  return parseInt(hex, 16);
}

export function toPercent(value) {
  return `${((value / DROP_BASE) * 100).toFixed(2)}%`;
}

export function toDeltaPercent(deltaDecimal) {
  if (!deltaDecimal) return '';
  const sign = deltaDecimal > 0 ? '+' : '-';
  return `${sign}${((Math.abs(deltaDecimal) / DROP_BASE) * 100).toFixed(2)}%`;
}

// A partir de 80 LCK se suma una tirada extra de 1/64 cada 10 puntos de suerte
export function rareGhostRolls(luck) {
  return 1 + Math.max(0, Math.floor((luck - 70) / 10));
}

export function rareGhostChance(luck) {
  const rolls = rareGhostRolls(luck);
  const chance = 1 - Math.pow(1 - RARE_GHOST_ROLL_CHANCE, rolls);
  return Math.min(chance, RARE_GHOST_MAX_CHANCE);
}
