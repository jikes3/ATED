# Changelog

## 0.4.1

Stabilizační vydání větve Device Registry.

- Sjednocena verze integrace v `const.py`, `manifest.json` a zařízeních Home Assistantu.
- Opravena zastaralá hodnota firmware zařízení po aktualizaci.
- Device Registry se po dokončení startu Home Assistantu nuceně obnoví.
- Registr se okamžitě obnoví při změně dostupnosti sledované entity.
- Doplněny seznamy dostupných, nedostupných a chybějících entit.
- Doplněna kompaktní diagnostika každé registrované entity.
- Zachován Historian schema v2 a Device Registry schema v1.
- Bez změny formátu historických JSONL dat.

## 0.4.0

- Přidán Device Registry Core.
- Přidáno logické seskupování zařízení pomocí HA Entity Registry a Device Registry.
- Přidána inference kategorií a capabilities.
- Přidán atomický export registru do JSON.
- Přidány diagnostické senzory Device Registry.
- Přidán samostatný senzor verze ATED.
