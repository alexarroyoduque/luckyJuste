# luckyJuste

A patch that makes Luck (LCK) affect enemy item drop rates and critical hit chances in *Castlevania: Harmony of Dissonance* (Game Boy Advance).

In the original game, LCK has no effect on either mechanic, making Luck-boosting equipment largely ineffective.

**luckyJuste** fixes this by making LCK gained from equipment increase both normal and rare item drop rates, as well as critical hit chances. Only equipment bonuses count; LCK naturally gained through leveling is excluded.

[Drop calculator](https://harmony-of-dissonance-drop.web.app/).

## How to apply

There are two patches, you can use one of them or both.

1. Get a clean USA ROM of *Castlevania: Harmony of Dissonance*.
2. [Download luckyJuste-drop.ips](./luckyJuste-drop.ips).
3. [Download luckyJuste-critical.ips](./luckyJuste-critical.ips).
4. [Apply the IPS patch](https://www.romhacking.net/patch/).

```text
Database match: Castlevania - Harmony of Dissonance (USA)
Database: No-Intro: Game Boy Advance (v. 20210227-023848)
File/ROM SHA-1: B90DA0D9BE0B3A0893CD9E2C399056BCF9579E21
File/ROM CRC32: 88C1B562
```

## luckyJuste-drop

### What does it change?

In the original game, enemy drop rates use fixed values. The Rare Ring is handled as a special case, providing a hidden `+16` bonus to rare drops and `+32` to normal drops.

With luckyJuste, **LCK gained from equipment increases both normal and rare item drop rates**.

Juste's natural LCK from leveling is excluded:

```text
EQUIPMENT_LUCKY = LCK_ATTR - level - 24
```

Luck equipment receives an efficient approximation of a **1× scaling bonus**:

The final drop check becomes:

```text
RNG < BASE_DROP_RATE + EXTRA_DROP
```

The game uses an RNG range of `0–1023`, so each point added to the drop threshold represents `1/1024` of the probability space. As in the original game, the rare item is checked first. If it drops, the normal item is not evaluated.

#### Rare Ring

The **Rare Ring now grants +22 LCK**, visible in Juste's stats.

This bonus applies to both normal and rare items, replacing the original hidden Rare Ring behavior with the global LCK system.

#### Rare Ghost

The patch does **not** modify the Rare Ghost routine.

Rare Ghost already uses LCK in the original game, so the Rare Ring's new `+22 LCK` can also improve its spawn rolls when it crosses the relevant LCK thresholds.

## luckyJuste-critical

### What does it change?

`CRITICAL_CHANCE = 6.25 + EQUIPMENT_LUCKY*0,15 + LEVEL_BONUS`

- The base chance is 4096/65536 = 6.25%, similar to the original game.
- The luck of the equip increases the critical chance.
- Each 10 level difference between Juste and its enemy adds 1% to the critical chance, up to a maximum of 4%.
- Only one roll is performed. En el juego original si Juste equipa "Platinum Tip" se realiza una segunda tirada aleatoria de 1/64 = 1,56%.
- Por qué el factor de escalado es 0,15? Porque en el juego original hay un comportamiento oculto en el "Lucky Charm" and "Lucky Ring" increment critcal change. Haciendo cálculos "Lucky Charm" que suma 10 de suerte y "Lucky Ring" que suma 20, alcanzan da una tasa de crítico interna en el juego de 7168/65536 = 10,94%. El factor 0,15 respeta ese escalado oculto pero con el nuevo sistema afecta a cualquier objeto que sume suerte.



## Credits

* AlexArroyoDuque
* -SuXei999- - testing and qualiy
* [Marc Robledo — RomPatcher.js](https://github.com/marcrobledo/RomPatcher.js)
* [LagoLunatic — DSVania Editor](https://www.romhacking.net/community/4318)
* [Zach Keene — Level stats](https://gamefaqs.gamespot.com/gba/554981-castlevania-harmony-of-dissonance/faqs/17440)
* [Romhacking.net](https://www.romhacking.net)
