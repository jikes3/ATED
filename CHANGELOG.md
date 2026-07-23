# Changelog

Všechny významné změny projektu budou uvedeny v tomto souboru.

## [0.2.0] – ATED Historian

### Přidáno
- přejmenování interního loggeru na `AtedHistorian`,
- obnovení dnešního počtu záznamů po restartu Home Assistantu,
- čas posledního kompletního snapshotu,
- souhrn kvality dat v každém snapshotu,
- senzor kvality dat v procentech,
- senzor počtu sledovaných entit,
- senzor velikosti archivu,
- senzor stavu Historianu a chyb zápisu,
- push aktualizace diagnostických senzorů bez zbytečného pollingu,
- opravené odkazy a codeowner v `manifest.json`,
- schema JSONL zvýšeno na verzi 2.

### Kompatibilita historie
Staré záznamy se nepřepisují. Soubory mohou bezpečně obsahovat záznamy schema verze 1 i 2.



## [0.1.0] – 2026-07-22

### Přidáno

- první read-only logger ATED,
- ukládání změn sledovaných entit do denních JSONL souborů,
- pravidelné snapshoty sledovaných entit,
- zachování syrových a normalizovaných hodnot,
- označení vadné vstupní teploty bazénového TČ −22 °C jako `invalid`,
- konfigurační a options flow,
- základní diagnostické senzory,
- HACS metadata a GitHub Actions.
