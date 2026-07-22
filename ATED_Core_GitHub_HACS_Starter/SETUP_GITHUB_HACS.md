# První nastavení GitHub + HACS

## A. Nahrání repozitáře na GitHub bez příkazové řádky

1. Přihlaste se na GitHub a vytvořte nový veřejný repozitář `ated-core`.
2. Nechte repozitář prázdný: nepřidávejte README, licenci ani `.gitignore`.
3. Nainstalujte a spusťte GitHub Desktop.
4. Zvolte **File → Add local repository** a vyberte tuto rozbalenou složku.
5. Pokud GitHub Desktop oznámí, že složka není repozitář, zvolte **Create a repository**.
6. Jako název použijte `ated-core`, větev přejmenujte na `main`.
7. Proveďte první commit a klikněte **Publish repository**.
8. Na GitHubu otevřete **Actions** a ověřte, že kontroly skončily zeleně.

## B. Dvě nutné úpravy před prvním vydáním

V `custom_components/ated_core/manifest.json` nahraďte
`YOUR_GITHUB_USERNAME` svým GitHub uživatelským jménem ve třech URL a vložte
stejné jméno do `codeowners` ve tvaru `@uživatel`.

## C. První release 0.1.0

V GitHub Desktop:

1. Commitněte případnou úpravu uživatelského jména a pushněte ji.
2. Otevřete web GitHubu → **Releases → Draft a new release**.
3. Vytvořte nový tag `v0.1.0` z větve `main`.
4. Název: `ATED Core v0.1.0`.
5. Klikněte **Publish release**.

Později lze release vytvořit také pouhým pushem tagu. Workflow automaticky
ověří shodu tagu s verzí v manifestu a vytvoří ZIP.

## D. Přidání do HACS

1. Home Assistant → **HACS → Integrace**.
2. Otevřete nabídku se třemi tečkami → **Vlastní repozitáře**.
3. Vložte adresu repozitáře `https://github.com/UŽIVATEL/ated-core`.
4. Kategorie: **Integration**.
5. Přidejte repozitář, otevřete ATED Core a zvolte **Download**.
6. Restartujte Home Assistant.
7. **Nastavení → Zařízení a služby → Přidat integraci → ATED Core**.

## E. Každá další aktualizace

1. Upravte kód.
2. Zvyšte verzi v `manifest.json`, například na `0.1.1`.
3. Doplňte `CHANGELOG.md`.
4. Commit + push a vyčkejte na zelené kontroly.
5. Vytvořte a pushněte tag `v0.1.1`, případně ho vytvořte přes GitHub Release.
6. HACS následně nabídne aktualizaci.
