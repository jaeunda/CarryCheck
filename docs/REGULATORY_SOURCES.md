# Regulatory Sources and Operational Notes

## Scope and Review Method

This source review was performed on **August 25, 2026** for the rules currently represented by CarryCheck. Official English pages from regulators, customs authorities, quarantine authorities, airports, IATA, and airlines were preferred. Where a regulator did not publish an equivalent English page, the primary-language government source is retained and an official operator's English notice is added when available; this applies to parts of the CAAC and Japan MLIT material. Search-result snippets and third-party travel blogs are not treated as rule data, and the structured dataset remains an educational snapshot rather than a live pre-departure check.

## How the Rules Depend on One Another

The following gates are cumulative, not alternatives:

1. **Airline acceptance:** the operating carrier may impose a stricter limit or require approval.
2. **Departure security:** the origin country or airport may prohibit an item that the airline would otherwise accept.
3. **International dangerous-goods baseline:** IATA/ICAO guidance supplies a shared safety baseline but does not guarantee carrier acceptance.
4. **Transit screening:** a connecting airport can reapply its own departure-security rules if the traveler is screened again.
5. **Destination entry:** customs, quarantine, medicine, tax, and permit rules apply independently of baggage carriage.

A production decision must satisfy every applicable gate. `allowed` for carriage therefore does not mean `allowed` for import, and an item that must be declared is not automatically prohibited on the aircraft.

## Global and Airline Sources

| Area | Official English source | Implemented facts | Dependency or special note |
| --- | --- | --- | --- |
| IATA power banks | [Passenger guidance (2026 PDF)](https://www.iata.org/contentassets/6fea26dd84d24b26a7a1fd5788561d6e/passengers_travelling_with_lithium_batteries.pdf) and [operator implementation guidance](https://www.iata.org/contentassets/90f8038b0eea42069554b2f4530f49ea/guidance-to-operators---power-banks.pdf) | Carry-on only, at most two power banks, no in-flight recharging, protected and observable storage | The operator guidance states that it is used with the 67th DGR and is not effective beyond December 31, 2026; the 68th DGR applies from January 1, 2027. Recheck before that transition. |
| IATA passenger baggage | [Passenger Baggage Rules](https://www.iata.org/en/programs/ops-infra/baggage/passenger-baggage-rules/) and [Safe Travel with Lithium Batteries](https://www.iata.org/en/youandiata/travelers/batteries) | Spare batteries, power banks, and e-cigarettes belong in carry-on baggage; loose terminals require protection | Carry-on allowances vary by airline, cabin, aircraft, and route. |
| Korean Air | [Restricted Items](https://www.koreanair.com/contents/plan-your-travel/baggage/restricted-item?hl=en) | Power banks are carry-on only; the current page publishes capacity, count, approval, short-circuit, use, charging, and storage controls | The page is dynamic and localized. Overseas departure airports may apply stricter rules; capacity must be readable and damaged or swollen batteries may be refused. |
| Asiana Airlines | [Restricted Items](https://flyasiana.com/C/US/EN/contents/restricted-transport-items) and [April 20, 2026 power-bank notice](https://flyasiana.com/C/US/EN/customer/notice/detail?id=CM202604100002528761) | Up to two power banks; 100–160Wh requires approval; checked baggage, onboard use/charging, and overhead-bin storage are prohibited | The combined count for power banks and spare batteries in the 100–160Wh band is limited. China departure restrictions and destination e-cigarette bans remain separate. |
| Jeju Air | [Transport Limitations](https://www.jejuair.net/en/linkService/boardingProcessGuide/transportLimitation.do) | Power banks up to 160Wh, at most two; 100–160Wh requires approval; carry-on only with short-circuit protection | Flights departing Thailand additionally publish a 32,000mAh ceiling. `mAh` alone is not interchangeable with `Wh` without voltage, so both checks may apply. |

### Important 2026 Power-bank Difference

The IATA passenger guidance reviewed for 2026 describes power banks at **100Wh or less**, while the reviewed Korean airline pages still publish an approval path for some devices over 100Wh and up to 160Wh. Japan's April 24, 2026 rule also permits no more than two power banks of 160Wh or less. CarryCheck therefore stores shared IATA rules and carrier/country rules separately; it must not flatten them into one universal threshold.

## China

| Area | Official English source | Implemented facts | Dependency or special note |
| --- | --- | --- | --- |
| Domestic-flight power banks | [CAAC notice on CCC markings](https://www.caac.gov.cn/English/News/202507/t20250709_227894.html) | Since June 28, 2025, domestic flights reject power banks with no CCC mark, an unreadable CCC mark, or a recalled model/batch | Applies to domestic flights within China and is additional to capacity and airline rules. Recall status changes over time and is not fetched live. |
| Passenger customs | [China Customs clearance guide](https://english.customs.gov.cn/statics/88707c1e-aa4e-40ca-a968-bdbdbb565e4f.html) | Declaration, prohibited/restricted articles, quarantine goods, alcohol, and tobacco checks are represented | The official English static page can be slow or unavailable. A production service should monitor link health and retain the government publication metadata used for each rule. |

China's liquid restrictions differ between domestic and international departures, and airport screening remains the controlling operational decision. CarryCheck does not maintain live manufacturer recall or CCC-certificate feeds, so a positive result cannot prove that a specific battery model is currently valid.

## Thailand

| Area | Official English source | Implemented facts | Dependency or special note |
| --- | --- | --- | --- |
| International-departure liquids | [Airports of Thailand LAG guidance](https://suvarnabhumi.airportthai.co.th/service/airport-guide/detail/Liquid_BKK) | Each container must be no more than 100mL/100g and fit in one transparent resealable bag with a total capacity no greater than 1L | Medicines, baby food, duty-free STEBs, and transfer screening require case-specific checks. |
| Entry allowances | [Thai Customs airport-passenger guidance](https://apps.customs.go.th/list_strc_simple_neted.php?ini_content=individual_160503_03_160905_01&ini_menu=menu_pbc&lang=en&left_menu=menu_pbc_02_01&left_menu=menu_pbc_02_02&root_left_menu=menu_pbc_02) | Duty-free allowance includes no more than 1L of alcohol and 200 cigarettes or 250g of tobacco | Excess quantities are not a green-channel case; customs instructions must be followed. Personal effects also depend on value, reasonable quantity, non-commercial use, and prohibited/restricted status. |
| E-cigarettes | [Thai Customs prohibition notice](https://www.customs.go.th/cont_strc_slide_image.php?current_id=142329324147505f49464b4c464b49&lang=en&top_menu=menu_homepage) | Electronic cigarettes and baraku are prohibited imports | An e-cigarette may be carry-on-only under aviation rules and still be prohibited at destination entry. |
| Restricted goods | [Thai Customs restricted and prohibited items](https://www.customs.go.th/cont_strc_simple.php?ini_content=individual_160426_01&lang=en) | Food, medicines, cosmetics, plants, animals, radios, firearms, antiques, and other categories can require permits from different agencies | The permit-issuing authority is part of the rule; Customs is not the only dependency. The page reports a February 27, 2025 update date and must be rechecked periodically. |

## Japan

| Area | Official English source | Implemented facts | Dependency or special note |
| --- | --- | --- | --- |
| Power banks from April 24, 2026 | [JAL English notice](https://www.jal.co.jp/jp/en/info/2026/other/260330/) and [ANA English notice](https://www.ana.co.jp/en/us/special-notice/001380.html) | Carry-on only, no more than two per passenger, each no more than 160Wh, terminal protection, no onboard recharging or use to charge devices | The legal dependency is the revised Japan MLIT guideline. JAL warns that the limit may fall to 100Wh from January 2027, so this rule has a scheduled review point. |
| International-departure liquids | [ANA international LAG guidance](https://www.ana.co.jp/en/jp/guide/boarding-procedures/baggage/international/baggage-limit/) and [JAL restricted items](https://www.jal.co.jp/jp/en/inter/baggage/limit/) | Containers no larger than 100mL, one transparent resealable bag no larger than 1L, one bag per passenger | Codeshare operators, departure airports, transfer screening, medicines, baby food, special diets, and duty-free STEBs can change the handling. The security inspector has the final operational decision. |
| Passenger customs | [Japan Customs passenger clearance](https://www.customs.go.jp/english/summary/passenger.htm) | Every passenger declares belongings; adult allowances include about three 760mL alcohol bottles, tobacco category limits, 2oz perfume, and a general ¥200,000 allowance | Tax-free allowances do not override prohibited, restricted, commercial, quarantine, or permit requirements. Age, item value, combined categories, and unaccompanied baggage can change the procedure. |
| Meat and animal products | [MAFF Animal Quarantine Service](https://www.maff.go.jp/aqs/english/product/import.html) | Most meat and processed animal products require an exporting-government inspection certificate and arrival inspection; vacuum packing, heating, duty-free purchase, gifts, and small quantities are not automatic exceptions | Disease-related suspension lists change. MAFF introduced clarified exclusion criteria effective July 1, 2026, so product composition and manufacturing process can matter. |
| Plants | [MAFF Plant Protection Station](https://www.maff.go.jp/pps/j/pqaqinfo_en.html) | Many fruits, vegetables, plants, seeds, and soil are prohibited or require a phytosanitary certificate and inspection | Eligibility depends on both the product and country of origin. |
| Personal medicines | [Japan MHLW guidance](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/kojinyunyu/topics/tp010401-1_00001.html) | Published no-Import-Confirmation quantities include one month for prescription drugs and specified injectables, two months for other drugs, and 24 units per cosmetic item | Narcotics, stimulants, psychotropics, syringes, and controlled ingredients follow separate permission or prohibition rules. Some applications must be completed before departure. |

## Known Coverage Gaps

- South Korea destination customs and quarantine rules are not implemented.
- Unsupported countries return no destination-policy decision; they must not be interpreted as unrestricted.
- Transit policy is advisory because the system cannot know whether the passenger will be screened again.
- Live airline approvals, aircraft-specific restrictions, airport security decisions, recalls, CCC certificate validity, disease suspensions, and permit databases are not queried.
- The rule engine covers named item categories and thresholds, not every dangerous good or every fare/cabin baggage allowance.
- Official pages can change without preserving old URLs; `verified_date` is a snapshot, not an automatic freshness guarantee.

## Update Checklist

1. Open the official source and record the review date, effective date, scope, and superseded notice.
2. Check airline, origin, transit, and destination rules independently and record stricter dependencies.
3. Update the structured rule and its unique `rule_id`; do not silently change the meaning of a historical ID.
4. Add boundary tests immediately below, at, and above every numerical limit and tests for missing information.
5. Run dataset validation, unit tests, lint, JavaScript syntax checks, and the no-API local demo.
6. Schedule reviews before known transitions, especially the January 1, 2027 IATA DGR change noted above.
