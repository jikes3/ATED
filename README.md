# ATED Core

ATED (Asistent toku energie domu) je připravovaný otevřený asistent pro
Home Assistant. Tato první vývojová verze je čistě **Read Only** a jejím cílem
je začít bezpečně archivovat data pro budoucí analýzu, Digital Twin a Decision
Engine.

## Funkce verze 0.1.0

- záznam každé změny vybraných entit,
- pravidelný snapshot všech vybraných entit,
- denní append-only soubory JSONL,
- syrová i normalizovaná hodnota a jednotka,
- kvalita dat `verified`, `invalid` nebo `missing`,
- vadná vstupní teplota bazénového TČ −22 °C je zachována jako raw, ale není
  použita jako normalizovaná hodnota,
- výběr entit a intervalu přes UI,
- diagnostické senzory loggeru.

## Instalace přes HACS

Repozitář je zatím nutné přidat jako vlastní repozitář HACS. Podrobný návod je
v [SETUP_GITHUB_HACS.md](SETUP_GITHUB_HACS.md).

Po instalaci a restartu přidejte integraci přes:

**Nastavení → Zařízení a služby → Přidat integraci → ATED Core**

## Ukládání dat

Data jsou ukládána do:

```text
/config/ated_data/ated-YYYY-MM-DD.jsonl
```

Každý řádek je samostatný verzovaný JSON záznam. Původní historická data se
nepřepisují.

## První sledované oblasti

- vlastní meteostanice ITEPLI65 přes Weather Underground,
- lokální venkovní teplota bazénového TČ,
- venkovní teplota Jablotronu po doplnění entity,
- hladina dešťové nádrže,
- stav a provoz bazénového TČ,
- cílová a diagnostické teploty bazénového TČ,
- modulace kompresoru,
- později samostatný příkon TČ a filtrace ze Shelly.

## Stav projektu

Vývojová verze. Neřídí zařízení a nemění jejich stav.
