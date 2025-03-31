# Home Assistant Integration for Svea Solar

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom component designed for [Home Assistant](https://www.home-assistant.io) with the capability to show information about your systems integrated with Svea Solar.

### Install with HACS (recommended)

Do you have [HACS][hacs] installed? Just search for Svea Solar and install it directly from HACS. HACS will keep track of updates, and you can easily upgrade this integration to the latest version.

### Manual Installation

1. Using the tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder), create a new folder called `sveasolar`.
4. Download _all_ the files from the `custom_components/sveasolar/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant.
7. In the HA UI, go to "Configuration" -> "Integrations", click "+", and search for "Svea Solar".

### Sensors Exposed by Svea Solar Integration

#### Battery

- **Battery Status**: Monitors the status of the battery.
- **Battery Level (SoC)**: Indicates the state of charge of the battery, measured in percentage.
- **Today Discharged Energy**: Measures the energy discharged by the battery today, in kWh.
- **Today Charged Energy**: Measures the energy charged into the battery today, in kWh.
- **Discharge Power**: Indicates the discharge power of the battery, measured in watts.
- **Capacity**: Shows the capacity of the battery, in kWh.

#### Electric Vehicle

- **EV Charging Status**: Displays the charging status of the electric vehicle.
- **EV Battery Level**: Indicates the battery level of the electric vehicle, measured in percentage.
- **EV Range**: Shows the range of the electric vehicle, measured in kilometers.
- **EV Total Energy**: Measures the total energy consumed by the electric vehicle, in kWh.
- **EV Total Charging Time**: Indicates the total charging time of the electric vehicle, measured in hours.

#### Location

- **Location Energy Price**: Displays the energy price at the location, measured in SEK/kWh.
- **Location Rating**: Shows the rating of the location based on energy price.
- **Location Status**: Indicates the status of the location.
- **Location Solar Power**: Measures the solar power generated at the location, in kW.
- **Location Battery Power**: Indicates the power drawn from the battery at the location, in kW.
- **Location Usage Power**: Shows the power usage at the location, in kW.
- **Location Grid Power**: Measures the power drawn from the grid at the location, in kW.

Contributions are welcome!

---

**Disclaimer**: This integration is not affiliated with the company Svea Solar.

[buymecoffee]: https://www.buymeacoffee.com/JohNan
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/JohNan/homeassistant-sveasolar.svg?style=for-the-badge
[commits]: https://github.com/JohNan/homeassistant-sveasolar/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/JohNan/homeassistant-sveasolar.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40JohNan-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/JohNan/homeassistant-sveasolar.svg?style=for-the-badge
[releases]: https://github.com/JohNan/homeassistant-sveasolar/releases
[user_profile]: https://github.com/JohNan
