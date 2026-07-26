# ATED 0.5.0-alpha.1

První kompletní instalační release větve 0.5.x. Verze je bezpečně pouze čtecí a nesmí provádět živé řízení.

## Nové části

- Event Journal schema 1, oddělený od Historianu schema 2.
- Actor model s konzervativním původem `unknown`, pokud chybí důkaz.
- Vazba stav → rozhodnutí → akce → reakce → budoucí uživatelský záměr.
- Detekce rychlého obrácení akce pouze jako `possible_rejection`.
- Decision model v režimech read-only/dry-run; live rozhodnutí je v této verzi zakázáno.
- Presentation Engine s úrovněmi 0–4:
  - 0 pouze výsledek,
  - 1 stručné vysvětlení,
  - 2 pokročilé údaje,
  - 3 expert,
  - 4 vývojář.
- Výchozí úroveň lze nastavit v možnostech integrace.

## Kompatibilita

- Historian schema zůstává 2.
- Device Registry schema zůstává 1.
- Stávající data se nemažou ani nemigrují.
- Event Journal používá vlastní adresář `ated_data/events`.
