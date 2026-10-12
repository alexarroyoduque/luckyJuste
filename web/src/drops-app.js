import { LitElement, html, unsafeCSS } from 'lit';
import drops from '../drops.json';
import styles from './drops-app.css?inline';
import {
  DEFAULT_RATIO,
  RARE_RING_COMMON_BONUS,
  RARE_RING_RARE_BONUS,
  hexToDecimal,
  toPercent,
  toDeltaPercent,
  rareGhostRolls,
  rareGhostChance,
} from './drop-math.js';

// \u2212 (minus sign) aparece en algunos nombres y debe normalizarse a un guion normal para la URL
function monsterWikiUrl(name) {
  const slug = name.replace(/\s+/g, '_').replace(/\u2212/g, '-');
  return `https://castlevania.fandom.com/wiki/${slug}`;
}

export class DropsApp extends LitElement {
  static properties = {
    filterText: { state: true },
    showRareRing: { state: true },
    showRareRingInLuckyJuste: { state: true },
    extraLuck: { state: true },
    showInfo: { state: true },
    showDelta: { state: true },
    showRareGhost: { state: true },
    rareGhostLuck: { state: true },
  };

  static styles = unsafeCSS(styles);

  constructor() {
    super();
    this.filterText = '';
    this.showRareRing = false;
    this.showRareRingInLuckyJuste = false;
    this.extraLuck = 0;
    this.showInfo = false;
    this.showDelta = false;
    this.showRareGhost = false;
    this.rareGhostLuck = 0;
  }

  onFilterInput(event) {
    this.filterText = event.target.value;
  }

  onRareRingToggle(event) {
    this.showRareRing = event.target.checked;
  }

  onExtraLuckInput(event) {
    this.extraLuck = Math.max(0, Number(event.target.value) || 0);
  }

  onRareRingInLuckyJusteToggle(event) {
    this.showRareRingInLuckyJuste = event.target.checked;
  }

  onInfoToggle() {
    this.showInfo = !this.showInfo;
  }

  onDeltaToggle(event) {
    this.showDelta = event.target.checked;
  }

  onRareGhostToggle() {
    this.showRareGhost = !this.showRareGhost;
  }

  onRareGhostLuckInput(event) {
    this.rareGhostLuck = Math.max(0, Number(event.target.value) || 0);
  }

  renderHeader() {
    return html`
      <div class="page-header">
        <h1>Drop Calculator - Harmony of Dissonance</h1>
        <span class="credit"
          >AlexArroyoDuque
          <a href="https://www.patreon.com/cw/AlexArroyoDuque" target="_blank" rel="noopener"
            >Patreon</a
          ></span
        >
      </div>
    `;
  }

  renderControls(extraDrop) {
    return html`
      <div class="controls">
        <div class="filter-group">
          <input
            type="search"
            placeholder="Filter by monster or item..."
            .value=${this.filterText}
            @input=${this.onFilterInput}
          />
          <label class="rare-ring-label">
            <input
              type="checkbox"
              .checked=${this.showRareRing}
              @change=${this.onRareRingToggle}
            />
            Rare Ring in original game
          </label>
          <button class="rare-ghost-button" type="button" @click=${this.onRareGhostToggle}>
            RARE GHOST CHANCE
          </button>
        </div>
        <div class="separator"></div>
        <div class="lucky-juste-group">
          <span class="lucky-juste-title">luckyJuste</span>
          <button class="info-button" type="button" @click=${this.onInfoToggle}>SHOW INFO</button>
          <label>
            EXTRA_DROP
            <input class="lucky-box" type="number" value=${extraDrop} readonly />
          </label>
          <label>
            ratio
            <input class="lucky-box ratio" type="number" value=${DEFAULT_RATIO} readonly />
          </label>
          <label>
            EQUIPMENT_LUCK
            <input
              class="lucky-box"
              type="number"
              min="0"
              .value=${String(this.extraLuck)}
              @input=${this.onExtraLuckInput}
            />
          </label>
          <label class="rare-ring-juste-label">
            <input type="checkbox" .checked=${this.showRareRingInLuckyJuste} @change=${this.onRareRingInLuckyJusteToggle} />
            <span class="rare-ring-juste-text">Rare Ring in luckyJuste</span>
          </label>
          <label>
            <input type="checkbox" .checked=${this.showDelta} @change=${this.onDeltaToggle} />
            &Delta;
          </label>
          <div class="formulas">
            <span class="formula">EXTRA_DROP = (TOTAL_LUCK - level - 24)&times;ratio</span>
            <span class="formula">TOTAL_LUCK = BASE_LUCK + EQUIPMENT_LUCK</span>
          </div>
        </div>
      </div>
    `;
  }

  renderInfoPanel() {
    if (!this.showInfo) return '';
    return html`
      <div class="info-panel">
        In Harmony of Dissonance, Luck only affects the chance of encountering the Rare Ghost enemy. Item drop chances are calculated out of 1024, and the only way to increase them is with the Rare Ring, which adds 32/1024 to the drop chance of common items and 16/1024 to that of rare items.

        The patch does not modify the Rare Ring hidden bonus. With luckyJuste, all the extra Luck granted by equipped items increases the drop rate. Juste starts at level 1 with 25 Luck and gains one point of Luck per level up to level 89.
      </div>
    `;
  }

  renderRareGhostPanel() {
    if (!this.showRareGhost) return '';
    return html`
      <div class="rare-ghost-panel">
        <div class="rare-ghost-title">RARE GHOST</div>
        <div class="rare-ghost-controls">
          <label>
            TOTAL_LUCK
            <input
              class="lucky-box"
              type="number"
              min="0"
              .value=${String(this.rareGhostLuck)}
              @input=${this.onRareGhostLuckInput}
            />
          </label>
          <label>
            Chance
            <input
              class="lucky-box"
              type="text"
              value=${`${(rareGhostChance(this.rareGhostLuck) * 100).toFixed(2)}%`}
              readonly
            />
          </label>
          <label>
            Rolls
            <input
              class="lucky-box"
              type="number"
              value=${rareGhostRolls(this.rareGhostLuck)}
              readonly
            />
          </label>
        </div>
        <ul>
          <li>At level 1, Juste has 25 Luck and gains 1 Luck per level (up to 89).</li>
          <li>LUCK 0–79: 1/64 ≈ 1.56% appearance chance.</li>
          <li>From 80 LUCK onward, every +10 LUCK adds another 1/64 roll.</li>
          <li>Examples: 80 LUCK → 3.10%, 90 → 4.61%, 100 → 6.11%.</li>
          <li>At 999 LUCK, it caps at around 25% effective maximum.</li>
        </ul>
      </div>
    `;
  }

  renderDropRow({ monster, id }, extraDrop) {
    const commonDecimal = hexToDecimal(monster.drop.common.HEX);
    const rareDecimal = hexToDecimal(monster.drop.rare.HEX);
    // A decimal value of 0 means there's no item, so the Rare Ring bonus doesn't apply
    const commonWithRing = commonDecimal === 0 ? 0 : commonDecimal + RARE_RING_COMMON_BONUS;
    const rareWithRing = rareDecimal === 0 ? 0 : rareDecimal + RARE_RING_RARE_BONUS;
    // Same rule applies to the luckyJuste EXTRA_DROP bonus
    let commonWithExtraDrop = commonDecimal === 0 ? 0 : commonDecimal + extraDrop;
    let rareWithExtraDrop = rareDecimal === 0 ? 0 : rareDecimal + extraDrop;
    // Add Rare Ring bonus to luckyJuste if checkbox is active
    if (this.showRareRingInLuckyJuste) {
      commonWithExtraDrop = commonDecimal === 0 ? 0 : commonWithExtraDrop + RARE_RING_COMMON_BONUS;
      rareWithExtraDrop = rareDecimal === 0 ? 0 : rareWithExtraDrop + RARE_RING_RARE_BONUS;
    }
    const commonDisplayed = this.showRareRing ? commonWithRing : commonDecimal;
    const rareDisplayed = this.showRareRing ? rareWithRing : rareDecimal;
    const commonDelta = commonWithExtraDrop - commonDisplayed;
    const rareDelta = rareWithExtraDrop - rareDisplayed;

    const renderRate = (value, delta = 0, isRareRingActive = false) => html`
      <span class="rate-value">
        <span class="rate-percent">
          ${toPercent(value)}
          ${this.showDelta && delta !== 0
            ? html`<span class="delta ${delta > 0 ? 'positive' : 'negative'}">${toDeltaPercent(delta)}</span>`
            : ''}
        </span>
        <span class="rate-fraction">
          <span class=${isRareRingActive ? 'rare-ring-active' : ''}>${value}</span>/1024
        </span>
      </span>
    `;

    return html`
      <tr>
        <td>${id + 1}</td>
        <td>
          <a href=${monsterWikiUrl(monster.name)} target="_blank" rel="noopener">${monster.name}</a>
        </td>
        <td>${monster.drop.common.item ?? '-'}</td>
        <td>${monster.drop.rare.item ?? '-'}</td>
        <td class=${this.showRareRing ? 'rare-ring-active' : ''}>
          ${renderRate(commonDisplayed, 0, this.showRareRing)}
        </td>
        <td class=${this.showRareRingInLuckyJuste ? 'rare-ring-juste-active gold' : 'gold'}>
          ${renderRate(commonWithExtraDrop, commonDelta, this.showRareRingInLuckyJuste)}
        </td>
        <td class=${this.showRareRing ? 'rare-ring-active' : ''}>
          ${renderRate(rareDisplayed, 0, this.showRareRing)}
        </td>
        <td class=${this.showRareRingInLuckyJuste ? 'rare-ring-juste-active gold' : 'gold'}>
          ${renderRate(rareWithExtraDrop, rareDelta, this.showRareRingInLuckyJuste)}
        </td>
      </tr>
    `;
  }

  renderTable(filteredDrops, extraDrop) {
    return html`
      <table>
        <thead>
          <tr>
            <th rowspan="2">#</th>
            <th rowspan="2">Monster</th>
            <th rowspan="2">Common</th>
            <th rowspan="2">Rare</th>
            <th colspan="2">Common Rate</th>
            <th colspan="2">Rare Rate</th>
          </tr>
          <tr>
            <th>original</th>
            <th class="gold">luckyJuste</th>
            <th>original</th>
            <th class="gold">luckyJuste</th>
          </tr>
        </thead>
        <tbody>
          ${filteredDrops.map((entry) => this.renderDropRow(entry, extraDrop))}
        </tbody>
      </table>
    `;
  }

  render() {
    const query = this.filterText.trim().toLowerCase();
    const extraDrop = Math.trunc(this.extraLuck * DEFAULT_RATIO);
    const filteredDrops = drops
      .map((monster, id) => ({ monster, id }))
      .filter(({ monster }) => {
        if (!query) return true;
        const haystack = [monster.name, monster.drop.common.item, monster.drop.rare.item]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return haystack.includes(query);
      });

    return html`
      ${this.renderHeader()}
      ${this.renderControls(extraDrop)}
      ${this.renderInfoPanel()}
      ${this.renderRareGhostPanel()}
      ${this.renderTable(filteredDrops, extraDrop)}
    `;
  }
}

customElements.define('drops-app', DropsApp);
