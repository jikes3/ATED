ATED 0.4.1 – instalace
========================

1. Vytvoř zálohu adresáře:
   /config/custom_components/ated_core

2. Zastav Home Assistant nebo nahraď celý adresář ATED soubory z tohoto balíčku:
   custom_components/ated_core

3. Ověř, že v souboru manifest.json je verze 0.4.1.

4. Proveď úplný restart Home Assistantu.

5. Po restartu zkontroluj:
   - ATED Core: verze/firmware 0.4.1
   - Historian Health: healthy
   - Device Registry Health: healthy
   - Chybějící entity: 0
   - Nedostupné entity: podle skutečného stavu zařízení

Poznámky
--------
- Historická data v /config/ated_data se nemažou ani nemigrují.
- Historian schema zůstává ve verzi 2.
- Device Registry schema zůstává ve verzi 1.
- Krátký stav „starting“ nebo přechodná nedostupnost během startu HA se po události
  Home Assistant Started automaticky přepočítá.
