<p align="center"><img src="https://raw.githubusercontent.com/tjolk/Schoolvakanties/main/images/icon.png" alt="Schoolvakanties Nederland" width="128"></p>

# Schoolvakanties Nederland

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/tjolk/Schoolvakanties/actions/workflows/validate.yml/badge.svg)](https://github.com/tjolk/Schoolvakanties/actions/workflows/validate.yml)

Een Home Assistant-integratie die de Nederlandse **schoolvakanties** en de **feestdagen waarop scholen dicht zijn** als sensoren en als kalender beschikbaar maakt. Je kunt ze gebruiken in automations, bijvoorbeeld voor de wekker, de verwarming of een melding op het dashboard.

*English: Dutch school holidays (per region) and school-free public holidays as Home Assistant sensors and a calendar. Data: Dutch government open data.*

## Functies

- Vakanties voor regio **Noord, Midden of Zuid**, rechtstreeks uit de [open data van de Rijksoverheid](https://www.rijksoverheid.nl/opendata/schoolvakanties).
- **De regio wordt voorgesteld op basis van de thuislocatie** van Home Assistant (via de [PDOK Locatieserver](https://www.pdok.nl/)). Je kunt hem altijd wijzigen.
- Feestdagen waarop scholen [in principe dicht zijn](https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/vrij-van-school-op-feestdagen): Nieuwjaarsdag, Tweede Paasdag, Koningsdag, Bevrijdingsdag, Hemelvaartsdag, Tweede Pinksterdag en Eerste en Tweede Kerstdag.
- Optionele extra vrije dagen: Goede Vrijdag en de vrijdag na Hemelvaart.
- Werkt ook als de API tijdelijk niet bereikbaar is, omdat de laatst bekende vakanties lokaal bewaard blijven.
- Geen API-key en geen extra Python-packages nodig.

## Installatie

### Via HACS (aangepaste repository)

1. Ga in HACS naar **⋮ → Aangepaste repositories**.
2. Voeg `https://github.com/tjolk/Schoolvakanties` toe, met type **Integratie**.
3. Zoek **Schoolvakanties Nederland**, installeer de integratie en herstart Home Assistant.
4. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen → Schoolvakanties Nederland**.

### Handmatig

Kopieer `custom_components/schoolvakanties_nl` naar de map `config/custom_components/` en herstart Home Assistant.

## Instellen

Bij het toevoegen zie je welke plaats is gevonden, bijvoorbeeld *Didam, gemeente Montferland, Gelderland → regio Zuid*. De regio is dan al ingevuld. Klopt het niet, kies dan zelf een andere regio. Je kunt alles later wijzigen via **Configureren**.

| Optie | Standaard | Uitleg |
|---|---|---|
| Regio | op basis van locatie | Noord, Midden of Zuid |
| Nationale feestdagen zijn schoolvrij | aan | De feestdagen hierboven |
| Extra vrije dagen | geen | Goede Vrijdag, vrijdag na Hemelvaart |
| Weekend telt als schoolvrij | aan | Zet uit als je alleen vakanties en feestdagen wilt meetellen |

## Entiteiten

De entity-id's hieronder gelden voor een Nederlandstalige Home Assistant. In het Engels krijg je bijvoorbeeld `binary_sensor.schoolvakanties_today`.

| Entiteit | Status | Belangrijkste attributen |
|---|---|---|
| `binary_sensor.schoolvakanties_vandaag` | `on` als er vandaag geen school is | `redenen`, `vakantie`, `feestdag`, `weekend`, `volgende_schooldag` |
| `binary_sensor.schoolvakanties_morgen` | `on` als er morgen geen school is | idem |
| `binary_sensor.schoolvakanties_schoolvakantie` | `on` tijdens een schoolvakantie | `naam`, `begin`, `eind` |
| `sensor.schoolvakanties_huidige_vakantie` | naam van de vakantie, of `Geen` | `begin`, `eind`, `dagen` |
| `sensor.schoolvakanties_volgende_vakantie` | naam van de volgende vakantie | `begin`, `eind`, `dagen_tot_begin` |
| `sensor.schoolvakanties_begin_volgende_vakantie` | datum | |
| `sensor.schoolvakanties_dagen_tot_vakantie` | aantal dagen (0 tijdens een vakantie) | |
| `calendar.schoolvakanties_kalender` | alle vakanties en feestdagen | |
| `sensor.schoolvakanties_regio` | `noord`, `midden` of `zuid` (diagnostisch) | `laatste_bekende_vakantiedag` |

## Voorbeelden

**Wekker alleen op schooldagen**

```yaml
automation:
  - alias: "Kinderen wekken"
    triggers:
      - trigger: time
        at: "07:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.schoolvakanties_vandaag
        state: "off"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.kinderkamer
```

**Laat de avond van tevoren weten dat morgen een vrije dag is**

```yaml
automation:
  - alias: "Morgen geen school"
    triggers:
      - trigger: time
        at: "19:30:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.schoolvakanties_morgen
        state: "on"
      - condition: template
        value_template: "{{ not state_attr('binary_sensor.schoolvakanties_morgen', 'weekend') }}"
    actions:
      - action: notify.mobile_app_telefoon
        data:
          message: >
            Morgen geen school:
            {{ state_attr('binary_sensor.schoolvakanties_morgen', 'redenen') | join(', ') }}
```

**Op het dashboard**

```yaml
type: markdown
content: >
  Nog **{{ states('sensor.schoolvakanties_dagen_tot_vakantie') }} dagen** tot de
  {{ states('sensor.schoolvakanties_volgende_vakantie') | lower }}.
```

## Gegevens bijwerken

De Rijksoverheid heeft alleen een API voor de vakanties zelf. Regio's en feestdagen staan daarom in de code, in twee bestanden die je makkelijk aanpast:

- **`custom_components/schoolvakanties_nl/data/regios.json`** bevat de indeling van provincies, gemeenten en woonplaatsen per regio, volgens [deze pagina](https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/regios-schoolvakantie). De volgorde bij het opzoeken is: woonplaats binnen een gemeente, dan gemeente, dan provincie.
- **`custom_components/schoolvakanties_nl/feestdagen.py`** bevat de feestdagen als *regels*, zoals "Pasen + 39 dagen" of "27 april, of 26 april als dat een zondag is". Ze kloppen daardoor voor elk jaar.

Als je een gemeente tegenkomt die in de verkeerde regio uitkomt, maak dan een issue aan.

## Bronnen en licentie

- Schoolvakanties: [Rijksoverheid open data](https://www.rijksoverheid.nl/opendata/schoolvakanties) (CC0)
- Locatie: [PDOK Locatieserver](https://github.com/PDOK/locatieserver/wiki/API-Locatieserver). Alleen bij het instellen worden de coördinaten van je thuislocatie één keer naar PDOK gestuurd.
- Code: [MIT](LICENSE)

Dit is geen officieel product van de Rijksoverheid. Controleer bij twijfel altijd de schoolgids van je school, want scholen kunnen extra vrije dagen of studiedagen hebben.

## Ontwikkelen

```bash
pip install -r requirements_test.txt
pytest
```
