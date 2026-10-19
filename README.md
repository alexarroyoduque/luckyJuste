# luckyJuste

In the original *Castlevania: Harmony of Dissonance* (Game Boy Advance), LUCK has no effect on either mechanic, making Luck-boosting equipment largely ineffective.

**luckyJuste** fixes this by making Luck gained from equipment increase both normal and rare item drop rates, as well as critical hit chances. Only equipment bonuses count; Luck naturally gained through leveling is excluded.

[Drop calculator](https://harmony-of-dissonance-drop.web.app).

## How to apply

There are two patches, you can use one of them or both.

1. Get a USA ROM of *Castlevania: Harmony of Dissonance*.
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

- Juste's natural Luck from leveling is excluded:
- A random roll [0-1023] is compared against `DROP_BASE + EQUIPMENT_LUCKY`:
- `EQUIPMENT_LUCKY = (LCK_ATTR - nivel - 24)*0,5`
- If the random roll is lower than this threshold, the item drops.
- The patch does **not** modify the Rare Ring hidden bonus.
- The patch does **not** modify the Rare Ghost spawn routine, which depends on total Luck.

#### Why is the multiplier set to 0.5?

For example, consider an item with a base drop threshold of 64, corresponding to a 6.25% drop chance. The game generates a random number between 0 and 1023. If the result is lower than 64, the item drops.

With the Rare Ring equipped, the threshold increases to 96, raising the drop chance to 9.375% (+3.125%).

The 0.5 multiplier was chosen to make equipment-based Luck meaningful while preserving the value of the Rare Ring. For example, 32 points of equipment Luck increase the threshold by 16, raising the drop chance from 6.25% to 7.8125%.

This **provides a balanced progression**: equipment Luck improves drop rates without making the Rare Ring obsolete. Both bonuses also stack.

## luckyJuste-critical

### What does it change?
- Juste's natural Luck from leveling is excluded:
- `BASE_CHANGE = 4096/65536 = 6.25%` (similar to the original game)
- `EQUIPMENT_LUCKY = (LCK_ATTR - nivel - 24)*(4,69/30)`
- A random roll [0-65535] is compared against `BASE_CHANGE + EQUIPMENT_LUCKY`:
- If the random roll is lower than this threshold, the hit is critical.
- As in the original game, if Juste has the **Platinum Tip** equipped and the first critical hit check fails, a second random roll is performed with a **1/64 (1.5625%)** chance of landing a critical hit.

#### Why is the multiplier (4,69/30)=0.156333?
**Because in the original game there is hidden behavior** in how "Lucky Charm" and "Lucky Ring" increase critical chance. Through calculations, "Lucky Charm" which grants +10 luck and "Lucky Ring" which grants +20 luck achieve a hidden critical rate of **7168/65536 = 10.94% (+4,69)** in the game. The **0.156333** factor respects that hidden scaling but with the new system affects any item that grants luck.


## Credits

* AlexArroyoDuque
* -SuXei999- - testing and qualiy
* [Marc Robledo — RomPatcher.js](https://github.com/marcrobledo/RomPatcher.js)
* [LagoLunatic — DSVania Editor](https://www.romhacking.net/community/4318)
* [Zach Keene — Level stats](https://gamefaqs.gamespot.com/gba/554981-castlevania-harmony-of-dissonance/faqs/17440)
* [Romhacking.net](https://www.romhacking.net)
