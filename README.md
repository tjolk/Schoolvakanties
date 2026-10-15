<p align="center"><img src="https://raw.githubusercontent.com/tjolk/Schoolvakanties/main/images/icon.png" alt="Schoolvakanties Nederland" width="128"></p>

# Schoolvakanties Nederland

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/tjolk/Schoolvakanties/actions/workflows/validate.yml/badge.svg)](https://github.com/tjolk/Schoolvakanties/actions/workflows/validate.yml)

🇬🇧 English · 🇳🇱 [Nederlands](README.nl.md)

A Home Assistant integration that provides the Dutch **school holidays** and the **public holidays on which schools are closed** as sensors and as a calendar. Use them in automations, for example for alarms, heating or a notification on your dashboard.

## Features

- School holidays for region **North, Central or South** (*Noord, Midden, Zuid*), taken directly from the [Dutch government's open data](https://www.rijksoverheid.nl/opendata/schoolvakanties).
- **The region is suggested based on your Home Assistant home location** (via the [PDOK Locatieserver](https://www.pdok.nl/)). You can always change it.
- Public holidays on which schools are [closed in principle](https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/vrij-van-school-op-feestdagen): New Year's Day, Easter Monday, King's Day, Liberation Day, Ascension Day, Whit Monday, and Christmas Day and Boxing Day.
- Optional extra days off: Good Friday and the Friday after Ascension Day.
- Keeps working when the API is temporarily unavailable, because the last known holidays are stored locally.
- No API key and no extra Python packages needed.

## Installation

### Via HACS (custom repository)

1. In HACS, go to **⋮ → Custom repositories**.
2. Add `https://github.com/tjolk/Schoolvakanties` with type **Integration**.
3. Search for **Schoolvakanties Nederland**, install it and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Schoolvakanties Nederland**.

### Manual

Copy `custom_components/schoolvakanties_nl` to your `config/custom_components/` folder and restart Home Assistant.

## Configuration

When you add the integration, it shows which place was found, for example *Didam, gemeente Montferland, Gelderland → region South*. The region is then pre-filled. If it is wrong, simply pick another region. You can change everything later via **Configure**.

| Option | Default | Description |
|---|---|---|
| Region | based on location | North, Central or South |
| National holidays are school-free | on | The public holidays listed above |
| Extra days off at your school | none | Good Friday, Friday after Ascension Day |
| Weekend counts as school-free | on | Turn off to only count school holidays and public holidays |

## Entities

The entity IDs below apply to a Home Assistant set to English. With Home Assistant set to Dutch you get, for example, `binary_sensor.schoolvakanties_vandaag`; see the [Dutch documentation](README.nl.md).

Holiday names (such as *Herfstvakantie*, *Kerstvakantie*) come from the government data and are in Dutch. Attribute names are also in Dutch; their meaning is given below.

| Entity | State | Main attributes |
|---|---|---|
| `binary_sensor.schoolvakanties_today` | `on` when there is no school today | `redenen` (reasons), `vakantie` (holiday), `feestdag` (public holiday), `weekend`, `volgende_schooldag` (next school day) |
| `binary_sensor.schoolvakanties_tomorrow` | `on` when there is no school tomorrow | same as above |
| `binary_sensor.schoolvakanties_school_holiday` | `on` during a school holiday | `naam` (name), `begin` (start), `eind` (end) |
| `sensor.schoolvakanties_current_holiday` | name of the current holiday, or `Geen` (none) | `begin`, `eind`, `dagen` (number of days) |
| `sensor.schoolvakanties_next_holiday` | name of the next holiday | `begin`, `eind`, `dagen_tot_begin` (days until start) |
| `sensor.schoolvakanties_next_holiday_start` | date | |
| `sensor.schoolvakanties_days_until_holiday` | number of days (0 during a holiday) | |
| `calendar.schoolvakanties_calendar` | all school holidays and public holidays | |
| `sensor.schoolvakanties_region` | `noord`, `midden` or `zuid` (diagnostic) | `laatste_bekende_vakantiedag` (last known holiday date) |

The calendar does not include weekends. Use it in the Home Assistant calendar view, on a calendar card, or with a calendar trigger (for example "30 minutes before the end of a holiday").

## Examples

**Alarm only on school days**

```yaml
automation:
  - alias: "Wake up the kids"
    triggers:
      - trigger: time
        at: "07:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.schoolvakanties_today
        state: "off"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.kids_room
```

**Notify the evening before a day off**

```yaml
automation:
  - alias: "No school tomorrow"
    triggers:
      - trigger: time
        at: "19:30:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.schoolvakanties_tomorrow
        state: "on"
      - condition: template
        value_template: "{{ not state_attr('binary_sensor.schoolvakanties_tomorrow', 'weekend') }}"
    actions:
      - action: notify.mobile_app_phone
        data:
          message: >
            No school tomorrow:
            {{ state_attr('binary_sensor.schoolvakanties_tomorrow', 'redenen') | join(', ') }}
```

**Reminder at the end of a holiday**

```yaml
automation:
  - alias: "School starts again tomorrow"
    triggers:
      - trigger: calendar
        event: end
        entity_id: calendar.schoolvakanties_calendar
        offset: "-04:30:00"   # the event ends at midnight, so 19:30 on the last day
    actions:
      - action: notify.mobile_app_phone
        data:
          message: "School starts again tomorrow ({{ trigger.calendar_event.summary }} is over)."
```

**On the dashboard**

```yaml
type: markdown
content: >
  **{{ states('sensor.schoolvakanties_days_until_holiday') }} days** until
  {{ states('sensor.schoolvakanties_next_holiday') }}.
```

## Keeping the data up to date

The Dutch government only offers an API for the school holidays themselves. Regions and public holidays are therefore part of the code, in two files that are easy to update:

- **`custom_components/schoolvakanties_nl/data/regios.json`** contains which provinces, municipalities and towns belong to which region, according to [this page](https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/regios-schoolvakantie). The lookup order is: town within a municipality, then municipality, then province.
- **`custom_components/schoolvakanties_nl/feestdagen.py`** contains the public holidays as *rules*, such as "Easter + 39 days" or "27 April, or 26 April if that is a Sunday". This keeps them correct for every year.

If you find a municipality that ends up in the wrong region, please open an issue.

## Sources and license

- School holidays: [Rijksoverheid open data](https://www.rijksoverheid.nl/opendata/schoolvakanties) (CC0)
- Location: [PDOK Locatieserver](https://github.com/PDOK/locatieserver/wiki/API-Locatieserver). The coordinates of your home location are sent to PDOK once, only during setup.
- Code: [MIT](LICENSE)

This is not an official product of the Dutch government. When in doubt, always check your school's own calendar, as schools may have extra days off or study days.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
