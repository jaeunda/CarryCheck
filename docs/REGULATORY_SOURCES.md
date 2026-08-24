# Regulatory Sources and Operational Notes

## Scope

This source review was performed on **August 25, 2026** for the rules represented by CarryCheck. Official English pages from regulators, customs and quarantine authorities, airports, IATA, and airlines were preferred. Search-result snippets and third-party travel blogs are not rule data; this dataset is an educational snapshot, not a live pre-departure clearance service.

![Cumulative regulatory gates from international guidance through destination entry](assets/regulatory-gates.svg)

## How Rules Combine

Every applicable gate is cumulative:

1. **International baseline** — IATA and ICAO dangerous-goods guidance establishes shared safety constraints.
2. **Operating airline** — the carrier may set stricter limits, require approval, or apply aircraft-specific controls.
3. **Departure security** — the origin country or airport may reject an item the carrier would otherwise accept.
4. **Transit screening** — connecting-airport rules may apply again when a passenger is rescreened.
5. **Destination entry** — customs, tax, quarantine, medicines, import prohibitions, and permits remain independent.

> [!IMPORTANT]
> `allowed` for aircraft carriage never means automatically `allowed` for import. A declaration requirement is also not the same as an aviation prohibition.

## Global and Airline Sources

### IATA — power banks in 2026

- **Official sources:** [Passenger guidance (2026 PDF)](https://www.iata.org/contentassets/6fea26dd84d24b26a7a1fd5788561d6e/passengers_travelling_with_lithium_batteries.pdf) · [Operator implementation guidance](https://www.iata.org/contentassets/90f8038b0eea42069554b2f4530f49ea/guidance-to-operators---power-banks.pdf)
- **Encoded rule:** carry-on only, at most two power banks, no in-flight recharging, and protected, observable storage.
- **Dependency:** the operator guidance accompanies the 67th DGR and is not effective beyond December 31, 2026. The 68th DGR applies from January 1, 2027, so this source has a scheduled review point.

### IATA — general passenger baggage

- **Official sources:** [Passenger Baggage Rules](https://www.iata.org/en/programs/ops-infra/baggage/passenger-baggage-rules/) · [Safe Travel with Lithium Batteries](https://www.iata.org/en/youandiata/travelers/batteries)
- **Encoded rule:** spare batteries, power banks, and e-cigarettes belong in carry-on baggage, with loose terminals protected.
- **Dependency:** allowances can still vary by airline, cabin, aircraft, and route.

### Korean Air

- **Official source:** [Restricted Items](https://www.koreanair.com/contents/plan-your-travel/baggage/restricted-item?hl=en)
- **Encoded rule:** power banks are carry-on only; the page publishes capacity, count, approval, short-circuit, onboard-use, charging, and storage controls.
- **Dependency:** the page is dynamic and localized. Overseas departure airports may be stricter; capacity must be readable, and damaged or swollen batteries may be refused.

### Asiana Airlines

- **Official sources:** [Restricted Items](https://flyasiana.com/C/US/EN/contents/restricted-transport-items) · [April 20, 2026 power-bank notice](https://flyasiana.com/C/US/EN/customer/notice/detail?id=CM202604100002528761)
- **Encoded rule:** at most two power banks; `100–160Wh` requires approval; checked baggage, onboard use or charging, and overhead-bin storage are prohibited.
- **Dependency:** the count for power banks and spare batteries in the `100–160Wh` band is combined. China departure restrictions and destination e-cigarette bans remain separate gates.

### Jeju Air

- **Official source:** [Transport Limitations](https://www.jejuair.net/en/linkService/boardingProcessGuide/transportLimitation.do)
- **Encoded rule:** power banks up to `160Wh`, at most two; `100–160Wh` requires approval; carry-on only with short-circuit protection.
- **Dependency:** Thailand departures additionally publish a `32,000mAh` ceiling. `mAh` cannot be converted to `Wh` without voltage, so both checks may apply.

> [!WARNING]
> **The 2026 power-bank thresholds are not universal.** The reviewed IATA passenger guidance describes power banks at `100Wh` or less, while Korean carrier pages retain an approval path through `160Wh`. Japan's April 24, 2026 rule also permits at most two batteries at or below `160Wh`. CarryCheck stores these rules separately instead of flattening them into one threshold.

## China

### Domestic-flight power banks

- **Official source:** [CAAC notice on CCC markings](https://www.caac.gov.cn/English/News/202507/t20250709_227894.html)
- **Encoded rule:** since June 28, 2025, domestic flights reject power banks without a CCC mark, with an unreadable mark, or from a recalled model or batch.
- **Dependency:** this is additional to airline capacity rules. CarryCheck does not query live manufacturer recalls or CCC-certificate validity.

### Passenger customs

- **Official source:** [China Customs clearance guide](https://english.customs.gov.cn/statics/88707c1e-aa4e-40ca-a968-bdbdbb565e4f.html)
- **Encoded rule:** declaration, prohibited or restricted articles, quarantine goods, alcohol, and tobacco checks are represented.
- **Dependency:** the official English static page can be slow or unavailable. Production use should monitor link health and retain government publication metadata.

China's liquid restrictions differ between domestic and international departures, and airport screening remains the controlling operational decision. A positive CarryCheck result cannot prove that a specific battery model is currently valid.

## Thailand

### International-departure liquids

- **Official source:** [Airports of Thailand LAG guidance](https://suvarnabhumi.airportthai.co.th/service/airport-guide/detail/Liquid_BKK)
- **Encoded rule:** each container is at most `100mL/100g` and must fit in one transparent resealable bag with total capacity no greater than `1L`.
- **Dependency:** medicines, baby food, duty-free STEBs, and transfer screening require case-specific checks.

### Entry allowances

- **Official source:** [Thai Customs airport-passenger guidance](https://apps.customs.go.th/list_strc_simple_neted.php?ini_content=individual_160503_03_160905_01&ini_menu=menu_pbc&lang=en&left_menu=menu_pbc_02_01&left_menu=menu_pbc_02_02&root_left_menu=menu_pbc_02)
- **Encoded rule:** duty-free allowance includes at most `1L` of alcohol and `200` cigarettes or `250g` of tobacco.
- **Dependency:** excess is not a green-channel case. Personal effects also depend on value, reasonable quantity, non-commercial use, and prohibited or restricted status.

### E-cigarettes

- **Official source:** [Thai Customs prohibition notice](https://www.customs.go.th/cont_strc_slide_image.php?current_id=142329324147505f49464b4c464b49&lang=en&top_menu=menu_homepage)
- **Encoded rule:** electronic cigarettes and baraku are prohibited imports.
- **Dependency:** an e-cigarette may be carry-on-only under aviation rules and still be prohibited at destination entry.

### Restricted goods

- **Official source:** [Thai Customs restricted and prohibited items](https://www.customs.go.th/cont_strc_simple.php?ini_content=individual_160426_01&lang=en)
- **Encoded rule:** food, medicines, cosmetics, plants, animals, radios, firearms, antiques, and other categories can require permits from different agencies.
- **Dependency:** Customs is not the only authority. The page reports a February 27, 2025 update date and requires periodic review.

## Japan

### Power banks from April 24, 2026

- **Official English notices:** [JAL](https://www.jal.co.jp/jp/en/info/2026/other/260330/) · [ANA](https://www.ana.co.jp/en/us/special-notice/001380.html)
- **Encoded rule:** carry-on only, at most two per passenger, each at most `160Wh`, terminal protection, and no onboard recharging or use to charge devices.
- **Dependency:** the legal basis is the revised Japan MLIT guideline. JAL warns that the limit may fall to `100Wh` from January 2027, creating a scheduled review point.

### International-departure liquids

- **Official sources:** [ANA international LAG guidance](https://www.ana.co.jp/en/jp/guide/boarding-procedures/baggage/international/baggage-limit/) · [JAL restricted items](https://www.jal.co.jp/jp/en/inter/baggage/limit/)
- **Encoded rule:** containers no larger than `100mL`, one transparent resealable bag no larger than `1L`, and one bag per passenger.
- **Dependency:** codeshare operators, departure airports, transfers, medicines, baby food, special diets, and duty-free STEBs can change handling. The security inspector has the final operational decision.

### Passenger customs

- **Official source:** [Japan Customs passenger clearance](https://www.customs.go.jp/english/summary/passenger.htm)
- **Encoded rule:** every passenger declares belongings; adult allowances include about three `760mL` alcohol bottles, tobacco-category limits, `2oz` of perfume, and a general `¥200,000` allowance.
- **Dependency:** tax-free allowances never override prohibited, restricted, commercial, quarantine, or permit requirements. Age, value, combined categories, and unaccompanied baggage can change the procedure.

### Meat and animal products

- **Official source:** [MAFF Animal Quarantine Service](https://www.maff.go.jp/aqs/english/product/import.html)
- **Encoded rule:** most meat and processed animal products require an exporting-government inspection certificate and arrival inspection. Vacuum packing, heating, duty-free purchase, gifts, and small quantities are not automatic exceptions.
- **Dependency:** disease suspension lists change. MAFF introduced clarified exclusion criteria effective July 1, 2026, so composition and manufacturing process can matter.

### Plants

- **Official source:** [MAFF Plant Protection Station](https://www.maff.go.jp/pps/j/pqaqinfo_en.html)
- **Encoded rule:** many fruits, vegetables, plants, seeds, and soil are prohibited or require a phytosanitary certificate and inspection.
- **Dependency:** eligibility depends on both product and country of origin.

### Personal medicines

- **Official source:** [Japan MHLW guidance](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/kojinyunyu/topics/tp010401-1_00001.html)
- **Encoded rule:** no-Import-Confirmation quantities include one month for prescription drugs and specified injectables, two months for other drugs, and 24 units per cosmetic item.
- **Dependency:** narcotics, stimulants, psychotropics, syringes, and controlled ingredients follow separate permissions or prohibitions. Some applications must be completed before departure.

## Known Coverage Gaps

- South Korea destination customs and quarantine are not implemented.
- Unsupported countries return no destination-policy decision and must not be interpreted as unrestricted.
- Transit policy is advisory because the system cannot know whether rescreening occurs.
- Live approvals, aircraft restrictions, airport decisions, recalls, CCC validity, disease suspensions, and permit databases are not queried.
- Named item categories and thresholds do not cover every dangerous good or fare and cabin allowance.
- `verified_date` records a snapshot; it is not an automatic freshness guarantee.

## Update Checklist

1. Open the official source and record its review date, effective date, scope, and superseded notice.
2. Check airline, origin, transit, and destination rules independently.
3. Update the structured rule and unique `rule_id`; never silently change a historical ID's meaning.
4. Add tests immediately below, at, and above every threshold, including missing-information cases.
5. Run dataset validation, unit tests, lint, JavaScript syntax checks, and the no-API local profile.
6. Schedule reviews before known transitions, especially the January 1, 2027 IATA DGR change.
